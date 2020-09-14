from azureml.core import Workspace, Dataset
from azureml.core.compute import ComputeTarget, AmlCompute, ComputeInstance
from azureml.core.datastore import Datastore
from azureml.exceptions import ComputeTargetException, ProjectSystemException, UserErrorException
from msrest.exceptions import HttpOperationError
from azure.storage.fileshare import ShareClient
from azure.core.exceptions import ResourceNotFoundError
from azureml.data import FileDataset
import os
from collections import namedtuple
from azure.storage.fileshare import ShareFileClient
from io import BytesIO
import asyncio
import re

SUBSCRIPTION_ID = os.environ.get('SUBSCRIPTION_ID')
STORAGE_ACCOUNT_CONN_STR = os.environ.get('STORAGE_ACCOUNT_CONN_STR')
STORAGE_ACCOUNT_KEY = STORAGE_ACCOUNT_CONN_STR.split("AccountKey=")[1].split(';')[0]
STORAGE_ACCOUNT_NAME = os.environ.get('STORAGE_ACCOUNT_NAME')
SAS_TOKEN = os.environ.get('SAS_TOKEN')


class AzureUserFiles():

    def __init__(self, user, log):
        super().__init__()
        self._user = user
        self.log = log

    def create_user_file_share_if_not_exists(self):
        share_name = self.fileshare_name()
        created = False
        share = ShareClient.from_connection_string(STORAGE_ACCOUNT_CONN_STR, share_name=share_name)
        try:
            share.get_share_properties()
            self.log.info(f"'{share_name}' file share already exists")
        except ResourceNotFoundError:
            # TODO: Set quota?
            self.log.info(f"'{share_name}' file share does not exists creating...")
            share.create_share()
            self.log.info(f"'{share_name}' file share created.")

            # If the fileshare is empty it won't mount. Create a file.
            file = ShareFileClient.from_connection_string(
                STORAGE_ACCOUNT_CONN_STR, share_name=share_name, file_path=".DO_NOT_DELETE")

            # Upload a file
            file.upload_file(BytesIO("Please do not delete. There must always be one file in this location".encode('utf-8')))
            self.log.info(f"DO_NOT_DELETE file uploaded to '{share_name}' file share")
            created = True
        return created

    def fileshare_name(self):
        slug = self._user.escaped_name
        name = re.sub('[^-0-9a-zA-Z]+', '', slug)
        if not re.match('[A-z]', name[0]):
            name = 'A-' + name
        return name[:23]

    async def mount_user_ds_on_ci(self, ci, mount_point, ssh_private_key):
        HERE = os.path.join(os.path.dirname(__file__))
        ssh_port = ci.ssh_port
        ssh_host = f"azureuser@{ci.public_ip_address}"
        fileshare = self.fileshare_name()
        copy_scripts_to_ci_cmd = ["scp", "-i", f"{ssh_private_key}", "-o", "StrictHostKeyChecking no", "-P", str(ssh_port), f"{HERE}/mount.sh", f"{ssh_host}:/tmp"]
        chmod_scripts = ["ssh",  "-i", f"{ssh_private_key}", "-o", "StrictHostKeyChecking no", "-p", str(ssh_port), str(ssh_host), "chmod +x /tmp/mount.sh"]
        run_mount_scripts_cmd = ["ssh", "-i", f"{ssh_private_key}", "-o", "StrictHostKeyChecking no", "-t", "-p",
                                 str(ssh_port), str(ssh_host), f"""bash -l -c 'STORAGE_ACCOUNT_NAME={STORAGE_ACCOUNT_NAME} MOUNT_POINT={mount_point} SAS_TOKEN="{SAS_TOKEN}" FILE_SHARE_NAME={fileshare} /tmp/mount.sh'"""]

        for i, cmd in enumerate([copy_scripts_to_ci_cmd, chmod_scripts, run_mount_scripts_cmd]):
            self.log.info(f"Running cmd {i} to mount files")
            proc = await asyncio.create_subprocess_exec(*cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
            stdout, stderr = await proc.communicate()
            self.log.info(f"Cmd {i} complete. Std err:{stderr}")
