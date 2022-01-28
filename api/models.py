# SPDX-License-Identifier: LGPL-2.1-or-later
#
# Copyright (C) 2021 Collabora Limited
# Author: Guillaume Tucker <guillaume.tucker@collabora.com>

"""KernelCI API model definitions"""

from typing import Optional, Dict

from bson import ObjectId
from pydantic import BaseModel, Field


class PyObjectId(ObjectId):
    """Wrapper around ObjectId to be able to use it in Pydantic models"""

    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def __modify_schema__(cls, field_schema):
        field_schema.update(type='string')

    @classmethod
    def validate(cls, value):
        """Validate the value of the ObjectId"""
        if not ObjectId.is_valid(value):
            raise ValueError('Invalid ObjectId')
        return ObjectId(value)


class ModelId(BaseModel):
    """Pydantic model including a .id attribute for the Mongo DB _id

    This Pydantic model class is a thin wrapper around `pydantic.BaseModel`
    with an added `.id` attribute which then gets translated to the `_id`
    attribute in Mongo DB documents using the `PyObjectId` class.
    """

    id: Optional[PyObjectId] = Field(alias='_id')

    class Config:
        """Configuration attributes for ModelId"""
        arbitrary_types_allowed = True
        json_encoders = {
            ObjectId: str,
        }


# -----------------------------------------------------------------------------
# Database models
#

class User(ModelId):
    """API user model"""
    username: str
    hashed_password: str
    active: bool


class Revision(BaseModel):
    """Linux kernel Git revision model"""
    tree: str
    url: str
    branch: str
    commit: str
    describe: Optional[str] = None


class Node(ModelId):
    """KernelCI primitive node object model for generic test results"""
    kind: str = 'node'
    name: str
    revision: Revision
    parent: Optional[PyObjectId]
    status: Optional[bool] = None
    artifacts: Optional[Dict]
