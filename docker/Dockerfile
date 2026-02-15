FROM frappe/bench:latest as builder

# Use local apps.json which excludes arijentek_core (pulled separately or copied)
COPY docker/builder_apps.json /apps.json

# Initialize bench with remote apps
RUN bench init --skip-redis-config-generation --skip-assets --frappe-branch version-16 --apps_path /apps.json /home/frappe/frappe-bench

WORKDIR /home/frappe/frappe-bench

WORKDIR /home/frappe/frappe-bench/apps/arijentek_core/frontend
RUN npm install && npm run build-only

WORKDIR /home/frappe/frappe-bench

# Build assets
RUN bench build

# --- Runtime Stage ---
FROM frappe/erpnext:v16.0.1

USER root
RUN apt-get update && apt-get install -y pkg-config gcc g++ make libmariadb-dev && rm -rf /var/lib/apt/lists/*
USER frappe

COPY --from=builder --chown=frappe:frappe /home/frappe/frappe-bench/apps /home/frappe/frappe-bench/apps
COPY --from=builder --chown=frappe:frappe /home/frappe/frappe-bench/sites/assets /home/frappe/frappe-bench/sites/assets

RUN cd /home/frappe/frappe-bench && \
    bench setup requirements
