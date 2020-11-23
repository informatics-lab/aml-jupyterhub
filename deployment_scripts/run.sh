#!/bin/bash

cd /home/${USER}/aml-jupyterlab
echo "about to do conda init bash"
/home/${USER}/miniconda/bin/conda init bash
. /home/${USER}/miniconda/etc/profile.d/conda.sh
echo $PATH > path3.txt

conda activate azml

# set environment variables needed by the spawner
set -o allexport -x
# Specify JupyterHub admin user
JUPYTERHUB_ADMIN=${USER}
set +o allexport

source setenv.sh

printenv > environment.txt

echo $PATH > path2.txt
echo `which python` >> path2.txt



nohup python -m jupyterhub -f deployments/azure_ad_auth_spawn_aml/jupyterhub_config.py >& jupyterout.txt &
