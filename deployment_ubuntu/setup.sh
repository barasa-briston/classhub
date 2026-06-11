#!/bin/bash

# Update and install system dependencies
sudo apt update
sudo apt install -y python3-pip python3-venv nginx curl

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install python dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Create media and static directories
mkdir -p ../lms/media ../lms/staticfiles
chmod -R 775 ../lms/media ../lms/staticfiles
sudo chown -R ubuntu:www-data ../lms/media ../lms/staticfiles

# Initial migrations and static collection
cd ../lms
../deployment_ubuntu/venv/bin/python manage.py collectstatic --noinput
../deployment_ubuntu/venv/bin/python manage.py migrate

echo "Setup complete! Please configure Gunicorn and Nginx using the provided config files."
