#!/usr/bin/env bash
sudo apt-get install python3-pip supervisor

#Reiniciar depois de instalar supervisor e testar se serviço ainda ativo
#sudo nano /etc/supervisor/supervisord.conf 
#Colocar user=root em supervisord

pip3 install pyusb
pip3 install requests
pip3 install boto3

sudo groupadd usbusers
sudo usermod -a -G usbusers admin

echo 'SUBSYSTEM=="usb", MODE="0666", GROUP="usbusers"' | sudo tee /etc/udev/rules.d/99-usbusers.rules
# Try to reload - if that does not work, reboot!
sudo udevadm control --reload
sudo udevadm trigger

# Print confirmation
echo "USB device configuration has been installed. Please log out and log back in or reboot"

