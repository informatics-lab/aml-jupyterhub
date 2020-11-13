# !/bin/bash

# This script will be called during the deployment process with the following args:
# vm-admin-username  subscription_id  location  tenant_id  client_id  client_secret

echo " ${1} ${2} ${3} ${4} ${5} ${6}" > /home/aml-jupyterhub-admin/vartest.txt
cd /home/${1}

# set environment variables needed by the spawner
set -o allexport
JUPYTERHUB_ADMIN=${1}
SUBSCRIPTION_ID=${2}
LOCATION=${3}
AAD_TENANT_ID=${4}
AAD_CLIENT_ID=${5}
AAD_CLIENT_SECRET=${6}
set +o allexport

printenv > environment.txt

# install miniconda
wget https://repo.continuum.io/miniconda/Miniconda3-latest-Linux-x86_64.sh -O ~/miniconda.sh
bash ~/miniconda.sh -b -p /home/${1}/miniconda
#export PATH=/home/${1}/miniconda/bin:$PATH
echo "about to do conda init bash"
/home/${1}/miniconda/bin/conda init bash
. /home/${1}/miniconda/etc/profile.d/conda.sh
echo $PATH > path1.txt

# clone the aml-jupyterhub repo and create the conda environment



git clone https://github.com/informatics-lab/aml-jupyterhub
cd aml-jupyterhub
/home/${1}/miniconda/bin/conda env create -f env.yaml
#bash
conda activate azml
#/home/${1}/miniconda/bin/conda activate azml
# run jupyterhub with our custom spawner
echo $PATH > path2.txt
echo `which python` >> path2.txt


python -m jupyterhub --port 80 -f deployments/azure_ad_auth_spawn_aml/jupyterhub_config.py &

#curl https://raw.githubusercontent.com/jupyterhub/the-littlest-jupyterhub/master/bootstrap/bootstrap.py \
#| sudo python3 - --admin ${1}
