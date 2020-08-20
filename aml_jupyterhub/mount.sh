#!/usr/bin/env bash
set -x
cd /tmp
echo "Try mount userspace"

MOUNT_ENV="$HOME/.mountenv"

if mountpoint $MOUNT_POINT
then
   echo "already mounted - early exit"
   exit 0
fi

# Init conda
eval "$('conda' 'shell.bash' 'hook' 2> /dev/null)"
. /anaconda/etc/profile.d/conda.sh

{ # try activate mount environment
    conda activate $MOUNT_ENV &&
    echo "Activated existing env at ${MOUNT_ENV}"
} || { # else create it
    echo "Failed to activate env at ${MOUNT_ENV}"
    conda create -y -p $MOUNT_ENV pip &&
    conda activate $MOUNT_ENV &&
    wget https://raw.githubusercontent.com/microsoft/AzureFilesFUSE/master/azfilesfuse.py -O $MOUNT_ENV/azfilesfuse.py &&
    wget https://raw.githubusercontent.com/microsoft/AzureFilesFUSE/master/requirements.txt -O $MOUNT_ENV/azfilesfuse-requirements.txt &&
    pip install -r $MOUNT_ENV/azfilesfuse-requirements.txt 
    echo "Created env at ${MOUNT_ENV}"
}

mkdir -p $MOUNT_POINT
echo "Env ready (I hope)"
nohup python ~/.mountenv/azfilesfuse.py $STORAGE_ACCOUNT_NAME $FILE_SHARE_NAME $SAS_TOKEN $MOUNT_POINT >/tmp/nohup.out 2>&1 &
echo "Mount started with nohup. Sleep 15s" 
sleep 7.5 # Not sure this is needed or not.
echo "Output after 7.5s"
cat /tmp/nohup.out
echo "Mount script ends"
