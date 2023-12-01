# SPDX-License-Identifier: LGPL-2.1-or-later
#
# Copyright (C) 2022 Jeny Sadadia
# Author: Jeny Sadadia <jeny.sadadia@gmail.com>
#
# Copyright (C) 2022, 2023 Collabora Limited
# Author: Jeny Sadadia <jeny.sadadia@collabora.com>

# pylint: disable=protected-access

"""pytest fixtures for KernelCI API"""

from unittest.mock import AsyncMock
import asyncio
import fakeredis.aioredis
from fastapi.testclient import TestClient
from fastapi import Request, HTTPException, status
import pytest
from mongomock_motor import AsyncMongoMockClient
from beanie import init_beanie
from httpx import AsyncClient

from api.main import (
    app,
    versioned_app,
    get_current_user,
    get_current_superuser,
)
from api.models import UserGroup
from api.user_models import User
from api.pubsub import PubSub, Subscription

BEARER_TOKEN = "Bearer \
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJib2IifQ.\
ci1smeJeuX779PptTkuaG1SEdkp5M1S1AgYvX8VdB20"

ADMIN_BEARER_TOKEN = 'Bearer \
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.\
eyJzdWIiOiJib2IiLCJzY29wZXMiOlsiYWRtaW4iXX0.\
t3bAE-pHSzZaSHp7FMlImqgYvL6f_0xDUD-nQwxEm3k'

API_VERSION = 'latest'
BASE_URL = f'http://testserver/{API_VERSION}/'


def mock_get_current_user(request: Request):
    """
    Get current active user
    """
    token = request.headers.get('authorization')
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing token",
        )
    return User(
        id='65265305c74695807499037f',
        username='bob',
        hashed_password='$2b$12$CpJZx5ooxM11bCFXT76/z.o6HWs2sPJy4iP8.'
                        'xCZGmM8jWXUXJZ4L',
        email='bob@kernelci.org',
        is_active=True,
        is_superuser=False,
        is_verified=True
    )


def mock_get_current_admin_user(request: Request):
    """
    Get current active admin user
    """
    token = request.headers.get('authorization')
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing token",
        )
    if token != ADMIN_BEARER_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden",
        )
    return User(
        id='653a5e1a7e9312c86f8f86e1',
        username='admin',
        hashed_password='$2b$12$CpJZx5ooxM11bCFXT76/z.o6HWs2sPJy4iP8.'
                        'xCZGmM8jWXUXJZ4K',
        email='admin@kernelci.org',
        groups=[UserGroup(name='admin')],
        is_active=True,
        is_superuser=True,
        is_verified=True
    )


app.dependency_overrides[get_current_user] = mock_get_current_user
app.dependency_overrides[get_current_superuser] = mock_get_current_admin_user


@pytest.fixture
def test_client():
    """Fixture to get FastAPI Test client instance"""
    # Mock dependency callables for getting current user
    with TestClient(app=versioned_app, base_url=BASE_URL) as client:
        return client


@pytest.fixture
async def test_async_client():
    """Fixture to get Test client for asynchronous tests"""
    async with AsyncClient(app=versioned_app, base_url=BASE_URL) as client:
        await versioned_app.router.startup()
        yield client
        await versioned_app.router.shutdown()


