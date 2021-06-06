#!/usr/bin/bash
activate_venv_cmd='source venv/bin/activate'
worker_run_cmd='celery -A ynvest_tube_server worker -l info -B'
beater_run_cmd='celery -A ynvest_tube_server beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler'
django_run_cmd='./manage.py runserver 0.0.0.0:8000'

source venv/bin/activate
gnome-terminal --tab --title="r1" --command="bash -c '$activate_venv_cmd; $worker_run_cmd'"
gnome-terminal --tab --title="r2" --command="bash -c '$activate_venv_cmd; $beater_run_cmd'"
gnome-terminal --tab --title="r3" --command="bash -c '$activate_venv_cmd; $django_run_cmd'"
