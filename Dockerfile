# See the upstream documentation for how this nginx+uwsgi Python image works
# It's based on Debian 11 Bullseye which is supported until August 31st, 2026
#
# https://github.com/tiangolo/uwsgi-nginx-docker
#
FROM tiangolo/uwsgi-nginx:python3.12

# Create virtualenv
RUN python3 -m venv /app/.ve
RUN . /app/.ve/bin/activate && pip install --no-cache-dir --upgrade pip wheel setuptools

# Copy in setup & install requirements
COPY tools/ /app/tools/
COPY lib360dataquality/ /app/lib360dataquality/
COPY setup.py requirements_cove.txt LICENCE AUTHORS /app/

RUN . /app/.ve/bin/activate && pip install --no-cache-dir --upgrade -r /app/requirements_cove.txt

# Copy in the application code
COPY cove/ /app/cove/

# The dqt expects to exist within a git repo
# in order to display the version
COPY .git/ /app/.git/

# The nginx+uwsgi image expects uwsgi config file at /app/uwsgi.ini
# prestart.sh script runs before app startup
COPY uwsgi.ini /app/uwsgi.ini
COPY prestart.sh /app/prestart.sh

# Nginx Maximum file upload size - what's the biggest 360 spreadsheet?
# https://github.com/tiangolo/uwsgi-nginx-docker?tab=readme-ov-file#custom-max-upload-size
ENV NGINX_MAX_UPLOAD=1G

# Place the database in a persistent volume.
# Note that Dokku must also be configured to mount
# the dir as persistent storage:
# https://dokku.com/docs/advanced-usage/persistent-storage/
# e.g.
# > dokku storage:ensure-directory --chown root dqt-persist-data
# > dokku storage:mount <dqt-app> /var/lib/dokku/data/storage/dqt-persist-data:/data
# (--chown root because this container runs the app as root)
VOLUME /data
ENV DB_NAME=/data/db.sqlite3
ENV MEDIA_ROOT=/data/media/

# Healthchecks are handled by Dokku, see CHECKS file.
