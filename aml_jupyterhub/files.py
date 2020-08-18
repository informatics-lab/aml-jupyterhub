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
import subprocess


SUBSCRIPTION_ID = os.environ.get('SUBSCRIPTION_ID')
STORAGE_ACCOUNT_CONN_STR = os.environ.get('STORAGE_ACCOUNT_CONN_STR')
STORAGE_ACCOUNT_KEY = STORAGE_ACCOUNT_CONN_STR.split("AccountKey=")[1].split(';')[0]
STORAGE_ACCOUNT_NAME = os.environ.get('STORAGE_ACCOUNT_NAME')
DATASTORE_NAME = "homespaces"

# user = {"username": os.environ.get('DEFAULT_USERNAME')}


def _crete_file_share_if_not_exists(share_name):
    created = False
    share = ShareClient.from_connection_string(STORAGE_ACCOUNT_CONN_STR, share_name=share_name)
    try:
        share.get_share_properties()
    except ResourceNotFoundError:
        # TODO: Set quota?
        share.create_share()

        # If the fileshare is empty it won't mount. Create a file.
        file = ShareFileClient.from_connection_string(
            STORAGE_ACCOUNT_CONN_STR, share_name=share_name, file_path=".DO_NOT_DELETE")
        # Upload a file
        file.upload_file(BytesIO("Please do not delete. There must always be one file in this location".encode('utf-8')))

        created = True
    return created


def _create_dataset_if_not_exists(user, datastore, workspace):
    # create a FileDataset for user files that are available accross datasets.
    created = False
    ds_props = dataset_properties(user)

    try:
        Dataset.get_by_name(workspace, ds_props.name)
    except UserErrorException:
        ds = Dataset.File.from_files(path=[(datastore, '*')], validate=False)
        ds.register(workspace=workspace,
                    name=ds_props.name,
                    description=ds_props.description)
        created = True
        print('created dataset for user')
    return created


def datastore_name(user):
    # Hopefully their will be some unique id we can use to avoid collions.
    slug = user['username'].split('@')[0].replace('.', '_')
    return f"{slug}_homespace_files"


def fileshare_name(user):
    # Hopefully their will be some unique id we can use to avoid collions.
    slug = user['username'].split('@')[0].replace('.', '-')
    return f"{slug}-homespace"


def dataset_properties(user):
    DatasetProperties = namedtuple('DatasetProperties', ['name', 'description'])

    def slug(user):
        return user['username'].split('@')[0]

    name = f"{slug(user)}s-homes"
    description = f"Persistant storage for {slug(user)} that is available accross workspaces."
    return DatasetProperties(name, description)


# # Get workspaces
# ws_list = Workspace.list(SUBSCRIPTION_ID)
# print('users has access to:\n\t', '\n\t'.join(name for name in ws_list.keys()))
# ws_name = 'theo-msc'
# ws = ws_list[ws_name][0]
# # to fix https://github.com/Azure/azure-sdk-for-python/issues/12948
# ws = Workspace(ws.subscription_id, ws.resource_group, ws.name)

# def get_compute_instances(ws):
#     # Get compute instances
#     ct_list = ComputeTarget.list(ws)
#     accassable_ci = list(filter((lambda ct: ct.type == 'ComputeInstance' and ct.ssh_public_access), ct_list))
#     assert len(accassable_ci) >= 1
#     ci = accassable_ci[0]
#     return ci


def create_datastore_and_set_for_userspace_if_not_exists(ws, user):
    # Get / create data store
    ds_name = datastore_name(user)
    try:
        homespace_datastore = Datastore.get(ws, ds_name)
        print("Found Datastore with name: %s" % ds_name)
    except HttpOperationError as e:
        if not e.response.status_code == 404:
            raise e  # Exception other than resource not existing.
        share_name = fileshare_name(user)
        _crete_file_share_if_not_exists(share_name)
        homespace_datastore = Datastore.register_azure_file_share(
            workspace=ws,
            datastore_name=ds_name,
            account_name=STORAGE_ACCOUNT_NAME,
            file_share_name=share_name,
            account_key=STORAGE_ACCOUNT_KEY)
        print("Registered datastore with name: %s" % ds_name)

    _create_dataset_if_not_exists(user, homespace_datastore, ws)


def mount_user_ds_on_ci(ci, user, mount_point):
    HERE = os.path.join(os.path.dirname(__file__))
    ssh_port = ci.ssh_port
    ssh_host = f"azureuser@{ci.public_ip_address}"
    ds_name = dataset_properties(user).name
    copy_scripts_to_ci_cmd = ["scp", "-o", "StrictHostKeyChecking no", "-P", str(ssh_port), f"{HERE}/mount.sh", f'{HERE}/mount_ds.py', f"{ssh_host}:/tmp"]
    chmod_scripts = ["ssh",  "-o", "StrictHostKeyChecking no", "-p", str(ssh_port), str(ssh_host), "chmod +x /tmp/mount.sh"]
    run_mount_scripts_cmd = ["ssh", "-o", "StrictHostKeyChecking no", "-t", "-p", str(ssh_port), str(ssh_host), f'bash -l -c "MOUNT_POINT={mount_point} USER_DATASET_NAME={ds_name} /tmp/mount.sh"']

    for cmd in [copy_scripts_to_ci_cmd, chmod_scripts, run_mount_scripts_cmd]:
        # TODO: This the mount scrip currently relies on the user being log in through the azure cli.
        result = subprocess.run(cmd,  capture_output=True)
        print(result)
