# Environmental Variables
Following the instructions in [README](https://github.com/informatics-lab/aml-jupyterhub/tree/master/README.md), copy the file `env.template` to `.env` and fill in the variables:

## Current mandatory variables
* SUBSCRIPTION_ID - in the [Azure portal](https://portal.azure.com) you can click on "Subscriptions", and find the ID (the long hex string) for the one you want.
* LOCATION - the Azure region where the resources are located, e.g. "uksouth", or "westeurope".
* SPAWN_TO_WORK_SPACE - the name of an AML Workspace (will be created if it doesn't already exist).
* SPAWN_TO_COMPUTE_INSTANCE_SUFFIX - suffix will be appended to the name of the Compute Instance that is created.
* RESOURCE_GROUP - the name of the Azure Resource Group containing the resources used here. If it does not exist it will be created automatically (in the [Azure portal](https://portal.azure.com) - search for "Resource Groups").
* HOST - The host name where this app is hosted (e.g. 'localhost:8888', 'd04091ec4cc6.ngrok.io', 'hub.mydomain.co.uk'). When authenticating with Azure Active Directory this should be an URL accessible to azure (i.e. not just `localhost` - check the ["Expose a local server"](README.md#expose-a-local-server) section for more details)

## Authentication variables
The following variables are are used to authenticate the app with Azure Active Directory. Previously, these had to be set up manually, by checking their values on Azure portal. The current implementation just requires the user to source the [`setenv.sh`](setenv.sh) script before launching the JupyterHub server - it automates the creation of a Service Principal and retrieves these values from the SP details.
* AAD_TENANT_ID - this can be found in the [Azure portal](https://portal.azure.com) if you search for and click on "Azure Active Directory", there will be a panel named "Tenant information", with "Tenant ID" in.
* AAD_CLIENT_ID, AAD_CLIENT_SECRET - these are used when using the Azure Active Directory OAuth authentication to log the user into Jupyterhub.  For this to work, the jupyterhub spawner needs to be registered as an Application in the Azure Portal (go to "Azure Active Directory", then "App Registration", and fill in the fields to register the app.  The "Client id" will then be on the overview panel for the app.  To generate a "Client secret", click on "Certificates and secrets" on the left sidebar, and click "+ New client secret".
