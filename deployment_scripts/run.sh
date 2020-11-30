#!/bin/bash

# This script will be run as the jupyterhub admin user.
# First activate the conda environment, then set env vars, then run jupyterhub

cd /home/${USER}/aml-jupyterhub

# activate the conda environment
/home/${USER}/miniconda/bin/conda init bash
. /home/${USER}/miniconda/etc/profile.d/conda.sh
conda activate azml

# set environment variables needed by the spawner
set -o allexport
source .env
set +o allexport

# Run jupyterhub
nohup python -m jupyterhub -f deployments/azure_ad_auth_spawn_aml/jupyterhub_config.py >& jupyterout.txt &
