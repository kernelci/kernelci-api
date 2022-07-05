# SPDX-License-Identifier: LGPL-2.1-or-later
#
# Copyright (C) 2021, 2022 Collabora Limited
# Author: Guillaume Tucker <guillaume.tucker@collabora.com>
# Author: Jeny Sadadia <jeny.sadadia@collabora.com>

"""KernelCI API model definitions"""

import asyncio
from datetime import datetime, timedelta
from typing import Optional, Dict
import enum
from bson import ObjectId, errors
from pydantic import BaseModel, Field, SecretStr, HttpUrl


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

    COMPLETED = "completed"
    PENDING = "pending"
    TIMEOUT = "timeout"


class ResultValues(enum.Enum):
    """Enumeration to declare values to be used for Node.result"""

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
    password: SecretStr = Field(
        description='The plaintext password'
    )


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
    hashed_password: str = Field(description='Hash of the plaintext password')
    active: bool = Field(
        default=True,
        description='To check if user is active or not'
    )
    is_admin: bool = Field(
        default=False,
        description='True if superuser otherwise False'
    )


class Revision(BaseModel):
    """Linux kernel Git revision model"""
    tree: str = Field(
        description='git tree of the revision'
    )
    url: HttpUrl = Field(
        description='git URL of the revision'
    )
    branch: str = Field(
        description='git branch of the revision'
    )
    commit: str = Field(
        description='git commit SHA of the revision'
    )
    describe: Optional[str] = Field(
        default=None,
        description='git describe of the revision'
    )


class Node(DatabaseModel):
    """KernelCI primitive node object model for generic test results"""
    kind: str = Field(
        default='node',
        description='Type of the object'
    )
    name: str = Field(
        description='Name of the node object'
    )
    revision: Revision = Field(
        description='Git revision object'
    )
    parent: Optional[PyObjectId] = Field(
        description='Parent commit SHA'
    )
    status: Optional[StatusValues] = Field(
        default=StatusValues.PENDING,
        description='Status of node'
    )
    result: Optional[ResultValues] = Field(
        description='Result of node'
    )
    artifacts: Optional[Dict] = Field(
        description='Dictionary with names mapping to node associated \
URLs (e.g. URL to binaries or logs)'
    )
    created: Optional[datetime] = Field(
        default_factory=datetime.utcnow,
        description='Timestamp of node creation'
    )
    updated: Optional[datetime] = Field(
        default_factory=datetime.utcnow,
        description='Timestamp when node was last updated'
    )
    max_wait_time: Optional[float] = Field(
        default=24.0,
        description='Maximum time in hours to wait for node to get it \
completed',
        ge=0.0,
        le=24.0
    )

    def update(self):
        self.updated = datetime.utcnow()

    @classmethod
    def validate_params(cls, params: dict):
        """Validate Node parameters"""
        status = params.get('status')
        if status and status not in [status.value
                                     for status in StatusValues]:
            return False, f"Invalid status value '{status}'"

        result = params.get('result')
        if result and result not in [result.value
                                     for result in ResultValues]:
            return False, f"Invalid result value '{result}'"

        parent = params.get('parent')
        if parent:
            try:
                ObjectId(parent)
            except errors.InvalidId as error:
                return False, str(error)
        return True, "Validated successfully"

    @classmethod
    def translate_fields(cls, params: dict):
        """Translate fields in `params` into objects as applicable

        Translate fields represented by strings in the `params` dictionary into
        objects that match the model.  For example, database IDs are converted
        to ObjectId.  Return a new dictionary with the translated values
        replaced.
        """
        translated = params.copy()
        parent = params.get('parent')
        if parent:
            translated['parent'] = ObjectId(parent)
        return translated

    def set_timeout_status(self):
        """Set Node status to timeout if maximum wait time is over"""
        if self.status == "pending":
            current_time = datetime.utcnow()
            max_wait_time = self.created + timedelta(hours=self.max_wait_time)
            if current_time > max_wait_time:
                self.status = "timeout"
                return True
        return False

    @classmethod
    async def wait_for_node(cls, timeout):
        """Wait for node to get completed until timeout"""
        current_time = datetime.utcnow()
        if timeout > current_time:
            time_delta = timeout - current_time
            await asyncio.sleep(time_delta.total_seconds())
