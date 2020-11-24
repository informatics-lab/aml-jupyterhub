# !/bin/bash

# This script will be called during the deployment process with the following args:
# vm-admin-username  subscription_id  location  tenant_id  client_id  client_secret dns_prefix run_script

# install jq so we can query json output
apt update; apt install jq

# install the Azure CLI
curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash


echo " ${1} ${2} ${3} ${4} ${5} ${6} ${7} ${8}" > /home/aml-jupyterhub-admin/vartest.txt
HOST="${7}.${3}.cloudapp.azure.com"
cd /home/${1}

# redirect port 443 (https) to port 8000
iptables -t nat -I PREROUTING -p tcp --dport 443 -j REDIRECT --to-ports 8000
iptables -L -t nat > iptables.txt


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

# Install certbot/letsencrypt
git -C /usr/local/etc clone https://github.com/certbot/certbot.git
ln -t /usr/local/bin/ /usr/local/etc/certbot/letsencrypt-auto

letsencrypt-auto certonly --standalone --agree-tos -m email@example.co.uk --no-eff-email -d $HOST
# Change permission to makekey and cert visible to jupyterhub
chown -R ${1}: /etc/letsencrypt/live/ /etc/letsencrypt/archive/
# chmod 600 /etc/letsencrypt/archive/$HOST/privkey1.pem 

# create the conda environment
cd aml-jupyterhub
/home/${1}/miniconda/bin/conda env create -f env.yaml

# write environment vars to .env file
rm -f .env
echo "# set environment vars here" > .env
echo "SUBSCRIPTION_ID=${2}" >> .env
echo "LOCATION=${3}" >> .env
echo "SERVICE_PRINCIPAL_NAME=aml_jupyterhub_sp" >> .env
echo "AAD_TENANT_ID=${4}" >> .env
echo "AAD_CLIENT_ID=${5}" >> .env
echo "AAD_CLIENT_SECRET=${6}" >> .env
echo "HOST=$HOST" >> .env
echo "JUPYTERHUB_ADMIN=${1}" >> .env
echo "SSL_KEY=/etc/letsencrypt/live/$HOST/privkey.pem" >> .env
echo "SSL_CERT=/etc/letsencrypt/live/$HOST/fullchain.pem" >> .env

# clone the aml-jupyterhub repo and create the conda environment
chown -R ${1}:${1} /home/${1}/miniconda
chown -R ${1}:${1} /home/${1}/aml-jupyterhub

# download the run script, and save as run.sh
wget ${8} -O run.sh
# call the run script - run it as vm-admin-username
sudo -u ${1} bash run.sh   # ${2} ${3} ${4} ${5} ${6} ${7}
