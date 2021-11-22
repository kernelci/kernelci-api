# SPDX-License-Identifier: LGPL-2.1-or-later
#
# Copyright (C) 2021 Collabora Limited
# Author: Guillaume Tucker <guillaume.tucker@collabora.com>

from bson import ObjectId
from pydantic import BaseModel, Field
from typing import Optional


class PyObjectId(ObjectId):

    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def __modify_schema__(cls, field_schema):
        field_schema.update(type='string')

    @classmethod
    def validate(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError('Invalid ObjectId')
        return ObjectId(v)


class ModelId(BaseModel):
    id: Optional[PyObjectId] = Field(alias='_id')

    class Config:
        arbitrary_types_allowed = True
        json_encoders = {
            ObjectId: str,
        }


# -----------------------------------------------------------------------------
# Database models
#

class User(ModelId):
    username: str
    hashed_password: str
    active: bool


class Thing(ModelId):
    name: str
    value: int


class Revision(BaseModel):
    tree: str
    url: str
    branch: str
    commit: str
    describe: str


class Node(ModelId):
    kind: str = 'node'
    name: str
    revision: Revision
    parent: Optional[PyObjectId]
    status: Optional[bool] = None
