# SPDX-License-Identifier: LGPL-2.1-or-later
#
# Copyright (C) 2026 Collabora Limited

"""Unit tests for the database abstraction."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from kernelci.api.models import TelemetryEvent
from pymongo.errors import OperationFailure

from api.db import Database

EVENT_INDEX = SimpleNamespace(
    field="timestamp", attributes={"expireAfterSeconds": 604800}
)


class EventModel:
    @classmethod
    def get_indexes(cls):
        return [EVENT_INDEX]


def _database_with_collection(mocker, collection):
    database = Database.__new__(Database)
    database.COLLECTIONS = {EventModel: "eventhistory"}
    mocker.patch.object(database, "_get_collection", return_value=collection)
    return database


@pytest.mark.asyncio
async def test_create_indexes_awaits_pymongo(mocker):
    """Every PyMongo AsyncCollection.create_index call is awaited."""
    collection = Mock()
    collection.index_information = AsyncMock(return_value={})
    collection.create_index = AsyncMock()
    database = Database.__new__(Database)
    database.COLLECTIONS = {TelemetryEvent: "telemetry"}
    mocker.patch.object(database, "_get_collection", return_value=collection)

    await database.create_indexes()

    assert collection.create_index.await_count == len(
        TelemetryEvent.get_indexes()
    )


@pytest.mark.asyncio
async def test_create_indexes_reuses_equivalent_named_index(mocker):
    collection = Mock()
    collection.index_information = AsyncMock(
        return_value={
            "ttl_timestamp": {
                "v": 2,
                "key": [("timestamp", 1)],
                "expireAfterSeconds": 604800,
            }
        }
    )
    collection.create_index = AsyncMock()
    database = _database_with_collection(mocker, collection)

    await database.create_indexes()

    collection.create_index.assert_not_awaited()


@pytest.mark.asyncio
async def test_create_indexes_rejects_conflicting_options(mocker):
    collection = Mock()
    collection.index_information = AsyncMock(
        return_value={
            "ttl_timestamp": {
                "v": 2,
                "key": [("timestamp", 1)],
                "expireAfterSeconds": 86400,
            }
        }
    )
    conflict = OperationFailure("index options conflict", code=85)
    collection.create_index = AsyncMock(side_effect=conflict)
    database = _database_with_collection(mocker, collection)

    with pytest.raises(OperationFailure) as exc_info:
        await database.create_indexes()

    assert exc_info.value is conflict


@pytest.mark.asyncio
async def test_create_indexes_accepts_concurrent_equivalent_index(mocker):
    collection = Mock()
    collection.index_information = AsyncMock(
        side_effect=[
            {},
            {
                "ttl_timestamp": {
                    "v": 2,
                    "key": [("timestamp", 1)],
                    "expireAfterSeconds": 604800,
                }
            },
        ]
    )
    collection.create_index = AsyncMock(
        side_effect=OperationFailure("index options conflict", code=85)
    )
    database = _database_with_collection(mocker, collection)

    await database.create_indexes()

    collection.create_index.assert_awaited_once_with(
        "timestamp", expireAfterSeconds=604800
    )
    assert collection.index_information.await_count == 2


@pytest.mark.asyncio
async def test_aggregate_awaits_pymongo_cursor(mocker):
    """PyMongo AsyncCollection.aggregate is a coroutine."""
    expected = [{"_id": {"runtime": "lava-test"}, "total": 3}]
    cursor = Mock()
    cursor.to_list = AsyncMock(return_value=expected)
    collection = Mock()
    collection.aggregate = AsyncMock(return_value=cursor)
    database = Database.__new__(Database)
    mocker.patch.object(database, "_get_collection", return_value=collection)
    pipeline = [{"$group": {"_id": "$runtime", "total": {"$sum": 1}}}]

    result = await database.aggregate(TelemetryEvent, pipeline)

    assert result == expected
    collection.aggregate.assert_awaited_once_with(pipeline)
    cursor.to_list.assert_awaited_once_with(length=None)
