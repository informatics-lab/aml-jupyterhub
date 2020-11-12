# !/bin/bash

# This script will be called during the deployment process with the following args:
# vm-admin-username  subscription_id  location  tenant_id  client_id  client_secret

#echo ${1} > /home/aml-jupyterhub-admin/tenantId.txt
cd /home/${1}

# set environment variables needed by the spawner
set -o allexport
SUBSCRIPTION_ID=${2}
LOCATION=${3}
AAD_TENANT_ID=${4}
AAD_CLIENT_ID=${5}
AAD_CLIENT_SECRET=${6}
set +o allexport
# clone the aml-jupyterhub repo and create the conda environment
git clone https://github.com/informatics-lab/aml-jupyterhub
cd aml-jupyterhub
conda env create -y -f env.yaml
conda activate azml
# run jupyterhub with our custom spawner
python -m jupyterhub -f deployments/azure_ad_auth_spawn_aml/jupyterhub_config.py

#curl https://raw.githubusercontent.com/jupyterhub/the-littlest-jupyterhub/master/bootstrap/bootstrap.py \
#| sudo python3 - --admin ${1}
