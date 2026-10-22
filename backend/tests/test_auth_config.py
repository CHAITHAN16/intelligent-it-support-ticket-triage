import os
import secrets

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

import pytest

from auth import load_jwt_secret


@pytest.mark.parametrize("configured_secret", [None, "", "   "])
def test_missing_jwt_secret_is_rejected(configured_secret):
    with pytest.raises(RuntimeError, match="JWT_SECRET_KEY must be configured"):
        load_jwt_secret(configured_secret, "production")


@pytest.mark.parametrize("environment", ["test", "production"])
def test_placeholder_jwt_secret_is_rejected_outside_development(environment):
    with pytest.raises(RuntimeError, match="not a placeholder"):
        load_jwt_secret("replace-with-a-local-development-secret", environment)


@pytest.mark.parametrize("environment", ["development", "test", "production"])
def test_valid_configured_jwt_secret_is_preserved(environment):
    configured_secret = secrets.token_urlsafe(48)

    assert load_jwt_secret(configured_secret, environment) == configured_secret


def test_short_jwt_secret_is_rejected():
    with pytest.raises(RuntimeError, match="at least 32 bytes"):
        load_jwt_secret("short", "development")


def test_unknown_app_environment_is_rejected():
    with pytest.raises(RuntimeError, match="APP_ENV must be"):
        load_jwt_secret(secrets.token_urlsafe(48), "staging")
