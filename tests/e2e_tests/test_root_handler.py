# SPDX-License-Identifier: LGPL-2.1-or-later
#
# Copyright (C) 2023 Collabora Limited
# Author: Jeny Sadadia <jeny.sadadia@collabora.com>

"""End-to-end test functions for KernelCI API root handler"""

import pytest


@pytest.mark.asyncio
async def test_root_endpoint(test_async_client):
    """Test root handler"""
    response = await test_async_client.get("/")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert "KernelCI API Server" in response.text


@pytest.mark.asyncio
async def test_health_endpoint(test_async_client):
    """Test health handler"""
    response = await test_async_client.get("health")
    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "KernelCI API",
    }
