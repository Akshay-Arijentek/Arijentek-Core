FROM frappe/erpnext:v16.0.1

ARG FRAPPE_BRANCH=version-16
ARG ERPNEXT_BRANCH=version-16

COPY builder_apps.json /opt/frappe/builder_apps.json

RUN install_app arijentek_core https://github.com/akshayarijentek/arijentek-core Arijentek-Core

# Install other apps if not present in base image (erpnext image has frappe+erpnext)
# We need to install: hrms, crm, helpdesk, insights, gameplan, telephony
# The standard frappe docker way for custom apps is often to build a new image from scratch using bench
# or use the 'custom' builder pattern.
#
# Simplified approach for 'install_app' is supported in some versions, but let's use the standard builder pattern
# to ensure all dependencies are met.

# --- Builder Stage ---
FROM frappe/bench:latest as builder

ARG FRAPPE_BRANCH=version-16
COPY builder_apps.json /apps.json

RUN bench init --skip-redis-config-generation --skip-assets --apps_path /apps.json /frappe-bench

WORKDIR /frappe-bench

# Install Node dependencies
RUN bench build

# --- Runtime Stage ---
FROM frappe/erpnext:v16.0.1

COPY --from=builder --chown=frappe:frappe /frappe-bench/apps /home/frappe/frappe-bench/apps
COPY --from=builder --chown=frappe:frappe /frappe-bench/sites/assets /home/frappe/frappe-bench/sites/assets

# Re-install python dependencies for all apps
RUN cd /home/frappe/frappe-bench && \
    bench setup requirements && \
    bench build
