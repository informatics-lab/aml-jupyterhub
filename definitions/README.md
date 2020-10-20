# Minimal user role to get access to spawned CIs

## About
The role definition in `restrictive.json` specifies the only action required by a user (already added in the subscription `1fedcbc3-e156-45f5-a034-c89c2fc0ac61`) to access a CI spawned by JupyterHub.

## How to create the role:
```
az role definition create --role-definition restrictive.json
```

## How to assign the role to a user:
Assign the restrictive role to a user on all resources in a resource group.
```
az role assignment create --role "Data Scientist Restrictive" --assignee <user_object_ID> --scope "/subscriptions/1fedcbc3-e156-45f5-a034-c89c2fc0ac61/resourceGroups/<resource_group_name>"
```
