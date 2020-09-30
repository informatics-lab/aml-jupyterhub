# aml_jupyterhub

## About

Code work and experiments to integrate Azure Machine Learning with JupyterHub.

`files.py` - Experiment(s) for testing and exploring using Azure File Shares to provide users storage that is private and persistent across instance and workspaces.

`aml_spawner.py` - A JupyterHub spawner that spawns compute instances on Azure Machine Learning.

## How to develop

### Set up your environment vars
copy `env.template` to `.env` and fill in.

You will need a SAS token for the storage account. SAS tokens at File Share level seem unavailable.

Ensure these variables are available when running.

This is the default for a `.env` file in many IDEs but else you could folow one of the suggestions [here](https://gist.github.com/mihow/9c7f559807069a03e302605691f85572) such as `set -o allexport; source .env; set +o allexport`


### Set up your conda environment

`conda env create -f env.yaml`

### Update the conda env

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

## Authenticating the user with the Jupyterhub spawner

### Dummy authenticator

The config files in `deployments/no_auth_spawn_on_aml` and `deployments/no_auth_spawn_on_aml_with_userspaces` use the "DummyAuthenticator" to authenticate the user with the spawner.  (Note that this is different from the authentication that the spawner needs in order to create resources such as Compute Instances).
If you run using one of these config files, you can give any username/password combination you like and you will be logged in.   Note that this username will be stored in a file `jupyterhub_cookie_secrets`, so you may want to delete this file if you later login using a different authentication method.

### Azure Active Directory OAuth

The config file `deployments/azure_ad_auth_spawn_on_aml` allows users to login to Jupyterhub using their Azure Active Directory account.  In order for this to work:
 1) The Jupyterhub spawner needs to be registered as an Application in Azure.
 2) For this to work, the spawner needs to be running on a URL that is accessible to Azure (i.e. not just `localhost`).


#### Test setup

A simple way to accomplish 2) is to use [ngrok](https://ngrok.com/).  If you follow the [instructions](https://dashboard.ngrok.com/get-started/setup) to download and unzip the free ngrok executable, you can then do:
```
./ngrok http 8000
```
and it will provide a "Forwarding" URL that looks like `https://<some_hex_string>.ngrok.io` from which you (or anyone else) can access whatever is running on `localhost:8000` (which will be our Jupyterhub spawner).
You can then add this forwarding URL, minus the "https://" to the `HOST` value in the `.env` file.

Once this is setup, you can register the Jupyterhub spawner as an Application in the Azure portal [https://portal.azure.com].  Search for the service "Azure Active Directory", then go to "App registrations" on the left sidebar, click on "New Registration", and come up with a descriptive name.  You will then get a `client_id` which you can enter as the `AAD_CLIENT_ID` in `.env`.
Then if you click on "Keys and Secrets" in the left sidebar, you can create a client secret to copy/paste into `AAD_CLIENT_SECRET` in `.env`.
Finally, you need to add the callback URL.  Click on "Authentication" in the left sidebar, then add a "Redirect URI", which will be the ngrok URL described above plus `/hub/oauth_callback`, i.e. something like `https://79604adc24f6.ngrok.io/hub/oauth_callback`.

Later on, if you want to see your app (e.g. to revoke permissions, or update the callback URL), you can find it here [https://myapps.microsoft.com/](https://myapps.microsoft.com/).  

Currently whilst the app authenticates against Azure AD it isn't able yet to use the delegated permissions to act as that user to spin up resources.
In practice this means that when using Azure AD auth, the spawner only works for the individual whose credentials are used in the `.env` file.

## Config / options for the AML Spawner
If you've not got a `jupyterhub_config.py` file generate with `jupyterhub --generate-config`.

Then set the options:

Use AML spawner:
`c.JupyterHub.spawner_class = 'aml_jupyterhub.aml_spawner.AMLSpawner'`

To attempt to mount a persistent users space available across AML workspaces, use:
`c.AMLSpawner.mount_userspace = True`

To set the location on the compute instance on which to mount this, use:
`c.AMLSpawner.mount_userspace_location = "~/userfiles"`
