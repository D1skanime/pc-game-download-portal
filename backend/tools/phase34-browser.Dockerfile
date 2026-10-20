ARG BASE_IMAGE=phase34-explicit-base:required
# checkov:skip=CKV_DOCKER_7:The runner pins a generated local alias to an inspected immutable image ID.
FROM ${BASE_IMAGE}

WORKDIR /app/frontend
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright
RUN npx --no-install playwright install --with-deps chromium \
    && useradd --create-home --uid 1000 phase34 \
    && mkdir -p /phase34/owned \
    && chown -R phase34:phase34 /phase34 /app/frontend/node_modules \
    && chmod a+rx /root /root/.nvm /root/.nvm/versions /root/.nvm/versions/node \
    && chmod -R a+rX /ms-playwright
ENV HOME=/home/phase34
USER phase34
HEALTHCHECK --interval=30s --timeout=5s CMD kill -0 1 || exit 1
