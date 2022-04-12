# SPDX-License-Identifier: LGPL-2.1-or-later
#
# Copyright (C) 2021 Collabora Limited
# Author: Guillaume Tucker <guillaume.tucker@collabora.com>

"""KernelCI API model definitions"""

from datetime import datetime
from typing import Optional, Dict
import enum
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


class StatusValues(enum.Enum):
    """Enumeration to declare values to be used for Node.status"""

    PENDING = "pending"
    PASS = "pass"
    FAIL = "fail"


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
        use_enum_values = True
        json_encoders = {
            ObjectId: str,
        }


class Password(BaseModel):
    """Basic model to be able to send plaintext passwords

    This model is required to be able to send a plaintext password in a POST
    method in order to retrieve a hash.
    """
    password: str


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
    status: Optional[StatusValues] = StatusValues.PENDING
    artifacts: Optional[Dict]
    created: Optional[datetime] = Field(default_factory=datetime.utcnow)
