# !/bin/bash

# This script will be called during the deployment process with the following args:
# vm-admin-username  subscription_id  location  tenant_id  client_id  client_secret run_script

# redirect port 443 (https) to port 8000
iptables -t nat -I PREROUTING -p tcp --dport 443 -j REDIRECT --to-ports 8000 

echo " ${1} ${2} ${3} ${4} ${5} ${6} ${7} ${8}" > /home/aml-jupyterhub-admin/vartest.txt
cd /home/${1}

# install miniconda
wget https://repo.continuum.io/miniconda/Miniconda3-latest-Linux-x86_64.sh -O ~/miniconda.sh
bash ~/miniconda.sh -b -p /home/${1}/miniconda

#export PATH=/home/${1}/miniconda/bin:$PATH
echo "about to do conda init bash"
/home/${1}/miniconda/bin/conda init bash
. /home/${1}/miniconda/etc/profile.d/conda.sh
echo $PATH > path1.txt

# clone the aml-jupyterhub repo
git clone https://github.com/informatics-lab/aml-jupyterhub

# create the conda environment
cd aml-jupyterhub
/home/${1}/miniconda/bin/conda env create -f env.yaml

# clone the aml-jupyterhub repo and create the conda environment
chown -R ${1}:${1} /home/${1}/miniconda
chown -R ${1}:${1} /home/${1}/aml-jupyterhub

# download the run script, and save as run.sh
wget ${8} -O run.sh
# call the run script - run it as vm-admin-username
sudo -u ${1} bash run.sh ${2} ${3} ${4} ${5} ${6} ${7}






#nohup python -m jupyterhub -f deployments/azure_ad_auth_spawn_aml/jupyterhub_config.py >& jupyterout.txt &
sudo -u ${1} nohup python -m jupyterhub -f deployments/azure_ad_auth_spawn_aml/jupyterhub_config.py & # >& jupyterout.txt &

#curl https://raw.githubusercontent.com/jupyterhub/the-littlest-jupyterhub/master/bootstrap/bootstrap.py \
#| sudo python3 - --admin ${1}
