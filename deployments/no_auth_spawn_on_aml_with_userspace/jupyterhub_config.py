# Configuration file for jupyterhub.
# Use `jupyterhub --generate-config` to generate a default config file

# Class for authenticating users.
import os

c.JupyterHub.authenticator_class = 'dummyauthenticator.DummyAuthenticator'

# The class to use for spawning single-user servers.
c.JupyterHub.spawner_class = 'aml_jupyterhub.aml_spawner.AMLSpawner'

# Options for the AMLSpawner
c.AMLSpawner.mount_userspace = True
c.AMLSpawner.mount_userspace_location = "~/userfiles"

# Custom templates from the aml_jupyterhub module
t_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'aml_jupyterhub', 'templates'))
c.JupyterHub.template_paths = [t_path]