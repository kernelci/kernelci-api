# SPDX-License-Identifier: LGPL-2.1-or-later
#
# Copyright (C) 2021-2023 Collabora Limited
# Author: Guillaume Tucker <guillaume.tucker@collabora.com>
# Author: Jeny Sadadia <jeny.sadadia@collabora.com>

"""Database abstraction"""

from bson import ObjectId
from beanie import init_beanie
from fastapi_pagination.ext.motor import paginate
from motor import motor_asyncio
from kernelci.api.models import Hierarchy, Node, parse_node_obj
from .models import User, UserGroup


class Database:
    """Database abstraction class

    This class provides an abstraction layer to access the Mongo DB database
    asynchronously using the models defined in `.models`.  *host* is the
    hostname where the database is, and *db_name* is the name of the database.
    """

    COLLECTIONS = {
        User: 'user',
        Node: 'node',
        UserGroup: 'usergroup',
    }

    OPERATOR_MAP = {
        'lt': '$lt',
        'lte': '$lte',
        'gt': '$gt',
        'gte': '$gte',
        'ne': '$ne',
        're': '$regex',
    }

    BOOL_VALUE_MAP = {
        'true': True,
        'false': False
    }

    def __init__(self, service='mongodb://db:27017', db_name='kernelci'):
        self._motor = motor_asyncio.AsyncIOMotorClient(service)
        self._db = self._motor[db_name]

    async def initialize_beanie(self):
        """Initialize Beanie ODM to use `fastapi-users` tools for MongoDB"""
        await init_beanie(
            database=self._db,
            document_models=[
                User,
            ],
        )

    def _get_collection(self, model):
        col = self.COLLECTIONS[model]
        return self._db[col]

    async def create_indexes(self):
        """Create indexes for models"""
        for model in self.COLLECTIONS:
            indexes = model.get_indexes()
            if not indexes:
                continue
            col = self._get_collection(model)
            for index in indexes:
                col.create_index(index.field, **index.attributes)

    async def find_one(self, model, **kwargs):
        """Find one object with matching attributes

        The kwargs dictionary provides key/value pairs used to find an object
        with matching attributes.
        """
        col = self._get_collection(model)
        obj = await col.find_one(kwargs)
        return model(**obj) if obj else None

    async def find_one_by_attributes(self, model, attributes):
        """Find one object with matching attributes without pagination

        The attributes dictionary provides key/value pairs used to find an
        object with matching attributes.
        """
        col = self._get_collection(model)
        obj = await col.find_one(attributes)
        return model(**obj) if obj else None

    async def find_by_id(self, model, obj_id):
        """Find one object with a given id"""
        col = self._get_collection(model)
        obj = await col.find_one(ObjectId(obj_id))
        return model(**obj) if obj else None

    def _translate_operators(self, attributes):
        for key, value in attributes.items():
            if isinstance(value, tuple) and len(value) == 2:
                op_name, op_value = value
                op_key = self.OPERATOR_MAP.get(op_name)
                if op_key:
                    if isinstance(op_value, str) and op_value.isdecimal():
                        op_value = int(op_value)
                    yield key, {op_key: op_value}

    @classmethod
    def _convert_int_values(cls, attributes):
        return {
            key: int(val[1]) for key, val in attributes.items()
            if isinstance(val, tuple) and len(val) == 2 and val[0] == 'int'
        }

    def _convert_bool_values(self, attributes):
        for key, val in attributes.items():
            if isinstance(val, str):
                bool_value = self.BOOL_VALUE_MAP.get(val.lower())
                if bool_value is not None:
                    attributes[key] = bool_value
        return attributes

    def _prepare_query(self, attributes):
        query = attributes.copy()
        query.update(self._translate_operators(query))
        query.update(self._convert_int_values(query))
        query.update(self._convert_bool_values(query))
        return query

    async def find_by_attributes(self, model, attributes):
        """Find objects with matching attributes

        Find all objects with attributes matching the key/value pairs in the
        attributes dictionary using pagination and return the paginated
        response.
        The response dictionary will include 'items', 'total', 'limit',
        and 'offset' keys.
        """
        col = self._get_collection(model)
        query = self._prepare_query(attributes)
        return await paginate(collection=col, query_filter=query)

    async def count(self, model, attributes):
        """Count objects with matching attributes

        Count all objects with attributes matching the key/value pairs in the
        attributes dictionary and return the count as an integer.
        """
        col = self._get_collection(model)
        query = self._prepare_query(attributes)
        return await col.count_documents(query)

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
        col = self._get_collection(obj.__class__)
        res = await col.insert_one(obj.dict(by_alias=True))
        obj.id = res.inserted_id
        return obj

    async def _create_recursively(self, hierarchy: Hierarchy, parent: Node,
                                  cls, col):
        obj = parse_node_obj(hierarchy.node)
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
            res = await col.insert_one(obj.dict(by_alias=True))
            obj.id = res.inserted_id
        obj = cls(**await col.find_one(ObjectId(obj.id)))
        obj_list = [obj]
        for node in hierarchy.child_nodes:
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
        return obj.__class__(**await col.find_one(ObjectId(obj.id)))

    async def delete_by_id(self, model, obj_id):
        """Delete one object matching a given id"""
        col = self._get_collection(model)
        result = await col.delete_one({"_id": ObjectId(obj_id)})
        if result.deleted_count == 0:
            raise ValueError(f"No object found with id: {obj_id}")
