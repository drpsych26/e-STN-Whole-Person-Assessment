"""Process for the migration role (STN_PROCESS_ROLE=migrate).

The container entrypoint runs `python -m app.migrate` first and exits if it fails. This app
then serves only /healthz and /readyz, so the deploy workflow can wait until the database is at
this build's schema version. It exposes no API routes and holds no data keys.
"""
from fastapi import FastAPI

from . import health

app = FastAPI(title="STN migration runner", version="0.5.0", docs_url=None, redoc_url=None, openapi_url=None)
app.include_router(health.make_router(health.migration_readiness))
