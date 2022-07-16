#!/usr/bin/env bash
cd /home/admin/dtrackgw && git pull
sudo cp /home/admin/dtrackgw/dtrackgw.conf /etc/supervisor/conf.d/dtrackgw.conf
sudo supervisorctl reload
