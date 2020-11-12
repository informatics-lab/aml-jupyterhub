# !/bin/bash

echo ${1} > tenantId.txt
git clone https://github.com/informatics-lab/aml-jupyterhub

#curl https://raw.githubusercontent.com/jupyterhub/the-littlest-jupyterhub/master/bootstrap/bootstrap.py \
#| sudo python3 - --admin ${1}
