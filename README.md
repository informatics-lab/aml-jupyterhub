# aml_jupyterhub


## About

Code work and experiments to integrate Azure Machine Learning with JupyterHub.
* `aml_jupyterhub/aml_spawner.py` - Custom JupyterHub spawner that spawns compute instances on Azure Machine Learning.
* `deployments/azure_ad_auth_spawn_aml/jupyterhub_config.py` - JupyterHub configuration file

## How to deploy on Azure

This repository contains an "ARM template" which can be used via the button below to deploy a JupyterHub spawner on Azure.  See [here](deploytoazure.md) for more details.

<table style="width:auto; margin-left:auto; margin-right:auto;">
 <tr>
 <td align='center' width='100%'>
 <a href="https://portal.azure.com/#create/Microsoft.Template/uri/https%3A%2F%2Fraw.githubusercontent.com%2Finformatics-lab%2Faml-jupyterhub%2Ffeature%2Fdeploy-to-azure-button%2Fazuredeploy.json" target="_blank">
 <img src="https://raw.githubusercontent.com/Azure/azure-quickstart-templates/master/1-CONTRIBUTION-GUIDE/images/deploytoazure.svg?sanitize=true"/>
 </td>
 </tr>
 </table>

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
or, when JupyterHub is running with SSL encryption,
```
./ngrok http https://localhost:8000
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


## Naming (and other) conventions

It is desirable to make this deployment as user-friendly as possible, and also make use of cloud-agnostic concepts in the user-facing side (i.e. refer to "Projects" as opposed to Azure-specific terms "Resource Groups" or "Workspaces").
Behind the scenes, the following mapping is applied:

 * One Project will be correspond to one Azure Resource Group, and that Resource Group will contain one AML Workspace.  Both the Resource Group and the Workspace will have the same name as the Project.
 * The VMs that the user will spin up will be labelled "Small", "Medium", "Large", or "GPU", and these are mapped to sizes of Azure VMs available in the same Azure region of the Resource Group.
 * The *name* of this VM (the Compute Instance) needs to be unique in the region, but we also want it to be deterministic for a given user/project/VM size.  There is also a limit of 24 characters on the Compute Instance name, and they must start with letters.  We therefore concatenate the username, the project name, and the VM size, take an MD5 hash, and append the first 21 characters of this to the string "ci-".  We then use this as the Compute Instance name.
 * *TEMPORARY* When offering the user a choice of Project (i.e. Resource Group), the app can currently see all Resource Groups in the Subscription.   We want to filter this list to only include the Resource Groups on which the user has certain Roles.   As a temporary measure, we are instead filtering this list to only show Resource Groups that have "Pangeo" in their name.