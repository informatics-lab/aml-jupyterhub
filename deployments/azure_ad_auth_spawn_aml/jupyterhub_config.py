# Configuration file for jupyterhub.

# Use `jupyterhub --generate-config` to generate a default config file

# Class for authenticating users.

import os

from oauthenticator.azuread import AzureAdOAuthenticator

c.Application.log_level = 'DEBUG'

c.Authenticator.admin_users = {os.environ['JUPYTERHUB_ADMIN']}

c.JupyterHub.authenticator_class = AzureAdOAuthenticator

c.AzureAdOAuthenticator.enable_auth_state = True
c.AzureAdOAuthenticator.oauth_callback_url = f"https://{os.environ['HOST']}/hub/oauth_callback"
c.AzureAdOAuthenticator.client_id = os.environ['AAD_CLIENT_ID']
c.AzureAdOAuthenticator.client_secret = os.environ['AAD_CLIENT_SECRET']
c.AzureAdOAuthenticator.tenant_id = os.environ.get('AAD_TENANT_ID') # Not necessary

# The class to use for spawning single-user servers.
c.JupyterHub.spawner_class = 'aml_jupyterhub.aml_spawner.AMLSpawner'

# c.JupyterHub.shutdown_on_logout = True
c.JupyterHub.allow_named_servers = True
c.JupyterHub.redirect_to_server = False

try:
    c.JupyterHub.ssl_cert = os.environ['SSL_CERT']
    c.JupyterHub.ssl_key = os.environ['SSL_KEY']
    # c.JupyterHub.port = 443
except:
    print("JupyterHub is running without SSL encryption!")
c.JupyterHub.cleanup_servers = False