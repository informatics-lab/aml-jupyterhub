import tempfile
from azureml.core import Dataset, Workspace
import os
from pathlib import Path

ws = Workspace.from_config()

my_file_ds = Dataset.get_by_name(workspace=ws, name=os.environ['USER_DATASET_NAME'])

# Make the mount point.
mounted_path = os.path.abspath(os.path.expanduser(os.environ['MOUNT_POINT']))
Path(mounted_path).mkdir(parents=True, exist_ok=True)

if len(os.listdir(mounted_path)) > 0:
    raise RuntimeError("f{mounted_path} is not empty. Abort")


# mount dataset onto the mounted_path of a Linux-based compute
mount_context = my_file_ds.mount(mounted_path)
mount_context.start()

print(os.listdir(mounted_path))
print(mounted_path)
