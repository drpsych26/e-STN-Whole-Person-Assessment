# STN API container. Synthetic data only until every production go-live gate is signed.
#
# Build:  docker build --build-arg STN_BUILD_ID=$(git rev-parse --short HEAD) -t stn-api backend
# Run:    read-only root filesystem with a tmpfs at /tmp; no secrets in the image. Configure
#         everything through environment variables (see backend/README.md).
#
# The base image is pinned by digest. Update it deliberately (and re-run the vulnerability scan).
ARG PYTHON_IMAGE=python:3.12-slim-bookworm@sha256:935c3c5b12357a7e10caa9c1e6ca5692344d97cf229832ef584be2cec9fc03df

FROM ${PYTHON_IMAGE} AS build
ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1
RUN python -m venv /opt/venv
ENV PATH=/opt/venv/bin:$PATH
COPY requirements.lock /tmp/requirements.lock
# Every dependency is hash-pinned; --no-deps means nothing unpinned can be pulled in.
RUN pip install --require-hashes --no-deps -r /tmp/requirements.lock

FROM ${PYTHON_IMAGE} AS runtime
ARG STN_BUILD_ID=unknown
ENV PATH=/opt/venv/bin:$PATH \
    PYTHONPATH=/srv \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    STN_BUILD_ID=${STN_BUILD_ID} \
    PORT=8000
# Apply current Debian security updates on top of the pinned base, then drop the package lists.
RUN apt-get update \
    && apt-get upgrade -y --no-install-recommends \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --system --gid 10001 stn \
    && useradd --system --uid 10001 --gid stn --no-create-home --home-dir /nonexistent --shell /usr/sbin/nologin stn
COPY --from=build /opt/venv /opt/venv
COPY app /srv/app
COPY docker-entrypoint.sh /usr/local/bin/stn-entrypoint
RUN chmod 0755 /usr/local/bin/stn-entrypoint && chmod -R a-w /srv/app
USER 10001:10001
WORKDIR /srv
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s --start-period=30s --retries=3 \
    CMD ["python", "-c", "import os, sys, urllib.request; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:%s/healthz' % os.environ.get('PORT', '8000'), timeout=2).status == 200 else 1)"]
ENTRYPOINT ["/usr/local/bin/stn-entrypoint"]
