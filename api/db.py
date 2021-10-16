# SPDX-License-Identifier: LGPL-2.1-or-later
#
# Copyright (C) 2021 Collabora Limited
# Author: Guillaume Tucker <guillaume.tucker@collabora.com>

from bson import ObjectId
from pymongo import MongoClient
from .models import Thing, User
from motor import motor_asyncio

# ToDo: use motor
# https://motor.readthedocs.io/en/stable/


class Database(object):
    COLLECTIONS = {
        Thing: 'thing',
        User: 'user',
    }

    def __init__(self, host='db', db_name='kernelci'):
        self._mongo = MongoClient(host=host)
        self._motor = motor_asyncio.AsyncIOMotorClient(host=host)
        self._db = self._motor[db_name]

    def _get_collection(self, model):
        col = self.COLLECTIONS[model]
        return self._db[col]

    def find_all(self, model):
        col = self._get_collection(model)
        objs = []
        for obj in col.find():
            objs.append(model(**obj))
        return objs

    def find_one(self, model, **kwargs):
        col = self._get_collection(model)
        obj = col.find_one(kwargs)
        return model(**obj) if obj else None

    def find_by_id(self, model, obj_id):
        col = self._get_collection(model)
        obj = col.find_one({'_id': ObjectId(obj_id)})
        return model(**obj) if obj else None

    def create(self, obj):
        col = self._get_collection(obj.__class__)
        if hasattr(obj, 'id'):
            delattr(obj, 'id')
        res = col.insert_one(obj.dict(by_alias=True))
        obj.id = res.inserted_id
        return obj
