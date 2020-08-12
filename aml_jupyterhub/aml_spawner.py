"""Create an AzureML Spawner for JupyterHub."""

from concurrent.futures import ThreadPoolExecutor
import time
from traitlets import Unicode, Integer, default

from jupyterhub.spawner import Spawner

from tornado.concurrent import run_on_executor
from tornado import gen

from azureml.core import Workspace
from azureml.core.compute import ComputeTarget, AmlCompute, ComputeInstance
from azureml.exceptions import ComputeTargetException, ProjectSystemException


class AMLSpawner(Spawner):
    """
    A JupyterHub spawner that creates AzureML resources. A user will be given an
    AzureML workspace and an attached compute instance.

    "PanzureML" || "Panamel"

    """

    ip = Unicode('0.0.0.0', config=True,
                 help="The IP Address of the spawned JupyterLab instance.")

    # port = Unicode("", config=True,
    #                help="The port of the spawned JupyterHub instance.")

    start_timeout = Integer(
        360, config=True,
        help="""
        Timeout (in seconds) before giving up on starting of single-user server.
        This is the timeout for start to return, not the timeout for the server to respond.
        Callers of spawner.start will assume that startup has failed if it takes longer than this.
        start should return when the server process is started and its location is known.
        """)

    _executor = None

    @property
    def executor(self):
        cls = self.__class__
        if cls._executor is None:
            cls._executor = ThreadPoolExecutor(1)
        return cls._executor

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Fix this for now.
        self.resource_group_name = "spawned_AMLs"

        self.workspace = None
        self.compute_instance = None
        self._application_urls = None

        # XXX: really??
        self._authenticate()

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

    # @run_on_executor
    def _poll_compute_setup(self):
        compute_instance_status = self.compute_instance.status
        state = compute_instance_status.state
        errors = compute_instance_status.errors
        return state, errors

    def _set_up_workspace(self):
        # Verify that the workspace does not already exist.
        try:
            self.workspace = Workspace(self.subscription_id,
                                       self.resource_group_name,
                                       self.workspace_name)
        except ProjectSystemException:
            self.workspace = Workspace.create(name=self.workspace_name,
                                              subscription_id=self.subscription_id,
                                              resource_group=self.resource_group_name,
                                              create_resource_group=False,
                                              location=self.location,
                                              sku='enterprise',
                                              show_output=False)

    def _set_up_compute_instance(self):
        """
        Set up an AML compute instance for the workspace. The compute instance is responsible
        for running the Python kernel and the optional JupyterLab instance for the workspace.

        """
        # Verify that cluster does not exist already.
        try:
            self.compute_instance = ComputeTarget(workspace=self.workspace,
                                                  name=self.compute_instance_name)
        except ComputeTargetException:
            instance_config = ComputeInstance.provisioning_configuration(vm_size="Standard_D2_v2")
            self.compute_instance = ComputeTarget.create(self.workspace,
                                                         self.compute_instance_name,
                                                         instance_config)

    def _start_compute_instance(self):
        stopped_state = "stopped"
        state, _ = self._poll_compute_setup()
        if state.lower() == stopped_state:
            try:
                self.compute_instance.start()
            except ComputeTargetException as e:
                self.log.warning(f"Warning: could not start compute resource:\n{e.message}")

    def _stop_compute_instance(self):
        try:
            self.compute_instance.stop()
        except ComputeTargetException as e:
            self.log.warning(e.message)

    def _wait_for_target_state(self, target_state):
        while True:
            state, _ = self._poll_compute_setup()
            if state.lower() == target_state:
                break
            time.sleep(2)

    # @run_on_executor
    def _set_up_resources(self):
        """Both of these methods are blocking, so try and async them as a pair."""
        self._set_up_workspace()
        self._set_up_compute_instance()
        self._start_compute_instance()  # Ensure existing but stopped resources are running.

    # @run_on_executor
    def _tear_down_resources(self):
        """This method blocks, so try and async it and pass back to a checker."""
        self._stop_compute_instance()

    def get_url(self):
        """An AzureML compute instance knows how to get its JupyterLab instance URL, so expose it."""
        key = "Jupyter Lab"
        return None if self.application_urls is None else self.application_urls[key]

    @gen.coroutine
    def start(self):
        """Start (spawn) AzureML resouces. Must be a coroutine."""
        self._set_up_resources()

        target_state = "running"
        self._wait_for_target_state(target_state)

        return self.application_urls["Jupyter Lab"]
        # self.port = ""  # Hacky McHackface.
        # return (self.ip, self.port)

    @gen.coroutine
    def stop(self, now=False):
        """Stop and terminate all spawned AzureML resources. Must be a coroutine."""
        self._tear_down_resources()

        if not now:
            target_state = "stopped"
            self._wait_for_target_state(target_state)

    @gen.coroutine
    def poll(self):
        """
        Healthcheck of spawned AzureML resources. Must be a coroutine.

        Checked statuses are as follows:
          * None: resources are running or starting up
          * 0 if unknown exit status
          * int > 0 for known exit status

        """
        result = None
        if self.compute_instance is not None:
            status, errors = self._poll_compute_setup()
            if status.lower() not in ["starting", "running"]:
                if status.lower() == "stopped":
                    # Assign code 2 == instance stopped.
                    result = 2
                elif len(errors):
                    # Known error.
                    result = 1
                else:
                    # Something else.
                    result = 0
        else:
            # Compute has not started, so treat as if not running.
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

    # async def progress(self):
    #     """
    #     Report on progress toward creating AzureML resources.

    #     Not essential, but given that AML resourece generation is sloooooowwww,
    #     having this might be good from a UX perspective.

    #     """
    #     return
