#!/bin/bash
source env/bin/activate
FLASK_ENV=development FLASK_APP=app/app.py flask run
