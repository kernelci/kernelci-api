# SPDX-License-Identifier: LGPL-2.1-or-later
#
# Copyright (C) 2023 Collabora Limited
# Author: Jeny Sadadia <jeny.sadadia@collabora.com>


"""pytest fixtures for KernelCI API end-to-end tests"""

import pytest
from httpx import AsyncClient
from motor.motor_asyncio import AsyncIOMotorClient

from fastapi.testclient import TestClient

from api.main import versioned_app
from kernelci.api.models import Node, Regression

BASE_URL = 'http://api:8000/latest/'
DB_URL = 'mongodb://db:27017'
DB_NAME = 'kernelci'

db_client = AsyncIOMotorClient(DB_URL)
db = db_client[DB_NAME]
node_model_fields = set(Node.__fields__.keys())
regression_model_fields = set(Regression.__fields__.keys())
paginated_response_keys = {
    'items',
    'total',
    'limit',
    'offset',
}

@pytest.fixture(scope='session')
def test_client():
    """Fixture to get FastAPI Test client instance"""
    with TestClient(app=versioned_app, base_url=BASE_URL) as client:
        yield client


@pytest.fixture(scope='session')
async def test_async_client():
    """Fixture to get Test client for asynchronous tests"""
    async with AsyncClient(app=versioned_app, base_url=BASE_URL) as client:
        await versioned_app.router.startup()
        yield client
        await versioned_app.router.shutdown()


async def db_create(collection, obj):
    """Database create method"""
    delattr(obj, 'id')
    col = db[collection]
    res = await col.insert_one(obj.dict(by_alias=True))
    obj.id = res.inserted_id
    return obj


@pytest.fixture(scope='session')
def event_loop():
    """Get an instance of the default event loop using database client.
    The event loop will be used for all async tests.
    """
    loop = db_client.get_io_loop()
    yield loop
    loop.close()
