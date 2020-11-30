# !/bin/bash

# This script will be called during the deployment process with the
# following args in order:
# 1) vm-admin-username
# 2) subscription_id
# 3) location
# 4) tenant_id
# 5) client_id
# 6) client_secret
# 7) dns_prefix
# 8) run_script

# The script is run as root, but will install things to the home
# area of the admin user specified in the deployment.
# At the end, the 'run.sh' script will be run as that user.
###################################################################

# install jq so we can query json output
apt update; apt install jq

# install the Azure CLI
curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash

# Set a few variables here for clarity
USERNAME=${1}
HOST="${7}.${3}.cloudapp.azure.com"

# Change to the user's home directory
cd /home/${USERNAME}

# redirect port 443 (https) to port 8000
iptables -t nat -I PREROUTING -p tcp --dport 443 -j REDIRECT --to-ports 8000
iptables -L -t nat > iptables.txt


# install miniconda
wget https://repo.continuum.io/miniconda/Miniconda3-latest-Linux-x86_64.sh -O ~/miniconda.sh
bash ~/miniconda.sh -b -p /home/${1}/miniconda

/home/${USERNAME}/miniconda/bin/conda init bash
. /home/${USERNAME}/miniconda/etc/profile.d/conda.sh

# clone the aml-jupyterhub repo
git clone https://github.com/informatics-lab/aml-jupyterhub

# Install certbot/letsencrypt
git -C /usr/local/etc clone https://github.com/certbot/certbot.git
ln -t /usr/local/bin/ /usr/local/etc/certbot/letsencrypt-auto

letsencrypt-auto certonly --standalone --agree-tos -m email@example.co.uk --no-eff-email -d $HOST
# Change permission to makekey and cert visible to jupyterhub
chown -R ${USERNAME}: /etc/letsencrypt/live/ /etc/letsencrypt/archive/

# create the conda environment
cd aml-jupyterhub
/home/${USERNAME}/miniconda/bin/conda env create -f env.yaml

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
echo "JUPYTERHUB_ADMIN=${USERNAME}" >> .env
echo "JUPYTERHUB_CRYPT_KEY=$(openssl rand -hex 32)" >> .env
echo "SSL_KEY=/etc/letsencrypt/live/$HOST/privkey.pem" >> .env
echo "SSL_CERT=/etc/letsencrypt/live/$HOST/fullchain.pem" >> .env

# clone the aml-jupyterhub repo and create the conda environment
chown -R ${USERNAME}:${USERNAME} /home/${USERNAME}/miniconda
chown -R ${USERNAME}:${USERNAME} /home/${USERNAME}/aml-jupyterhub

# download the run script, and save as run.sh
wget ${8} -O run.sh
# call the run script - run it as vm-admin-username
sudo -u ${USERNAME} bash run.sh
