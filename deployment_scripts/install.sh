# !/bin/bash

echo ${1} > /home/aml-jupyterhub-admin/tenantId.txt
cd /home/aml-jupyterhub-admin
git clone https://github.com/informatics-lab/aml-jupyterhub

#curl https://raw.githubusercontent.com/jupyterhub/the-littlest-jupyterhub/master/bootstrap/bootstrap.py \
#| sudo python3 - --admin ${1}
