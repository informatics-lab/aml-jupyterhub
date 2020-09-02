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
import datetime
import re
import tempfile

from . import redirector
from . import files
import base64

URL_REGEX = re.compile(r'\bhttps://[^ ]*')
CODE_REGEX = re.compile(r'\b[A-Z0-9]{9}\b')


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
    _events = None
    _last_progress = 50

    ip = Unicode('0.0.0.0', config=True,
                 help="The IP Address of the spawned JupyterLab instance.")

    start_timeout = Integer(
        3600, config=True,
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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Fix this for now.
        self.resource_group_name = os.environ.get('RESOURCE_GROUP')

        self.workspace = None
        self.compute_instance = None
        self._application_urls = None
        self.redirect_server = None
        self._create_ssh_key()

        # XXX: this can be done better.
        self._authenticate()

    def _create_ssh_key(self):
        with tempfile.NamedTemporaryFile('wb', delete=False) as ssh_file:
            ssh_file.write(base64.b64decode(os.environ['SSH_PRIVATE_KEY']))
            self._ssh_private_key = ssh_file.name

    def _start_recording_events(self):
        self._events = []

    def _stop_recording_events(self):
        self._events = None

    def _add_event(self, msg, progress=None):
        if self._events is not None:
            if progress is None:
                progress = self._last_progress
            self._events.append((msg, progress))
            self.log.info(f"Event {msg}@{progress}%")
            self._last_progress = progress

    _VALID_MACHINE_NAME = re.compile(r"[A-z][-A-z0-9]{2,23}")

    def _make_safe_for_compute_name(self, name):
        name = re.sub('[^-0-9a-zA-Z]+', '', name)
        if not re.match('[A-z]', name[0]):
            name = 'A-' + name
        return name[:23]

    def _authenticate(self):
        """
        Authenticate our user to Azure.

        TODO: actually perform authentication, rather than setting variables!
        TODO: figure out how to get an existing workspace for a user (like the AML login page.)

        """
        self.subscription_id = os.environ.get('SUBSCRIPTION_ID')
        self.location = os.environ.get('LOCATION')
        self.workspace_name = os.environ.get('SPAWN_TO_WORK_SPACE')
        self.compute_instance_name = self._make_safe_for_compute_name(self.user.escaped_name + os.environ.get('SPAWN_COMPUTE_INSTANCE_SUFFIX'))

    @ property
    def application_urls(self):
        if self._application_urls is None:
            if self.compute_instance is None:
                result = None
            else:
                result = self._applications()
            self.application_urls = result
        return self._application_urls

    @ application_urls.setter
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
        files.create_user_file_share_if_not_exists(self.user)
        self._add_event(f"Mounting user files...", 75)
        await files.mount_user_ds_on_ci(self.compute_instance, self.user, self.mount_userspace_location, self._ssh_private_key)
        self._add_event(f"Mounted user files.", 90)

    def _set_up_workspace(self):
        # Verify that the workspace does not already exist.
        try:
            self.workspace = Workspace(self.subscription_id,
                                       self.resource_group_name,
                                       self.workspace_name)
            self.log.info(f"Workspace {self.workspace_name} already exits.")
            self._add_event(f"Workspace {self.workspace_name} already exits.", 10)
        except ProjectSystemException:
            self.log.info(f"Creating workspace {self.workspace_name}.")
            self._add_event(f"Creating workspace {self.workspace_name}", 1)
            self.workspace = Workspace.create(name=self.workspace_name,
                                              subscription_id=self.subscription_id,
                                              resource_group=self.resource_group_name,
                                              create_resource_group=False,
                                              location=self.location,
                                              sku='enterprise',
                                              show_output=False)
            self.log.info(f"Workspace {self.workspace_name} created.")
            self._add_event(f"Workspace {self.workspace_name} created", 10)

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
            self._add_event(f"Compute instance {self.compute_instance_name} already exists", 20)
        except ComputeTargetException:
            self._add_event(f"Creating compute instance {self.compute_instance_name}", 15)
            instance_config = ComputeInstance.provisioning_configuration(vm_size="Standard_DS1_v2",
                                                                         ssh_public_access=True,
                                                                         admin_user_ssh_public_key=os.environ.get('SSH_PUB_KEY'))
            self.compute_instance = ComputeTarget.create(self.workspace,
                                                         self.compute_instance_name,
                                                         instance_config)
            self.log.info(f"Created compute instance {self.compute_instance_name}.")
            self._add_event(f"Created compute instance {self.compute_instance_name}.", 20)

    def _start_compute_instance(self):
        stopped_state = "stopped"
        state, _ = self._poll_compute_setup()
        self.log.info(f"Compute instance state is {state}.")
        self._add_event(f"Compute instance in {state} state.", 20)

        if state.lower() == stopped_state:
            try:
                self.log.info(f"Starting the compute instance.")
                self._add_event("Starting the compute instance. This may take a short while...", 25)
                self.compute_instance.start()
            except ComputeTargetException as e:
                self.log.warning(f"Could not start compute resource:\n{e.message}.")

    def _stop_compute_instance(self):
        try:
            self.log.info(f"Stopping the compute instance.")
            self.compute_instance.stop()

        except ComputeTargetException as e:
            self.log.warning(e.message)

    async def _wait_for_target_state(self, target_state, progress_between=(30, 70), progress_in_seconds=240):
        """ Wait for the compute instance to be in the target state.

        emit events reporting progress starting at `progress_between[0]` to `progress_between[1]` over `progress_in_seconds` seconds.
        This is to give the use watching the progress bar the illusion of progress even if we don't really know how far we have progressed.
        """
        started_at = datetime.datetime.now()
        while True:
            state, _ = self._poll_compute_setup()
            time_taken = datetime.datetime.now() - started_at
            min_progress, max_progress = progress_between
            progress = (min_progress + (max_progress - min_progress) * (time_taken.total_seconds()/progress_in_seconds))//1
            progress = max_progress if progress > max_progress else progress
            if state.lower() == target_state:
                self.log.info(f"Compute in target state {target_state}.")
                self._add_event(f"Compute in target state '{target_state}'.", max_progress)
                break
            elif state.lower() in self._vm_bad_states:
                self._add_event(f"Compute instance in failed state: {state!r}.", min_progress)
                raise ComputeTargetException(f"Compute instance in failed state: {state!r}.")
            else:
                self._add_event(f"Compute in state '{state.lower()}' after {time_taken.total_seconds():.0f} seconds. Aiming for target state '{target_state}', this may take a short while", progress)
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

    @ async_generator
    async def progress(self):
        while self._events is not None:
            if len(self._events) > 0:
                msg, progress = self._events.pop(0)
                await yield_({
                    'progress': progress,
                    'message':  msg
                })
            await asyncio.sleep(1)

    async def _cli_login(self):

        async def _capture_az_login_code_and_url(stream):
            url = None
            code = None
            while True:
                line = await stream.readline()
                if line:
                    output = line.decode('ascii')

                    maybe_url = URL_REGEX.findall(output)
                    if len(maybe_url) == 1:
                        url = maybe_url[0]

                    maybe_code = CODE_REGEX.findall(output)
                    if len(maybe_code) == 1:
                        code = maybe_code[0]

                    if len(maybe_url) > 1 or len(maybe_code) > 1:
                        raise RuntimeError(f"The output from the az login command had more than one url or code: {output}")

                    if code and url:
                        msg = f"**Please visit {url} and enter {code} to authenticate the spawner to act on your behalf.**"
                        self._add_event(msg)
                        self.log.info(msg)
                        break
                else:
                    break

        cmd = ["az", "login", "--use-device-code"]
        proc = await asyncio.create_subprocess_exec(*cmd,
                                                    stdout=asyncio.subprocess.PIPE,
                                                    stderr=asyncio.subprocess.STDOUT)

        await _capture_az_login_code_and_url(proc.stdout)
        await proc.wait()
        self._add_event("Login complete, thank you!", 5)
        asyncio.sleep(1.5)  # This gives the progress bar a chance to notice, better user experience even if 1.5 seconds slower.

    async def start(self):
        """Start (spawn) AzureML resouces."""
        try:
            self._start_recording_events()
            self._add_event("Initializing...", 0)
            await self._cli_login()
            await self._set_up_resources()

            target_state = "running"
            await self._wait_for_target_state(target_state)

            if self.mount_userspace:
                await self._mount_userspace()

            url = self.application_urls["Jupyter Lab"]
            route = redirector.RedirectServer.get_existing_redirect(url)
            if route:
                self._add_event(f"Existing route to compute instance found.", 95)
            else:
                self._add_event(f"Creating route to compute instance.", 91)
                self.redirect_server = redirector.RedirectServer(url)
                self.redirect_server.start()
                await asyncio.sleep(1)  # not sure this is need but did occasionally get bug where proxy didn't seem to have started fast enough so put in in as a just in case.
                route = self.redirect_server.route
                self._add_event(f"Route to compute instance created.", 95)

            self._add_event(f"Set up complete. Prepare for redirect...", 100)

            return route
        finally:
            self._stop_recording_events()

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

    # def get_state(self):
    #     """Get the state of our spawned AzureML resources so that we can persist over restarts."""
    #     state = super().get_state()
    #     state["workspace_name"] = self.workspace_name
    #     state["compute_instance_name"] = self.compute_instance_name
    #     return state

    # def load_state(self, state):
    #     """Load previously-defined state so that we can resume where we left off."""
    #     super().load_state(state)
    #     if "workspace_name" in state:
    #         self.workspace_name = state["workspace_name"]
    #     if "compute_instance_name" in state:
    #         self.compute_instance_name = state["compute_instance_name"]
