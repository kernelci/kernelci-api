# SPDX-License-Identifier: LGPL-2.1-or-later
#
# Copyright (C) 2022 Jeny Sadadia
# Author: Jeny Sadadia <jeny.sadadia@gmail.com>
#
# Copyright (C) 2022 Collabora Limited
# Author: Jeny Sadadia <jeny.sadadia@collabora.com>

# pylint: disable=protected-access

"""pytest fixtures for KernelCI API"""

from unittest.mock import AsyncMock
import asyncio
import fakeredis.aioredis
from fastapi.testclient import TestClient
import pytest

from api.main import app
from api.models import User
from api.pubsub import PubSub

BEARER_TOKEN = "Bearer \
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJib2IifQ.\
ci1smeJeuX779PptTkuaG1SEdkp5M1S1AgYvX8VdB20"

ADMIN_BEARER_TOKEN = 'Bearer \
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.\
eyJzdWIiOiJib2IiLCJzY29wZXMiOlsiYWRtaW4iXX0.\
t3bAE-pHSzZaSHp7FMlImqgYvL6f_0xDUD-nQwxEm3k'

API_VERSION = '/latest'



# added a blank line
@pytest.fixture
def client():
    """Returns test client instance"""
    return TestClient(app)


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


@pytest.fixture
def mock_get_current_user(mocker):
    """
    Mocks async call to Authentication class method
    used to get current user
    """
    async_mock = AsyncMock()
    user = User(username='bob',
                hashed_password='$2b$12$CpJZx5ooxM11bCFXT76/z.o6HWs2sPJy4iP8.'
                                'xCZGmM8jWXUXJZ4K',
                active=True, is_admin=False)
    mocker.patch('api.auth.Authentication.get_current_user',
                 side_effect=async_mock)
    async_mock.return_value = user, None
    return async_mock


@pytest.fixture
def mock_get_current_admin_user(mocker):
    """
    Mocks async call to Authentication class method
    used to get current user
    """
    async_mock = AsyncMock()
    user = User(username='admin',
                hashed_password='$2b$12$CpJZx5ooxM11bCFXT76/z.o6HWs2sPJy4iP8.'
                                'xCZGmM8jWXUXJZ4K',
                active=True, is_admin=True)
    mocker.patch('api.auth.Authentication.get_current_user',
                 side_effect=async_mock)
    async_mock.return_value = user, None
    return async_mock


@pytest.fixture
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
    mocker.patch.object(pubsub, '_redis', redis_mock)
    subscriptions_mock = dict({1: pubsub._redis.pubsub()})
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
