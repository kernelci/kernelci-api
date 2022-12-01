# SPDX-License-Identifier: LGPL-2.1-or-later
#
# Copyright (C) 2021, 2022 Collabora Limited
# Author: Guillaume Tucker <guillaume.tucker@collabora.com>
# Author: Jeny Sadadia <jeny.sadadia@collabora.com>

"""Database abstraction"""

from bson import ObjectId
from fastapi_pagination.ext.motor import paginate
from motor import motor_asyncio
from .models import Hierarchy, Node, User, Regression


class Database:
    """Database abstraction class

    This class provides an abstraction layer to access the Mongo DB database
    asynchronously using the models defined in `.models`.  *host* is the
    hostname where the database is, and *db_name* is the name of the database.
    """

    COLLECTIONS = {
        User: 'user',
        Node: 'node',
        Regression: 'regression',
    }

    OPERATOR_MAP = {
        'lt': '$lt',
        'lte': '$lte',
        'gt': '$gt',
        'gte': '$gte',
    }

    def __init__(self, host='db', db_name='kernelci'):
        self._motor = motor_asyncio.AsyncIOMotorClient(host=host)
        self._db = self._motor[db_name]

    def _get_collection(self, model):
        col = self.COLLECTIONS[model]
        return self._db[col]

    async def create_indexes(self):
        """Create indexes for models"""
        for model in self.COLLECTIONS:
            col = self._get_collection(model)
            model.create_indexes(col)

    async def find_all(self, model):
        """Find all objects of a given model"""
        col = self._get_collection(model)
        objs = []
        data = col.find()
        async for obj in data:
            objs.append(model(**obj))
        return objs

    async def find_one(self, model, **kwargs):
        """Find one object with matching attributes

        The kwargs dictionary provides key/value pairs used to find an object
        with matching attributes.
        """
        col = self._get_collection(model)
        obj = await col.find_one(kwargs)
        return model(**obj) if obj else None

    async def find_by_id(self, model, obj_id):
        """Find one object with a given id"""
        col = self._get_collection(model)
        obj = await col.find_one({'_id': ObjectId(obj_id)})
        return model(**obj) if obj else None

    def _operator_translation(self, attributes):
        translated = attributes.copy()
        for key, value in attributes.items():
            if isinstance(value, dict):
                for sub_key, sub_value in value.items():
                    if not self.OPERATOR_MAP.get(sub_key):
                        raise ValueError(
                            f"No operator found matching '{sub_key}'"
                        )
                    translated[key] = {
                        self.OPERATOR_MAP.get(sub_key): sub_value
                    }
        return translated

    async def find_by_attributes(self, model, attributes):
        """Find objects with matching attributes

        Find all objects with attributes matching the key/value pairs in the
        attributes dictionary using pagination and return the paginated
        response.
        The response dictionary will include 'items', 'total', 'limit',
        and 'offset' keys.
        """
        col = self._get_collection(model)
        translated = self._operator_translation(attributes)
        return await paginate(collection=col, query_filter=translated)

    async def count(self, model, attributes):
        """Count objects with matching attributes

        Count all objects with attributes matching the key/value pairs in the
        attributes dictionary and return the count as an integer.
        """
        col = self._get_collection(model)
        translated = self._operator_translation(attributes)
        return await col.count_documents(translated)

    async def create(self, obj):
        """Create a database document from a model object

        For a given object instance from .models, create a document in the
        database.  Add the new id to the object and return it.  Raise
        ValueError if the object already has an id as this should be created by
        the database.
        """
        if obj.id is not None:
            raise ValueError(f"Object cannot be created with id: {obj.id}")
        delattr(obj, 'id')
        obj.set_timeout()
        col = self._get_collection(obj.__class__)
        res = await col.insert_one(obj.dict(by_alias=True))
        obj.id = res.inserted_id
        return obj

    async def _create_recursively(self, hierarchy: Hierarchy, parent: Node,
                                  cls, col):
        obj, nodes = hierarchy.node, hierarchy.child_nodes
        if parent:
            obj.parent = parent.id
        if obj.id:
            obj.update()
            res = await col.replace_one(
                {'_id': ObjectId(obj.id)}, obj.dict(by_alias=True)
            )
            if res.matched_count == 0:
                raise ValueError(f"No object found with id: {obj.id}")
        else:
            delattr(obj, 'id')
            obj.set_timeout()
            res = await col.insert_one(obj.dict(by_alias=True))
            obj.id = res.inserted_id
        obj = cls(**await col.find_one({'_id': ObjectId(obj.id)}))
        obj_list = [obj]
        for node in nodes:
            child_nodes = await self._create_recursively(node, obj, cls, col)
            obj_list.extend(child_nodes)
        return obj_list

    async def create_hierarchy(self, hierarchy: Hierarchy, cls):
        """Create a hierarchy of objects"""
        col = self._get_collection(cls)
        return await self._create_recursively(hierarchy, None, cls, col)

    async def update(self, obj):
        """Update an existing document from a model object

        For a given object instance from .models, update the document in the
        database with a matching id.  The object is then returned.  Raise a
        ValueError if the object has no id or if no document matches the id in
        the database.
        """
        if obj.id is None:
            raise ValueError("Cannot update object with no id")
        col = self._get_collection(obj.__class__)
        obj.update()
        res = await col.replace_one(
            {'_id': ObjectId(obj.id)}, obj.dict(by_alias=True)
        )
        if res.matched_count == 0:
            raise ValueError(f"No object found with id: {obj.id}")
        return obj.__class__(**await col.find_one({'_id': ObjectId(obj.id)}))
