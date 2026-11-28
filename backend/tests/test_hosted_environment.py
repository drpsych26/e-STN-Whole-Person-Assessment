"""Hosted environments (STN_ENVIRONMENT=staging|production) refuse SQLite and PostgreSQL without TLS."""
from __future__ import annotations

import pytest

from app import db


@pytest.mark.parametrize("env", ["staging", "production", "Production"])
def test_hosted_refuses_sqlite(monkeypatch, tmp_path, env):
    monkeypatch.setenv(db.ENVIRONMENT_ENV, env)
    monkeypatch.delenv(db.URL_ENV, raising=False)
    monkeypatch.setenv(db.DB_ENV, str(tmp_path / "x.sqlite3"))
    with pytest.raises(db.StoreNotConfigured):
        db.dialect()


@pytest.mark.parametrize("url", [
    "postgresql://u@h:5432/d",
    "postgresql://u@h:5432/d?sslmode=prefer",
    "postgresql://u@h:5432/d?sslmode=disable",
])
def test_hosted_refuses_postgres_without_tls(monkeypatch, url):
    monkeypatch.setenv(db.ENVIRONMENT_ENV, "production")
    monkeypatch.setenv(db.URL_ENV, url)
    with pytest.raises(db.StoreNotConfigured):
        db.dialect()


@pytest.mark.parametrize("url", [
    "postgresql://u@h:5432/d?sslmode=require",
    "postgresql://u@h:5432/d?connect_timeout=5&sslmode=verify-full",
])
def test_hosted_accepts_postgres_with_tls(monkeypatch, url):
    monkeypatch.setenv(db.ENVIRONMENT_ENV, "staging")
    monkeypatch.setenv(db.URL_ENV, url)
    assert db.dialect() == "postgres"


def test_local_still_allows_sqlite(monkeypatch, tmp_path):
    monkeypatch.delenv(db.ENVIRONMENT_ENV, raising=False)
    monkeypatch.delenv(db.URL_ENV, raising=False)
    monkeypatch.setenv(db.DB_ENV, str(tmp_path / "x.sqlite3"))
    assert db.dialect() == "sqlite"