@pytest.fixture
def event_loop():
    """Create an instance of the default event loop for each test case.
    This is a workaround to prevent the default event loop to be closed by
    async pubsub tests. It was causing other tests unable to run.
    The issue has already been reported here:
    https://github.com/pytest-dev/pytest-asyncio/issues/371
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    loop.close()


@pytest.fixture
def mock_db_create(mocker):
    """Mocks async call to Database class method used to create object"""
    async_mock = AsyncMock()
    mocker.patch('api.db.Database.create',
                 side_effect=async_mock)
    return async_mock


@pytest.fixture
def mock_db_count(mocker):
    """Mocks async call to Database class method used to count objects"""
    async_mock = AsyncMock()
    mocker.patch('api.db.Database.count',
                 side_effect=async_mock)
    return async_mock


@pytest.fixture
def mock_db_find_by_attributes(mocker):
    """
    Mocks async call to Database class method
    used to find a list of objects by attributes
    """
    async_mock = AsyncMock()
    mocker.patch('api.db.Database.find_by_attributes',
                 side_effect=async_mock)
    return async_mock


@pytest.fixture
def mock_db_find_by_id(mocker):
    """
    Mocks async call to Database class method
    used to find an object by id
    """
    async_mock = AsyncMock()
    mocker.patch('api.db.Database.find_by_id',
                 side_effect=async_mock)
    return async_mock


@pytest.fixture
def mock_db_find_one(mocker):
    """Mocks async call to database method used to find one object"""
    async_mock = AsyncMock()
    mocker.patch('api.db.Database.find_one',
                 side_effect=async_mock)
    return async_mock


@pytest.fixture(autouse=True)
def mock_init_sub_id(mocker):
    """Mocks async call to PubSub method to initialize subscription id"""
    async_mock = AsyncMock()
    mocker.patch('api.pubsub.PubSub._init_sub_id',
                 side_effect=async_mock)
    return async_mock


@pytest.fixture
def mock_listen(mocker):
    """Mocks async call to listen method of PubSub"""
    async_mock = AsyncMock()
    mocker.patch('api.pubsub.PubSub.listen',
                 side_effect=async_mock)
    return async_mock


@pytest.fixture
def mock_publish_cloudevent(mocker):
    """
    Mocks async call to PubSub class method
    used to publish cloud event
    """
    async_mock = AsyncMock()
    mocker.patch('api.pubsub.PubSub.publish_cloudevent',
                 side_effect=async_mock)
    return async_mock


@pytest.fixture
def mock_pubsub(mocker):
    """Mocks `_redis` member of PubSub class instance"""
    pubsub = PubSub()
    redis_mock = fakeredis.aioredis.FakeRedis()
    mocker.patch.object(pubsub, '_redis', redis_mock)
    return pubsub


@pytest.fixture
def mock_pubsub_subscriptions(mocker):
    """Mocks `_redis` and `_subscriptions` member of PubSub class instance"""
    pubsub = PubSub()
    redis_mock = fakeredis.aioredis.FakeRedis()
    sub = Subscription(id=1, channel='test', user='test')
    mocker.patch.object(pubsub, '_redis', redis_mock)
    subscriptions_mock = dict(
        {1: {'sub': sub, 'redis_sub': pubsub._redis.pubsub()}})
    mocker.patch.object(pubsub, '_subscriptions', subscriptions_mock)
    return pubsub


@pytest.fixture()
def mock_pubsub_publish(mocker):
    """
    Mocks execution of publish_cloudevent
    from PubSub class.
    """
    pubsub = PubSub()
    redis_mock = fakeredis.aioredis.FakeRedis()
    mocker.patch.object(pubsub, '_redis', redis_mock)
    mocker.patch.object(pubsub._redis, 'execute_command')
    return pubsub


@pytest.fixture
def mock_subscribe(mocker):
    """Mocks async call to subscribe method of PubSub"""
    async_mock = AsyncMock()
    mocker.patch('api.pubsub.PubSub.subscribe',
                 side_effect=async_mock)
    return async_mock


@pytest.fixture
def mock_unsubscribe(mocker):
    """Mocks async call to unsubscribe method of PubSub"""
    async_mock = AsyncMock()
    mocker.patch('api.pubsub.PubSub.unsubscribe',
                 side_effect=async_mock)
    return async_mock


@pytest.fixture(autouse=True)
async def mock_init_beanie(mocker):
    """Mocks async call to Database method to initialize Beanie"""
    async_mock = AsyncMock()
    client = AsyncMongoMockClient()
    init = await init_beanie(
        document_models=[User], database=client.get_database(name="db"))
    mocker.patch('api.db.Database.initialize_beanie',
                 side_effect=async_mock, return_value=init)
    return async_mock


@pytest.fixture
def mock_db_update(mocker):
    """
    Mocks async call to Database class method used to update object
    """
    async_mock = AsyncMock()
    mocker.patch('api.db.Database.update',
                 side_effect=async_mock)
    return async_mock


@pytest.fixture
async def mock_beanie_get_user_by_id(mocker):
    """Mocks async call to external method to get model by id"""
    async_mock = AsyncMock()
    mocker.patch('fastapi_users_db_beanie.BeanieUserDatabase.get',
                 side_effect=async_mock)
    return async_mock


@pytest.fixture
def mock_auth_current_user(mocker):
    """
    Mocks async call to external method to get authenticated user
    """
    async_mock = AsyncMock()
    mocker.patch('fastapi_users.authentication.Authenticator._authenticate',
                 side_effect=async_mock)
    return async_mock


@pytest.fixture
def mock_user_find(mocker):
    """
    Mocks async call to external method to find user model using Beanie
    """
    async_mock = AsyncMock()
    mocker.patch('api.user_models.User.find_one',
                 side_effect=async_mock)
    return async_mock
