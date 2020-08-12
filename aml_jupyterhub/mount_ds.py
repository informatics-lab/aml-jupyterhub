import tempfile
from azureml.core import Dataset, Workspace
import os

ws = Workspace.from_config()

my_file_ds = Dataset.get_by_name(workspace=ws, name=os.environ['USER_DATASET_NAME'])

# File datasets can be mounted:
mounted_path = tempfile.mkdtemp()

# mount dataset onto the mounted_path of a Linux-based compute
mount_context = my_file_ds.mount(mounted_path)
mount_context.start()

print(os.listdir(mounted_path))
print(mounted_path)
