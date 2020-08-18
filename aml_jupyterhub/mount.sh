#!/usr/bin/env bash
set -ex
cd /tmp
nohup python mount_ds.py >/tmp/nohup.out 2>&1 &
echo "no hupping"
sleep 45
tail /tmp/nohup.out