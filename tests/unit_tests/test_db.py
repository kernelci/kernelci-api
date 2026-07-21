# SPDX-License-Identifier: LGPL-2.1-or-later
#
# Copyright (C) 2026 Collabora Limited

"""Unit tests for the database abstraction."""

from unittest.mock import AsyncMock, Mock

import pytest
from kernelci.api.models import TelemetryEvent

from api.db import Database


@pytest.mark.asyncio
async def test_create_indexes_awaits_pymongo(mocker):
    """Every PyMongo AsyncCollection.create_index call is awaited."""
    collection = Mock()
    collection.create_index = AsyncMock()
    database = Database.__new__(Database)
    database.COLLECTIONS = {TelemetryEvent: "telemetry"}
    mocker.patch.object(database, "_get_collection", return_value=collection)

    await database.create_indexes()

    assert collection.create_index.await_count == len(
        TelemetryEvent.get_indexes()
    )


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
