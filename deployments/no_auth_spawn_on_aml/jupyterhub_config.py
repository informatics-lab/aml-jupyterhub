# Configuration file for basic jupyterhub spawner, running locally, no mounted user space

# The dummy authenticator will ask the user for username/password, but these
# won't be authenticated against anything
c.JupyterHub.authenticator_class = 'dummyauthenticator.DummyAuthenticator'


# Specify the spawner class
c.JupyterHub.spawner_class = 'aml_jupyterhub.aml_spawner.AMLSpawner'
