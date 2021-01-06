## Using the "Deploy to Azure" button.

The [ARM template](https://docs.microsoft.com/en-us/azure/azure-resource-manager/templates/overview) in the file [azuredeploy.json](azuredeploy.json) makes it easy to deploy a Virtual Machine running the custon Jupyterhub spawner on Azure, by clicking the "Deploy to Azure" button, and then filling out the various fields in the Azure portal.

However, for this to work, it is necessary to have an "App Registration" in Azure, with the correct set of permissions.   Depending on the privileges you have on the Azure subscription, you may be able to do this yourself.  Otherwise, you will need to ask the administrators of your organization's Azure account to do this.   

The following instructions (steps 1 to 4) assume that you have the necessary privileges.  If you do not, please see the section "What to ask the Azure account administrators for" at the bottom.

### 1) Create an App Registration

 * In the Azure portal, search for "App registrations" and click on the icon.
 * Select *"+ New registration"*.
 * Give it a NAME (doesn't matter too much what this is, but remember it for the next step), leave the default option for *"Supported account types"* to be only accounts in the same organizational directory, and set the *"Redirect URI"* to be
 ```
 https://DOMAIN_NAME_LABEL.LOCATION.cloudapp.azure.com/hub/oauth_callback
 ```
 where "LOCATION" is the Azure region you want to use (e.g. "uksouth", "eastus", ...).  For "DOMAIN_NAME_LABEL", choose a (unique for this region) name that will form the first part of the hub's URL.  You will also need to remember this for when you fill out the fields after clicking the "Deploy to Azure" button. Click *"Register"* at the bottom of the screen.

### 2) Give permissions and roles to the app

After the steps above, you should be on the *"Overview"* page of your newly registered app.
 * Click on *"App roles | Preview"* on the left, and click *"+ Create app role"*.
 Put something like "User read" in the *"Display name"*, click "Applications" for *"Allowed member types"*, and "User.Read" in the *"Value"* box.  In the *"Description"* box you can put something like "Give the application rights to create AML resources on behalf of a user".   Click *"Apply"* at the bottom of the screen.
 * You will want to come back to the "Overview" page of your app later, so you can do the next step in a new tab, or just use the "back" button.  Go back to "Home" in your Azure portal, and search for and click on *"Subscriptions"*, then click on your subscription.
 * Click on *"Access control (IAM)"* on the left of the screen.
 * Click *"Add role assignements"* in the "Grant access to this resource" box.  For *"Select a role"*, choose "Contributor".   For *"Assign access to"*, choose the option "User, group, or service principal".   Then in the search box for *"Select"*, start typing the NAME of the app you registered in the previous step.  Click *"Save"* at the bottom of this screen.

### 3) Fill out the fields in the Azure portal after clicking the "Deploy to Azure" button.
 * You will want to have one browser tab back at the "Overview" page of the app registration you created in the first step.
 * Choose the Azure subscription you want to use, and either choose an existing resource group or create a new one.   Note that the *"Region"* of the resource group must match the "LOCATION" you specified in the "redirect URL" of your App Registration.
 * You can leave the *"Virtual Machine Name"* and *"Admin Username"* as the default values.
 * Copy/paste an SSH public key into the *"Admin Public Key"* field.  If you don't already have one of these, you can create one with the command ```ssh-keygen``` on Mac or Linux systems.  The key that you paste into the box should start with "ssh-rsa" and end with "== <some-email-address>".   Note that this is only needed if you want to SSH into the VM, which may not be necessary, but on the other hand if you don't put a valid SSH key in here, you won't be able to SSH to it via any other means later on.
 * In the *"Domain Name Label"* field, put the "DOMAIN_NAME_LABEL" that you created in the last step of 1).
 * For *"Tenant Id"* and *"Client Id"*, you can copy/paste these from the "Overview" page of your App Registration.
 * For the *"Client Secret"*, go to the "Overview" page of your App Registration, and click *"Certificates & secrets"* on the left.  In the middle of the screen, click *"+ New client secret"*.  Set an expiry date, e.g. 1 year, then click "Add".  A new entry should appear under "Client secrets".   Copy the *"Value"* of it, and paste into the *"Client secret"* field of your deployment.
 * Click *"Review + create"* and then *"Create"*.
 * It should take 5-10 minutes for the deployment to complete (most of this is provisioning the VM and running the installation script).
 * When this is done, you can click *"Go to resource group"*, find the Virtual Machine (whose name will be "AML-Jupyterhub" unless you changed it), and clicking on this should take you to its "Overview" page.  Towards the top right, you should see a *"DNS name"*.   Clicking on this will take you to the URL of your Jupyterhub, and hopefully a login page.
 
 ## If you don't have rights to create an "App Registration" yourself, what should you ask your Azure admins for?
 
 You should ask your friendly admins to create an "App Registration" for you.   The information they will need is:
  * Azure Subscription - what subscription to use for this app.
  * App name - this can be anything you like.
  * Required privileges - the app will need a "Service Principal", which has "Contributor" role on the Subscription, and the app needs the "User.Read" role.
  * Callback URL - this will be https://DOMAIN_NAME_LABEL.LOCATION.cloudapp.azure.com/hub/oauth_callback where DOMAIN_NAME_LABEL is a name you choose yourself (must be unique to the Azure region), and LOCATION is the Azure region (e.g. "uksouth", "westeurope").
  * You will need them to create a "Client Secret" for the app.
  
  Once the admins have created the app registration, they should be able to provide you with the following bits of information, that you can then use to fill out the fields in the form as in Step 3) above:
   * Client ID - This might also be known as "Object ID".
   * Client Secret - the "value" of the Secret, not the ID.
   * Tenant ID - though it is also possible to find this out through other means e.g. `az account show` in the Azure CLI.
   
   
 
 
