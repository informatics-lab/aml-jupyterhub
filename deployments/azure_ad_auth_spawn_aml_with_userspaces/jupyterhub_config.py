# Configuration file for jupyterhub.

# Use `jupyterhub --generate-config` to generate a default config file

# Class for authenticating users.

import os
import json
import jwt
import os
import urllib

from tornado.auth import OAuth2Mixin
from tornado.log import app_log
from tornado.httpclient import HTTPRequest, AsyncHTTPClient

from jupyterhub.auth import LocalAuthenticator
from traitlets import Unicode, default
from oauthenticator.azuread import AzureAdOAuthenticator

c.JupyterHub.authenticator_class = AzureAdOAuthenticator

c.Application.log_level = 'DEBUG'

c.AzureAdOAuthenticator.tenant_id = os.environ.get('AAD_TENANT_ID')

c.AzureAdOAuthenticator.oauth_callback_url = f"https://{os.environ['HOST']}/hub/oauth_callback"
c.AzureAdOAuthenticator.client_id = os.environ['AAD_CLIENT_ID']
c.AzureAdOAuthenticator.client_secret = os.environ['AAD_CLIENT_SECRET']


# The class to use for spawning single-user servers.
c.JupyterHub.spawner_class = 'aml_jupyterhub.aml_spawner.AMLSpawner'

# Options for the AMLSpawner
c.AMLSpawner.mount_userspace = True
c.AMLSpawner.mount_userspace_location = "~/userfiles"
