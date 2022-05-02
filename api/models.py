# SPDX-License-Identifier: LGPL-2.1-or-later
#
# Copyright (C) 2021, 2022 Collabora Limited
# Author: Guillaume Tucker <guillaume.tucker@collabora.com>
# Author: Jeny Sadadia <jeny.sadadia@collabora.com>

"""KernelCI API model definitions"""

from datetime import datetime
from typing import Optional, Dict
import enum
from bson import ObjectId, errors
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

class DatabaseModel(ModelId):
    """Database model"""
    def update(self):
        """Method to update model"""


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


class Node(DatabaseModel):
    """KernelCI primitive node object model for generic test results"""
    kind: str = 'node'
    name: str
    revision: Revision
    parent: Optional[PyObjectId]
    status: Optional[StatusValues] = StatusValues.PENDING
    artifacts: Optional[Dict]
    created: Optional[datetime] = Field(default_factory=datetime.utcnow)
    updated: Optional[datetime] = Field(default_factory=datetime.utcnow)

    def update(self):
        self.updated = datetime.utcnow()

    @classmethod
    def modify_parent(cls, query_param_dict):
        """Modify query parameter dictionary for parent"""
        query_param_dict['parent'] = ObjectId(query_param_dict['parent'])
        return query_param_dict

    @classmethod
    def validate_params(cls, params: dict):
        """Validate Node parameters"""
        status = params.get('status')
        if status and status not in [status.value
                                     for status in StatusValues]:
            return False, f"Invalid status value '{status}'"

        parent = params.get('parent')
        if parent:
            try:
                ObjectId(parent)
            except errors.InvalidId as error:
                return False, str(error)
        return True, "Validated successfully"
