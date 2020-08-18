# aml_jupyterhub

## About

Code work and experiments to integrate Azure Machine Learning with JupyterHub.

`files.py` - Experiment(s) for testing and exploring using Azure File Shares to provide users storage that is private and persistent across instance and workspaces.

`aml_spawner.py` - A JupyterHub spawner that spawns compute instances on Azure Machine Learning.

## How to develop

### Set up your environment vars
copy `env.template` to `.env` and fill in.

Ensure these variables are available when running.

This is the default for a `.env` file in many IDEs but else you could folow one of the suggestions [here](https://gist.github.com/mihow/9c7f559807069a03e302605691f85572) such as `set -o allexport; source .env; set +o allexport`


### Set up you conda environment

`conda create --from-file env.yaml`

### Up date the env

If you update the environment (install packages etc) then update the record of it.

`conda env export > env.yaml`

### Running a deployment (for testing)

`python -m jupyterhub -f path_to_deployment_config_file`

i.e.

`python -m jupyterhub -f ${workspaceFolder}/deployments/no_auth_spawn_aml_wtih_userspace/jupyterhub_config.py`


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