# SPDX-License-Identifier: LGPL-2.1-or-later
#
# Copyright (C) 2021 Collabora Limited
# Author: Guillaume Tucker <guillaume.tucker@collabora.com>

from bson import ObjectId
from pymongo import MongoClient
from .models import Node, User
from motor import motor_asyncio


class Database(object):
    COLLECTIONS = {
        User: 'user',
        Node: 'node',
    }

    def __init__(self, host='db', db_name='kernelci'):
        self._motor = motor_asyncio.AsyncIOMotorClient(host=host)
        self._db = self._motor[db_name]

    def _get_collection(self, model):
        col = self.COLLECTIONS[model]
        return self._db[col]

    async def find_all(self, model):
        col = self._get_collection(model)
        objs = []
        data = col.find()
        async for obj in data:
            objs.append(model(**obj))
        return objs

    async def find_one(self, model, **kwargs):
        col = self._get_collection(model)
        obj = await col.find_one(kwargs)
        return model(**obj) if obj else None

    async def find_by_id(self, model, obj_id):
        col = self._get_collection(model)
        obj = await col.find_one({'_id': ObjectId(obj_id)})
        return model(**obj) if obj else None

    async def find_by_attributes(self, model, attributes):
        col = self._get_collection(model)
        data = await col.find(attributes).to_list(None)
        return list(model(**obj) for obj in data)

    async def create(self, obj):
        if obj.id is not None:
            raise ValueError(f"Object cannot be created with id: {obj.id}")
        delattr(obj, 'id')
        col = self._get_collection(obj.__class__)
        res = await col.insert_one(obj.dict(by_alias=True))
        obj.id = res.inserted_id
        return obj

    async def update(self, obj):
        if obj.id is None:
            raise ValueError("Cannot update object with no id")
        col = self._get_collection(obj.__class__)
        res = await col.replace_one(
            {'_id': ObjectId(obj.id)}, obj.dict(by_alias=True)
        )
        if res.matched_count == 0:
            raise ValueError(f"No object found with id: {obj.id}")
        return obj
