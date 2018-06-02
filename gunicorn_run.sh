#!/bin/bash
source env/bin/activate
gunicorn -w 3 -b 127.0.0.1:5000 app:app
