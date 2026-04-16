# SPDX-License-Identifier: LGPL-2.1-or-later
#
# Copyright (C) 2023 Collabora Limited
# Author: Jeny Sadadia <jeny.sadadia@collabora.com>


"""pytest fixtures for KernelCI API end-to-end tests"""

import asyncio

import pytest
from httpx import ASGITransport, AsyncClient
from kernelci.api.models import Node, Regression
from pymongo import AsyncMongoClient

from api.main import versioned_app

BASE_URL = "http://api:8000/latest/"
DB_URL = "mongodb://db:27017"
DB_NAME = "kernelci"

db_client = AsyncMongoClient(DB_URL)
db = db_client[DB_NAME]
node_model_fields = set(Node.model_fields.keys())
regression_model_fields = set(Regression.model_fields.keys())
paginated_response_keys = {
    "items",
    "total",
    "limit",
    "offset",
}


@pytest.fixture(scope="session")
async def test_async_client():
    """Fixture to get Test client for asynchronous tests"""
    transport = ASGITransport(app=versioned_app)
    async with AsyncClient(transport=transport, base_url=BASE_URL) as client:
        await versioned_app.router.startup()
        yield client
        await versioned_app.router.shutdown()


async def db_create(collection, obj):
    """Database create method"""
    delattr(obj, "id")
    col = db[collection]
    # res = await col.insert_one(obj.dict(by_alias=True))
    res = await col.insert_one(obj.model_dump(by_alias=True))
    obj.id = res.inserted_id
    return obj


@pytest.fixture(scope="session")
def event_loop():
    """Session-scoped event loop shared by all async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()
