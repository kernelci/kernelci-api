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
import datetime
import os
from pymongo import MongoClient


def purge_ids(db, collection, ids):
    """
    Delete documents from the specified collection in the database
    by their IDs.

    Args:
        db: The MongoDB database instance.
        collection (str): The name of the collection to purge from.
        ids (list): List of document IDs to delete.
    """
    print("Purging", len(ids), "from", collection)
    db[collection].delete_many({
        "_id": {"$in": ids}
    })


def connect_to_db():
    """
    Connect to the MongoDB database using the MONGO_SERVICE environment
    variable.

    Returns:
        db: The 'kernelci' MongoDB database instance.
    Raises:
        ValueError: If the MONGO_SERVICE environment variable is not set.
    """
    mongo_service = os.environ["MONGO_SERVICE"]
    if not mongo_service:
        raise ValueError("MONGO_SERVICE environment variable is not set")
    client = MongoClient(mongo_service)
    db = client["kernelci"]
    return db


async def purge_old_nodes(age_days=180, batch_size=1000):
    """
    Purge nodes from the 'nodes' collection that are older than the
    specified number of days.

    Args:
        age_days (int, optional): The age in days to use as the
        threshold for deletion.
            Defaults to 180.
    """
    date_end = datetime.datetime.today() - datetime.timedelta(days=age_days)
    db = connect_to_db()
    nodes = db["nodes"].find({
        "created": {"$lt": date_end}
    })
    # We need to delete node in chunks of {batch_size}
    # to not block the main thread for too long
    deleted = 0
    del_batch = []
    for node in nodes:
        del_batch.append(node["_id"])
        if len(del_batch) == batch_size:
            deleted += len(del_batch)
            purge_ids(db, "nodes", del_batch)
            del_batch = []
    if del_batch:
        deleted += len(del_batch)
        purge_ids(db, "nodes", del_batch)
    db = {
        'response': 'ok',
        'deleted': deleted,
        'age_days': age_days
    }
    return db
