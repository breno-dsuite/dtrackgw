#!/usr/bin/env bash
cd /home/admin/dtrackgw && git pull
sudo supervisorctl reload
