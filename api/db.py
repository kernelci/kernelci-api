# SPDX-License-Identifier: LGPL-2.1-or-later
#
# Copyright (C) 2021 Collabora Limited
# Author: Guillaume Tucker <guillaume.tucker@collabora.com>

from bson import ObjectId
from .models import Thing, User
from motor import motor_asyncio


class Database(object):
    COLLECTIONS = {
        Thing: 'thing',
        User: 'user',
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

    async def create(self, obj):
        col = self._get_collection(obj.__class__)
        if hasattr(obj, 'id'):
            delattr(obj, 'id')
        res = await col.insert_one(obj.dict(by_alias=True))
        obj.id = res.inserted_id
        return obj
