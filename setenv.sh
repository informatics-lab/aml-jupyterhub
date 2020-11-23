#!/bin/bash

set -o allexport -x

# Specify JupyterHub admin user
JUPYTERHUB_ADMIN=$(az ad signed-in-user show | jq -r '.displayName')
# Set JUPYTERHUB_CRYPT_KEY to persist users information in auth_state
JUPYTERHUB_CRYPT_KEY=$(openssl rand -hex 32)

# Export all variables in `.env` file
source .env

set +o allexport

# do we already have Service Principal variables set?
if [ -z "${AAD_CLIENT_ID}" ] or [ ${AAD_CLIENT_ID} == "Unknown" ]; then
    echo "Will create SP";
    # Create a Service Principal with contributor role
    SP_FILENAME=".az-sp-$SERVICE_PRINCIPAL_NAME.json"

    az ad sp create-for-rbac --name  $SERVICE_PRINCIPAL_NAME \
                         --role contributor \
                         --scopes "/subscriptions/${SUBSCRIPTION_ID}" \
                         --sdk-auth > $SP_FILENAME

    # Export Tenant ID, Client ID, and Client Secret
    set -o allexport
    AAD_TENANT_ID=$(jq -r '.tenantId' $SP_FILENAME)
    AAD_CLIENT_ID=$(jq -r '.clientId' $SP_FILENAME)
    AAD_CLIENT_SECRET=$(jq -r '.clientSecret' $SP_FILENAME)
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
fi;
