#!/bin/bash

set -o allexport -x
# Export all variables in `.env` file
source .env
# Set JUPYTERHUB_CRYPT_KEY to persist users information in auth_state
JUPYTERHUB_CRYPT_KEY=$(openssl rand -hex 32)
set +o allexport

# Create resource group if it does not exist
if ! `az group exists -n $RESOURCE_GROUP`
    then az group create -l $LOCATION -n $RESOURCE_GROUP
fi

# Create a Service Principal with contributor role on resource group
SP_NAME='pangeong-tmp-sp'
SP_FILENAME=".$SP_NAME.json"

az ad sp create-for-rbac --name  $SP_NAME \
                         --role contributor \
                         --scopes "/subscriptions/$SUBSCRIPTION_ID/resourceGroups/$RESOURCE_GROUP" \
                         --sdk-auth > $SP_FILENAME

# Export Tenant ID, Client ID, and Client Secret
set -o allexport
AAD_TENANT_ID=$(jq -r '.tenantId' $SP_FILENAME)
AAD_CLIENT_ID=$(jq -r '.clientId' $SP_FILENAME)
AAD_CLIENT_SECRET=$(jq -r '.clientSecret' $SP_FILENAME)

# rm $SP_FILENAME
set +o allexport

# Add Azure Active Directory Graph delegated permission `User.Read`
az ad app permission add --id=$AAD_CLIENT_ID \
                         --api="00000002-0000-0000-c000-000000000000" \
                         --api-permissions="311a71cc-e848-46a1-bdf8-97ff7156d8e6=Scope"
# Grant the app an API Delegated permissions with default expiration in 1 year
az ad app permission grant --id=$AAD_CLIENT_ID \
                           --api="00000002-0000-0000-c000-000000000000"
# Set reply-URL
az ad app update --id=$AAD_CLIENT_ID \
                 --reply-urls="https://$HOST/hub/oauth_callback"

set +x

