#!/bin/sh
set -eu

# Run DB migrations & collect static before starting the app
cd /app/cove/
. /app/.ve/bin/activate
set -x
python3 manage.py migrate
python3 manage.py collectstatic
