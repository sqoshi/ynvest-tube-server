#!/usr/bin/bash
sudo apt-get install redis
redis-cli ping
sudo apt-get install python3
sudo apt-get install python3-pip
pip install virtualenv
virtualenv -q -p /usr/bin/python3 venv
source venv/bin/activate
venv/bin/pip install -r requirements.txt
python manage.py makemigrations
python manage.py migrate