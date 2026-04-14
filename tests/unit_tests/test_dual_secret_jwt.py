# SPDX-License-Identifier: LGPL-2.1-or-later
#
# Copyright (C) 2025 Collabora Limited
# Author: Denys Fedoryshchenko <denys.f@collabora.com>

"""Unit tests for DualSecretJWTStrategy"""

import time
from unittest.mock import AsyncMock, MagicMock

import jwt as pyjwt
import pytest
from fastapi_users.jwt import generate_jwt

from api.auth import DualSecretJWTStrategy

PRIMARY_SECRET = "primary-secret-key"
UNIFIED_SECRET = "unified-secret-key"
WRONG_SECRET = "wrong-secret-key"
USER_ID = "65265305c74695807499037f"
AUDIENCE = ["fastapi-users:auth"]


def _make_user_manager(user=None):
    """Create a mock user manager that returns the given user."""
    manager = AsyncMock()
    manager.parse_id = MagicMock(return_value=USER_ID)
    manager.get = AsyncMock(return_value=user)
    return manager


def _make_user():
    """Create a minimal mock user."""
    user = MagicMock()
    user.id = USER_ID
    return user


def _generate_token(secret, user_id=USER_ID):
    """Generate a JWT token with the given secret."""
    data = {
        "sub": user_id,
        "aud": AUDIENCE,
        "email": "test@kernelci.org",
        "origin": "kernelci-pipeline",
    }
    return generate_jwt(data, secret, lifetime_seconds=3600)


@pytest.mark.asyncio
async def test_read_token_primary_secret():
    """Token signed with primary secret should authenticate."""
    strategy = DualSecretJWTStrategy(
        secret=PRIMARY_SECRET,
        lifetime_seconds=3600,
        unified_secret=UNIFIED_SECRET,
    )
    user = _make_user()
    manager = _make_user_manager(user)
    token = _generate_token(PRIMARY_SECRET)

    result = await strategy.read_token(token, manager)
    assert result is user


@pytest.mark.asyncio
async def test_read_token_unified_secret():
    """Token signed with unified secret should authenticate via fallback."""
    strategy = DualSecretJWTStrategy(
        secret=PRIMARY_SECRET,
        lifetime_seconds=3600,
        unified_secret=UNIFIED_SECRET,
    )
    user = _make_user()
    manager = _make_user_manager(user)
    token = _generate_token(UNIFIED_SECRET)

    result = await strategy.read_token(token, manager)
    assert result is user


@pytest.mark.asyncio
async def test_read_token_wrong_secret():
    """Token signed with unknown secret should fail."""
    strategy = DualSecretJWTStrategy(
        secret=PRIMARY_SECRET,
        lifetime_seconds=3600,
        unified_secret=UNIFIED_SECRET,
    )
    manager = _make_user_manager(_make_user())
    token = _generate_token(WRONG_SECRET)

    result = await strategy.read_token(token, manager)
    assert result is None


@pytest.mark.asyncio
async def test_read_token_no_unified_secret():
    """Without unified secret, only primary secret works."""
    strategy = DualSecretJWTStrategy(
        secret=PRIMARY_SECRET,
        lifetime_seconds=3600,
        unified_secret="",
    )
    user = _make_user()
    manager = _make_user_manager(user)

    # Primary should work
    token_ok = _generate_token(PRIMARY_SECRET)
    result = await strategy.read_token(token_ok, manager)
    assert result is user

    # Unified-signed token should fail
    token_fail = _generate_token(UNIFIED_SECRET)
    result = await strategy.read_token(token_fail, manager)
    assert result is None


@pytest.mark.asyncio
async def test_read_token_none():
    """None token should return None."""
    strategy = DualSecretJWTStrategy(
        secret=PRIMARY_SECRET,
        lifetime_seconds=3600,
        unified_secret=UNIFIED_SECRET,
    )
    manager = _make_user_manager()

    result = await strategy.read_token(None, manager)
    assert result is None


@pytest.mark.asyncio
async def test_read_token_user_not_found():
    """Valid token but user not in DB should return None."""
    strategy = DualSecretJWTStrategy(
        secret=PRIMARY_SECRET,
        lifetime_seconds=3600,
        unified_secret=UNIFIED_SECRET,
    )
    manager = _make_user_manager(user=None)
    token = _generate_token(PRIMARY_SECRET)

    result = await strategy.read_token(token, manager)
    assert result is None


