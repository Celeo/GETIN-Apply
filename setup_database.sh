#!/bin/bash
source env/bin/activate
python -c 'from app.app import db; from app.models import *; db.create_all()'
echo "done"
