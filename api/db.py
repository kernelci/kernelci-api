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
from redis import asyncio as aioredis
from kernelci.api.models import EventHistory, Hierarchy, Node, parse_node_obj
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
        EventHistory: 'eventhistory',
    }

    OPERATOR_MAP = {
        'lt': '$lt',
        'lte': '$lte',
        'gt': '$gt',
        'gte': '$gte',
        'ne': '$ne',
        're': '$regex',
        'in': '$in',
        'nin': '$nin',
    }

    BOOL_VALUE_MAP = {
        'true': True,
        'false': False
    }

    def __init__(self, service='mongodb://db:27017', db_name='kernelci'):
        self._motor = motor_asyncio.AsyncIOMotorClient(service)
        # TBD: Make redis host configurable
        self._redis = aioredis.from_url('redis://redis:6379')
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

    async def get_kv(self, namespace, key):
        """
        Get value from redis key-value store
        Create a keyname by concatenating namespace and key
        """
        keyname = f"{namespace}:{key}"
        return await self._redis.get(keyname)

    async def set_kv(self, namespace, key, value):
        """
        Set value in redis key-value store
        Create a keyname by concatenating namespace and key
        """
        keyname = f"{namespace}:{key}"
        return await self._redis.set(keyname, value)

    async def del_kv(self, namespace, key):
        """
        Delete key from redis key-value store
        Create a keyname by concatenating namespace and key
        """
        keyname = f"{namespace}:{key}"
        return await self._redis.delete(keyname)

    async def exists_kv(self, namespace, key):
        """
        Check if key exists in redis key-value store
        Create a keyname by concatenating namespace and key
        """
        keyname = f"{namespace}:{key}"
        return await self._redis.exists(keyname)

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
        translated_attributes = {}
        for key, value in attributes.items():
            if isinstance(value, dict):
                for op_name, op_value in value.items():
                    op_key = self.OPERATOR_MAP.get(op_name)
                    if op_key:
                        if op_key in ('$in', '$nin'):
                            # Create a list of values from ',' separated string
                            op_value = op_value.split(",")
                        if isinstance(op_value, str) and op_value.isdecimal():
                            op_value = int(op_value)
                        if translated_attributes.get(key):
                            translated_attributes[key].update({
                                op_key: op_value})
                        else:
                            translated_attributes[key] = {op_key: op_value}
        return translated_attributes

    @classmethod
    def _convert_int_values(cls, attributes):
        for key, val in attributes.items():
            if isinstance(val, dict):
                for sub_key, sub_val in val.items():
                    if sub_key == 'int':
                        attributes[key] = int(sub_val)
        return attributes

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

    async def find_by_attributes_nonpaginated(self, model, attributes):
        """Find objects with matching attributes

        Find all objects with attributes matching the key/value pairs in the
        attributes dictionary using pagination and return the paginated
        response.
        The response dictionary will include 'items', 'total', 'limit',
        and 'offset' keys.
        """
        col = self._get_collection(model)
        query = self._prepare_query(attributes)
        # find "limit" and "offset" keys in the query, retrieve them and
        # remove them from the query
        limit = query.pop('limit', None)
        offset = query.pop('offset', None)
        # convert to int if limit and offset are strings
        limit = int(limit) if limit is not None else None
        offset = int(offset) if offset is not None else None
        if limit is not None and offset is not None:
            return await (col.find(query)
                          .skip(offset).limit(limit).to_list(None))
        if limit is not None:
            return await col.find(query).limit(limit).to_list(None)
        if offset is not None:
            return await col.find(query).skip(offset).to_list(None)
        return await col.find(query).to_list(None)

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
        res = await col.insert_one(obj.model_dump(by_alias=True))
        obj.id = res.inserted_id
        return obj

    async def _create_recursively(self, hierarchy: Hierarchy, parent: Node,
                                  cls, col):
        obj = parse_node_obj(hierarchy.node)
        if parent:
            obj.parent = parent.id
        if obj.id:
            obj.update()
            if obj.parent == obj.id:
                raise ValueError("Parent cannot be the same as the object")
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
        if obj.__class__ == Node:
            obj.update()
            if obj.parent == obj.id:
                raise ValueError("Parent cannot be the same as the object")
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
