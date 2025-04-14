from pymongo import MongoClient
import datetime
import os


def purge_ids(db, collection, ids):
    print("Purging", len(ids), "from", collection)
    db[collection].delete_many({"_id": {"$in": ids}})


def connect_to_db():
    mongo_service = os.environ["MONGO_SERVICE"]
    if not mongo_service:
        raise ValueError("MONGO_SERVICE environment variable is not set")
    client = MongoClient(mongo_service)
    db = client["kernelci"]
    return db


async def purge_old_nodes(age_days=180):
    date_end = datetime.datetime.today() - datetime.timedelta(days=age_days)
    db = connect_to_db()
    nodes = db["nodes"].find({"created": {"$lt": date_end}})
    # We need to delete node in chunks of 1000,
    # to not block the main thread for too long
    del_batch = []
    for node in nodes:
        del_batch.append(node["_id"])
        if len(del_batch) == 1000:
            purge_ids(db, "nodes", del_batch)
            del_batch = []
    if del_batch:
        purge_ids(db, "nodes", del_batch)
