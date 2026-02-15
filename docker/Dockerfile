FROM frappe/bench:latest as builder

# Use local apps.json which excludes arijentek_core (pulled separately or copied)
COPY docker/builder_apps.json /apps.json

# Initialize bench with remote apps
RUN bench init --skip-redis-config-generation --skip-assets --apps_path /apps.json /frappe-bench

WORKDIR /frappe-bench

# Get other apps from remote (already done by init for those in apps.json)
# ...

# COPY local app source
# Note: Context must be set to /workspace/development/frappe-bench/apps/arijentek_core (app root)
COPY . /frappe-bench/apps/arijentek_core

# Install the app
RUN cd /frappe-bench/apps/arijentek_core && \
    pip install -e . && \
    echo "arijentek_core" >> /frappe-bench/sites/apps.txt

# Build assets
RUN bench build

# --- Runtime Stage ---
FROM frappe/erpnext:v16.0.1

COPY --from=builder --chown=frappe:frappe /frappe-bench/apps /home/frappe/frappe-bench/apps
COPY --from=builder --chown=frappe:frappe /frappe-bench/sites/assets /home/frappe/frappe-bench/sites/assets

RUN cd /home/frappe/frappe-bench && \
    bench setup requirements
