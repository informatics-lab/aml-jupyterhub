# aml_jupyterhub

## About

Code work and experiments to integrate Azure Machine Learning with JupyterHub.
* `aml_jupyterhub/aml_spawner.py` - Custom JupyterHub spawner that spawns compute instances on Azure Machine Learning.
* `deployments/azure_ad_auth_spawn_aml/jupyterhub_config.py` - JupyterHub configuration file

## How to develop

### Set up your conda environment
To create a new conda environment with all the required dependencies:
```
conda env create -f env.yaml
```
If you update the environment (install packages etc) then update the record of it by `conda env export > env.yaml`.
If necessary, edit the 'name' and 'prefix' fields in the resulting file to remove your local path.

### Set up your environment vars
Copy `env.template` to `.env` and fill in. See [here](environmentvars.md) for an explanation of the parameters, and where to find them.

#### Expose a local server
In order to allow users authentication by their Azure Active Directory account, the spawner needs to be running on a URL that is accessible to Azure (i.e. not just `localhost`).

A simple way to expose your local server to the public internet is to use [ngrok](https://ngrok.com/).  If you follow the [instructions](https://dashboard.ngrok.com/get-started/setup) to download and unzip the free ngrok executable, you can then do:
```
./ngrok http 8000
```
and it will provide a "Forwarding" URL that looks like `https://<some_hex_string>.ngrok.io` from which you (or anyone else) can access whatever is running on `localhost:8000` (which will be our Jupyterhub spawner).
You can then add this forwarding URL, minus the "https://" to the `HOST` value in the `.env` file.

### Set up the resources
From the command line,
```
source setenv.sh
```
This script exports the variables in `.env` (if the specified Resource Group and Workspace do not already exist, it will create them). Moreover, a Service Principal is automatically created and granted *contributor* role on the resource group (needed by the Spawner) and permission to read the profile of the signed-in user (needed by the Authenticator). Both the JupyterHub's Authenticator and Spawner authenticate themselves with Azure Active Directory using this SP.

Later on, if you want to see your app (e.g. to revoke permissions, or update the callback URL), you can find it here [https://myapps.microsoft.com/](https://myapps.microsoft.com/).  

### Running a deployment
To launch a JupyterHub server:
```
python -m jupyterhub -f ${workspaceFolder}/deployments/azure_ad_auth_spawn_aml/jupyterhub_config.py
```

## Config / options for the AML Spawner
If you want to create a new `jupyterhub_config.py` file, you can generate one with `jupyterhub --generate-config`.

Then set the following option to use the AML spawner:

`c.JupyterHub.spawner_class = 'aml_jupyterhub.aml_spawner.AMLSpawner'`
