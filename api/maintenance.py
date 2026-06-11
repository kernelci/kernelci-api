# SPDX-License-Identifier: LGPL-2.1-or-later
#
# Copyright (C) 2021-2025 Collabora Limited
# Author: Guillaume Tucker <guillaume.tucker@collabora.com>
# Author: Jeny Sadadia <jeny.sadadia@collabora.com>
# Author: Denys Fedoryshchenko <denys.f@collabora.com>

"""
This module provides maintenance utilities for the KernelCI API, including
functions to purge old nodes from the database and manage MongoDB connections.
"""

import asyncio
import datetime
import os
import time

from pymongo import AsyncMongoClient

DEFAULT_MONGO_SERVICE = "mongodb://db:27017"
# Node kinds that must never be purged, whatever their age
PURGE_EXCLUDED_KINDS = ["checkout"]
# How often to report purge progress, in seconds
PURGE_PROGRESS_INTERVAL = 30
# Pause between deletion batches to let other queries run
PURGE_BATCH_PAUSE = 1


async def purge_old_nodes(age_days=180, batch_size=10000):
    """
    Purge nodes from the 'node' collection that are older than the
    specified number of days, except the kinds listed in
    PURGE_EXCLUDED_KINDS.

    Args:
        age_days (int, optional): The age in days to use as the
            threshold for deletion.  Defaults to 180.
        batch_size (int, optional): Number of nodes to delete in one
            batch.  Defaults to 10000.
    """
    date_end = datetime.datetime.today() - datetime.timedelta(days=age_days)
    mongo_service = os.getenv("MONGO_SERVICE", DEFAULT_MONGO_SERVICE)
    client = AsyncMongoClient(mongo_service)
    collection = client["kernelci"]["node"]
    node_filter = {
        "created": {"$lt": date_end},
        "kind": {"$nin": PURGE_EXCLUDED_KINDS},
    }
    total = await collection.count_documents(node_filter)
    print(
        f"Node purge started: {total} nodes older than {age_days} days "
        f"(created before {date_end.isoformat()})"
    )
    started = time.monotonic()
    last_report = started
    deleted = 0
    # Paginate on _id (indexed) as there is no index on 'created'
    query = dict(node_filter)
    while True:
        batch = (
            await collection.find(query, {"_id": 1})
            .sort("_id", 1)
            .limit(batch_size)
            .to_list(batch_size)
        )
        if not batch:
            break
        ids = [doc["_id"] for doc in batch]
        result = await collection.delete_many({"_id": {"$in": ids}})
        deleted += result.deleted_count
        query["_id"] = {"$gt": ids[-1]}
        now = time.monotonic()
        if now - last_report >= PURGE_PROGRESS_INTERVAL:
            print(f"Node purge progress: {deleted}/{total} nodes deleted")
            last_report = now
        await asyncio.sleep(PURGE_BATCH_PAUSE)
    elapsed = round(time.monotonic() - started)
    print(f"Node purge finished: {deleted} nodes deleted in {elapsed}s")
    await client.close()
    return {"response": "ok", "deleted": deleted, "age_days": age_days}