@pytest.mark.asyncio
async def test_unified_token_primary_secret():
    """Unified token (all fields) signed with primary secret should work."""
    strategy = DualSecretJWTStrategy(
        secret=PRIMARY_SECRET,
        lifetime_seconds=3600,
        unified_secret=UNIFIED_SECRET,
    )
    user = _make_user()
    manager = _make_user_manager(user)
    data = {
        "sub": USER_ID,
        "email": "test@kernelci.org",
        "origin": "kernelci-pipeline",
        "permissions": ["checkout", "testretry", "patchset"],
        "aud": AUDIENCE,
    }
    token = generate_jwt(data, PRIMARY_SECRET, lifetime_seconds=3600)

    result = await strategy.read_token(token, manager)
    assert result is user


@pytest.mark.asyncio
async def test_unified_token_unified_secret():
    """Unified token (all fields) signed with unified secret should work."""
    strategy = DualSecretJWTStrategy(
        secret=PRIMARY_SECRET,
        lifetime_seconds=3600,
        unified_secret=UNIFIED_SECRET,
    )
    user = _make_user()
    manager = _make_user_manager(user)
    data = {
        "sub": USER_ID,
        "email": "test@kernelci.org",
        "origin": "kernelci-pipeline",
        "permissions": ["checkout", "testretry", "patchset"],
        "aud": AUDIENCE,
    }
    token = generate_jwt(data, UNIFIED_SECRET, lifetime_seconds=3600)

    result = await strategy.read_token(token, manager)
    assert result is user


@pytest.mark.asyncio
async def test_unified_token_expired():
    """Expired unified token should be rejected."""
    strategy = DualSecretJWTStrategy(
        secret=PRIMARY_SECRET,
        lifetime_seconds=3600,
        unified_secret=UNIFIED_SECRET,
    )
    manager = _make_user_manager(_make_user())
    data = {
        "sub": USER_ID,
        "email": "test@kernelci.org",
        "origin": "kernelci-pipeline",
        "permissions": ["checkout", "testretry", "patchset"],
        "aud": AUDIENCE,
        "exp": int(time.time()) - 3600,  # expired 1 hour ago
    }
    token = pyjwt.encode(data, UNIFIED_SECRET, algorithm="HS256")

    result = await strategy.read_token(token, manager)
    assert result is None


@pytest.mark.asyncio
async def test_unified_token_wrong_audience():
    """Unified token with wrong audience should be rejected."""
    strategy = DualSecretJWTStrategy(
        secret=PRIMARY_SECRET,
        lifetime_seconds=3600,
        unified_secret=UNIFIED_SECRET,
    )
    manager = _make_user_manager(_make_user())
    data = {
        "sub": USER_ID,
        "email": "test@kernelci.org",
        "origin": "kernelci-pipeline",
        "permissions": ["checkout", "testretry", "patchset"],
        "aud": ["wrong-audience"],
    }
    token = generate_jwt(data, UNIFIED_SECRET, lifetime_seconds=3600)

    result = await strategy.read_token(token, manager)
    assert result is None


@pytest.mark.asyncio
async def test_unified_token_missing_sub():
    """Unified token without sub claim should be rejected."""
    strategy = DualSecretJWTStrategy(
        secret=PRIMARY_SECRET,
        lifetime_seconds=3600,
        unified_secret=UNIFIED_SECRET,
    )
    manager = _make_user_manager(_make_user())
    data = {
        "email": "test@kernelci.org",
        "origin": "kernelci-pipeline",
        "permissions": ["checkout", "testretry", "patchset"],
        "aud": AUDIENCE,
    }
    token = generate_jwt(data, UNIFIED_SECRET, lifetime_seconds=3600)

    result = await strategy.read_token(token, manager)
    assert result is None


@pytest.mark.asyncio
async def test_write_token_uses_primary_secret():
    """write_token should always use the primary secret."""
    strategy = DualSecretJWTStrategy(
        secret=PRIMARY_SECRET,
        lifetime_seconds=3600,
        unified_secret=UNIFIED_SECRET,
    )
    user = _make_user()
    token = await strategy.write_token(user)

    # Should be verifiable with primary secret
    manager = _make_user_manager(user)
    result = await strategy.read_token(token, manager)
    assert result is user

    # Verify it was NOT signed with unified secret by creating
    # a strategy that only knows the unified secret
    strategy_unified_only = DualSecretJWTStrategy(
        secret=UNIFIED_SECRET,
        lifetime_seconds=3600,
        unified_secret="",
    )
    result = await strategy_unified_only.read_token(token, manager)
    assert result is None
