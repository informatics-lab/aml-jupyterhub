"""Create an AzureML Spawner for JupyterHub."""

from concurrent.futures import ThreadPoolExecutor
import os
import time
from traitlets import Unicode, Integer, default, Bool

from jupyterhub.spawner import Spawner

from tornado.concurrent import run_on_executor
import asyncio

from async_generator import async_generator, yield_

from azureml.core import Workspace
from azureml.core.compute import ComputeTarget, AmlCompute, ComputeInstance
from azureml.exceptions import ComputeTargetException, ProjectSystemException
import os

from . import redirector
from . import files


class AMLSpawner(Spawner):
    """
    A JupyterHub spawner that creates AzureML resources. A user will be given an
    AzureML workspace and an attached compute instance.

    "PanzureML" || "Panamel"

    """

    _vm_started_states = ["starting", "running"]
    _vm_transition_states = ["creating", "updating", "deleting"]
    _vm_stopped_states = ["stopping", "stopped"]
    _vm_bad_states = ["failed"]

    ip = Unicode('0.0.0.0', config=True,
                 help="The IP Address of the spawned JupyterLab instance.")

    start_timeout = Integer(
        360, config=True,
        help="""
        Timeout (in seconds) before giving up on starting of single-user server.
        This is the timeout for start to return, not the timeout for the server to respond.
        Callers of spawner.start will assume that startup has failed if it takes longer than this.
        start should return when the server process is started and its location is known.
        """)

    mount_userspace = Bool(
        False,
        config=True,
        help="""
        Whether or not to create (if not exists) and mount an Azure File Share to store user data
        than can persist between VMs and accross Azure ML workspaces.
        """
    )

    mount_userspace_location = Unicode(
        "~/userfiles",
        config=True,
        help="""
        Were to mount the users userspace files if `mount_userspace` is `True`.
        """
    )

    _events = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Fix this for now.
        self.resource_group_name = os.environ.get('RESOURCE_GROUP')

        self.workspace = None
        self.compute_instance = None
        self._application_urls = None
        self.redirect_server = None

        # XXX: this can be done better.
        self._authenticate()

    def _start_recording_events(self):
        self._events = []

    def _stop_recording_events(self):
        self._events = None

    def _add_event(self, msg, progress):
        if self._events is not None:
            self._event.append((msg, progress))

    def _authenticate(self):
        """
        Authenticate our user to Azure.

        TODO: actually perform authentication, rather than setting variables!
        TODO: figure out how to get an existing workspace for a user (like the AML login page.)

        """
        self.subscription_id = os.environ.get('SUBSCRIPTION_ID')
        self.location = os.environ.get('LOCATION')
        self.workspace_name = os.environ.get('SPAWN_TO_WORK_SPACE')
        self.compute_instance_name = os.environ.get('SPAWN_COMPUTE_INSTANCE_NAME')

    @property
    def application_urls(self):
        if self._application_urls is None:
            if self.compute_instance is None:
                result = None
            else:
                result = self._applications()
            self.application_urls = result
        return self._application_urls

    @application_urls.setter
    def application_urls(self, value):
        self._application_urls = value

    def _applications(self):
        """Parse Application URLs from the compute instance into a more queryable format."""
        applications = self.compute_instance.applications
        return {d["displayName"]: d["endpointUri"] for d in applications}

    def _poll_compute_setup(self):
        compute_instance_status = self.compute_instance.get_status()
        state = compute_instance_status.state
        errors = compute_instance_status.errors
        return state, errors

    async def _mount_userspace(self):
        user = {"username": 'theo.mccaie@informaticslab.co.uk'}
        files.create_user_file_share_if_not_exists(user)
        await files.mount_user_ds_on_ci(self.compute_instance, user, self.mount_userspace_location)

    def _set_up_workspace(self):
        # Verify that the workspace does not already exist.
        try:
            self.workspace = Workspace(self.subscription_id,
                                       self.resource_group_name,
                                       self.workspace_name)
            self.log.info(f"Workspace {self.workspace_name} already exits.")
        except ProjectSystemException:
            self.log.info(f"Creating workspace {self.workspace_name}.")
            self.workspace = Workspace.create(name=self.workspace_name,
                                              subscription_id=self.subscription_id,
                                              resource_group=self.resource_group_name,
                                              create_resource_group=False,
                                              location=self.location,
                                              sku='enterprise',
                                              show_output=False)
            self.log.info(f"Workspace {self.workspace_name} created.")

    def _set_up_compute_instance(self):
        """
        Set up an AML compute instance for the workspace. The compute instance is responsible
        for running the Python kernel and the optional JupyterLab instance for the workspace.

        """
        # Verify that cluster does not exist already.
        try:
            self.compute_instance = ComputeTarget(workspace=self.workspace,
                                                  name=self.compute_instance_name)

            self.log.info(f"Compute instance {self.compute_instance_name} already exists.")
        except ComputeTargetException:
            instance_config = ComputeInstance.provisioning_configuration(vm_size="Standard_DS1_v2",
                                                                         ssh_public_access=True,
                                                                         admin_user_ssh_public_key=os.environ.get('SSH_PUB_KEY'))
            self.compute_instance = ComputeTarget.create(self.workspace,
                                                         self.compute_instance_name,
                                                         instance_config)
            self.log.info(f"Created compute instance {self.compute_instance_name}.")

    def _start_compute_instance(self):
        stopped_state = "stopped"
        state, _ = self._poll_compute_setup()
        self.log.info(f"Compute instance state is {state}.")
        if state.lower() == stopped_state:
            try:
                self.log.info(f"Starting the compute instance.")
                self.compute_instance.start()
            except ComputeTargetException as e:
                self.log.warning(f"Could not start compute resource:\n{e.message}.")

    def _stop_compute_instance(self):
        try:
            self.log.info(f"Stopping the compute instance.")
            self.compute_instance.stop()

        except ComputeTargetException as e:
            self.log.warning(e.message)

    async def _wait_for_target_state(self, target_state):
        while True:
            state, _ = self._poll_compute_setup()
            if state.lower() == target_state:
                self.log.info(f"Compute in target state {target_state}.")
                break
            elif state.lower() in self._vm_bad_states:
                self.log.info(f"Waiting for compute to be in state {target_state}. Current state is {state}.")
                raise ComputeTargetException(f"Compute instance in failed state: {state!r}.")
            await asyncio.sleep(5)

    def _stop_redirect(self):
        if self.redirect_server:
            self.log.info(f"Stopping the redirect server route: {self.redirect_server.route}.")
            self.redirect_server.stop()
            self.redirect_server = None

    async def _set_up_resources(self):
        """Both of these methods are blocking, so try and async them as a pair."""
        self._set_up_workspace()
        self._set_up_compute_instance()
        self._start_compute_instance()  # Ensure existing but stopped resources are running.

    def _tear_down_resources(self):
        """This method blocks, so try and async it and pass back to a checker."""
        self._stop_compute_instance()
        self._stop_redirect()

    def get_url(self):
        """An AzureML compute instance knows how to get its JupyterLab instance URL, so expose it."""
        key = "Jupyter Lab"
        return None if self.application_urls is None else self.application_urls[key]

    @async_generator
    async def progress(self):

        import random
        count = 0
        action = ["Terminating", "Reconfiguring", "Dehydrating", "Rehydrating", "Activating", "Fermenting"]
        the_object = ["dog", "cat", "hat", "rhino", "powers that be", "ISS", "the twin you didn't know you had"]
        to = ["to", "in order to", "allowing the system to", "which will"]
        reason = ["activate the compute", "power the machine learning", "deionize the static", "release the power", "initialise the cloud", "retrieve user data"]
        while True:
            msg = f"{random.choice(action)} the {random.choice(the_object)} {random.choice(to)} {random.choice(reason)}."
            await yield_({
                'progress': random.randint(1, 99),
                'message':  msg
            })
            count += 1
            if count >= 50:
                break
            await asyncio.sleep(5)

    async def start(self):
        """Start (spawn) AzureML resouces."""
        await self._set_up_resources()

        target_state = "running"
        await self._wait_for_target_state(target_state)

        if self.mount_userspace:
            await self._mount_userspace()

        url = self.application_urls["Jupyter Lab"]
        route = redirector.RedirectServer.get_existing_redirect(url)
        if not route:
            self.redirect_server = redirector.RedirectServer(url)
            self.redirect_server.start()
            await asyncio.sleep(1)  # not sure this is need but did occasionally get bug where proxy didn't seem to have started fast enough so put in in as a just in case.
            route = self.redirect_server.route

        return route

    async def stop(self, now=False):
        """Stop and terminate all spawned AzureML resources."""
        self._tear_down_resources()

        self._stop_redirect()

        if not now:
            target_state = "stopped"
            await self._wait_for_target_state(target_state)

    async def poll(self):
        """
        Healthcheck of spawned AzureML resources.

        Checked statuses are as follows:
          * None: resources are running or starting up
          * 0 if unknown exit status
          * int > 0 for known exit status:
              * 1: Known error returned by polling the instance
              * 2: Compute instance found in an unhealthy state
              * 3: Compute instance stopped

        """
        result = None
        if self.compute_instance is not None:
            status, errors = self._poll_compute_setup()
            if status.lower() not in self._vm_started_states:
                if status.lower() in self._vm_stopped_states:
                    # Assign code 3 == instance stopped.
                    result = 3
                elif status.lower() in self._vm_bad_states:
                    # Assign code 2 == instance bad.
                    result = 2
                elif len(errors):
                    # Known error.
                    result = 1
                else:
                    # Something else.
                    result = 0
        else:
            # Compute has not started, so treat as if not running.
            result = 0
        return result

    def get_state(self):
        """Get the state of our spawned AzureML resources so that we can persist over restarts."""
        state = super().get_state()
        state["workspace_name"] = self.workspace_name
        state["compute_instance_name"] = self.compute_instance_name
        return state

    def load_state(self, state):
        """Load previously-defined state so that we can resume where we left off."""
        super().load_state(state)
        if "workspace_name" in state:
            self.workspace_name = state["workspace_name"]
        if "compute_instance_name" in state:
            self.compute_instance_name = state["compute_instance_name"]
