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

class AzureAdOAuthenticatorProxy(AzureAdOAuthenticator):
    """
    Custom Authenticator to use Azure AD with JupyterHub.
    This class is just a copy of the AzureAdOAuthenticator
    It's only here for easier debugging whilst I try figure out
    how to use the deligated permissions to act as the signed in user.
    """

    login_service = Unicode(
        os.environ.get('LOGIN_SERVICE', 'Azure AD'),
        config=True,
        help="""Azure AD domain name string, e.g. My College"""
    )

    tenant_id = Unicode(config=True, help="The Azure Active Directory Tenant ID")

    @default('tenant_id')
    def _tenant_id_default(self):
        return os.environ.get('AAD_TENANT_ID', '')

    username_claim = Unicode(config=True)

    @default('username_claim')
    def _username_claim_default(self):
        return 'name'

    @default("authorize_url")
    def _authorize_url_default(self):
        return 'https://login.microsoftonline.com/{0}/oauth2/authorize'.format(self.tenant_id)

    @default("token_url")
    def _token_url_default(self):
        return 'https://login.microsoftonline.com/{0}/oauth2/token'.format(self.tenant_id)

    async def authenticate(self, handler, data=None):
        code = handler.get_argument("code")
        http_client = AsyncHTTPClient()

        params = dict(
            client_id=self.client_id,
            client_secret=self.client_secret,
            grant_type='authorization_code',
            code=code,
            redirect_uri=self.get_callback_url(handler))

        data = urllib.parse.urlencode(
            params, doseq=True, encoding='utf-8', safe='=')

        url = self.token_url

        headers = {
            'Content-Type':
            'application/x-www-form-urlencoded; charset=UTF-8'
        }
        req = HTTPRequest(
            url,
            method="POST",
            headers=headers,
            body=data  # Body is required for a POST...
        )

        resp = await http_client.fetch(req)
        resp_json = json.loads(resp.body.decode('utf8', 'replace'))

        # app_log.info("Response %s", resp_json)
        access_token = resp_json['access_token']

        id_token = resp_json['id_token']
        decoded = jwt.decode(id_token, verify=False)

        userdict = {"name": decoded[self.username_claim]}
        userdict["auth_state"] = auth_state = {}
        auth_state['access_token'] = access_token
        # results in a decoded JWT for the user data
        auth_state['user'] = decoded

        return userdict


c.JupyterHub.authenticator_class = AzureAdOAuthenticatorProxy
# c.JupyterHub.authenticator_class = AzureAdOAuthenticator


c.Application.log_level = 'DEBUG'

c.AzureAdOAuthenticator.tenant_id = os.environ.get('AAD_TENANT_ID')

c.AzureAdOAuthenticator.oauth_callback_url = "https://{os.environ['HOST']}/hub/oauth_callback"
c.AzureAdOAuthenticator.client_id = os.environ['AAD_CLIENT_ID']
c.AzureAdOAuthenticator.client_secret = os.environ['AAD_CLIENT_SECRET']

# The class to use for spawning single-user servers.
c.JupyterHub.spawner_class = 'aml_jupyterhub.aml_spawner.AMLSpawner'

# Options for the AMLSpawner
c.AMLSpawner.mount_userspace = True
c.AMLSpawner.mount_userspace_location = "~/userfiles"