# aml_jupyterhub

## About

Code work and experiments to integrate Azure Machine Learning with JupyterHub.

`files.py` - Experiment(s) for testing and exploring using Azure File Shares to provide users storage that is private and persistent across instance and workspaces.

`aml_spawner.py` - A JupyterHub spawner that spawns compute instances on Azure Machine Learning.

## How to develop

### Create a Service Principal
Log in with Azure CLI, then create a SP.
```
az ad sp create-for-rbac --name <sp_name> --skip-assignment --sdk-auth > local-sp.json
```
Use the values of "clientId", "clientSecret", "subscriptionId", "tenantId" to fill the `.env` file and export the variables (a sdescribed below).

Provide RBAC Contributor role to the SP for the entire resource group (to be changed in the future!).
```
az role assignment create --assignee $AAD_CLIENT_ID --role "Contributor” \
    --scope "/subscriptions/$AAD_SUBSCRIPTION_ID/resourceGroups/$RESOURCE_GROUP"
```

### Set up your environment vars
copy `env.template` to `.env` and fill in.

You will need a SAS token for the storage account. SAS tokens at File Share level seem unavailable.

Ensure these variables are available when running.

This is the default for a `.env` file in many IDEs but else you could folow one of the suggestions [here](https://gist.github.com/mihow/9c7f559807069a03e302605691f85572) such as `set -o allexport; source .env; set +o allexport`


### Set up you conda environment

`conda env create -f env.yaml`

### Update the env

If you update the environment (install packages etc) then update the record of it.

`conda env export > env.yaml`
and if necessary, edit the 'name' and 'prefix' fields in the resulting file to remove your local path.


### Running a deployment (for testing)

`python -m jupyterhub -f path_to_deployment_config_file`

i.e.

`python -m jupyterhub -f ${workspaceFolder}/deployments/no_auth_spawn_aml_wtih_userspace/jupyterhub_config.py`

(See below for instructions on how to create and modify a jupyterhub config file.)


Or here is a VS Code debug configuration

```
        {
            "name": "JupyterHub no_auth_spawn_aml",
            "type": "python",
            "request": "launch",
            "module": "jupyterhub",
            "args": ["-f", "${workspaceFolder}/deployments/no_auth_spawn_on_aml/jupyterhub_config.py"]
        }
```

## Azure AD

You can find our app (in order to revoke permission for the app, for testing or other reasons) here [https://myapps.microsoft.com/](https://myapps.microsoft.com/)

The app needs to be available on the web to use AAD OAuth for login. Using [ngrok](https://ngrok.com/) is the easiest way of doing this when running locally.
You will need add the callback url to the AD record for the App in the AzureCLI (the format for this is in `deployments/azure_ad_auth_spawn_aml_with_userspaces/jupyterhub_config.py`). You will also have to add the `HOST` to the `.env` file, if using ngrok this will be something like `d04091ec4cc6.ngrok.io`.ma

Currently whilst the app authenticates against Azure AD it isn't able yet to use the delegated permissions to act as that user to spin up resources.
In practice this means that when using Azure AD auth, the spawner only works for the individual whose credentials are used in the `.env` file.

## Config / options for the AML Spawner
If you've not got a `jupyterhub_config.py` file generate with `jupyterhub --generate-config`.

Then set the options:

Use AZM spawner:
`c.JupyterHub.spawner_class = 'aml_jupyterhub.aml_spawner.AMLSpawner'`

To attempt to mount a persistent users space available across AML workspaces us:
`c.AMLSpawner.mount_userspace = True`

To set the location to mount this use:
`c.AMLSpawner.mount_userspace_location = "~/userfiles"`