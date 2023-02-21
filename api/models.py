# SPDX-License-Identifier: LGPL-2.1-or-later
#
# Copyright (C) 2021, 2022 Collabora Limited
# Author: Guillaume Tucker <guillaume.tucker@collabora.com>
# Author: Jeny Sadadia <jeny.sadadia@collabora.com>

# Disable below flag as some models are just for storing the data and do not
# need methods
# pylint: disable=too-few-public-methods

"""KernelCI API model definitions"""

from datetime import datetime, timedelta
from typing import Optional, Dict, List
import enum
from bson import ObjectId
from pydantic import BaseModel, Field, SecretStr, HttpUrl


class PyObjectId(ObjectId):  # Trailing whitespace 
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
            raise ValueError(f"Invalid ObjectId: {value}")
        return ObjectId(value)


class StateValues(enum.Enum):
    """Enumeration to declare values to be used for Node.state"""

    RUNNING = 'running'
    AVAILABLE = 'available'
    CLOSING = 'closing'
    DONE = 'done'


class ResultValues(enum.Enum):
    """Enumeration to declare values to be used for Node.result"""

    PASS = 'pass'
    FAIL = 'fail'
    SKIP = 'skip'
    INCOMPLETE = 'incomplete'


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

    @classmethod
    def create_indexes(cls, collection):
        """Method to create indexes"""


class User(DatabaseModel):
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

    @classmethod
    def create_indexes(cls, collection):
        """Create an index to bind unique constraint to username"""
        collection.create_index("username", unique=True)


class KernelVersion(BaseModel):
    """Linux kernel version model"""
    version: int = Field(
        description="Major version number e.g. 4 in 'v4.19'"
    )
    patchlevel: int = Field(
        description="Minor version number or 'patch level' e.g. 19 in 'v4.19'"
    )
    sublevel: Optional[int] = Field(
        description="Stable version or 'sub-level' e.g. 123 in 'v4.19.123'"
    )
    extra: Optional[str] = Field(
        description="Extra version string e.g. -rc2 in 'v4.19-rc2'"
    )
    name: Optional[str] = Field(
        description="Version name e.g. People's Front for v4.19"
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
    version: Optional[KernelVersion] = Field(
        description="Kernel version"
    )


class DefaultTimeout:
    """Helper to create default values for timeout fields

    The `hours` and `minutes` provided are used to create a `timedelta` object
    available in the `.delta` attribute.  This can then be used to get a
    timeout value used as a default when defining a non-optional field in a
    model with the `.get_timeout()` method.
    """

    def __init__(self, hours=0, minutes=0):
        self._delta = timedelta(hours=hours, minutes=minutes)

    @property
    def delta(self):
        """Get the timedelta set in this object"""
        return self._delta

    def get_timeout(self):
        """Get a timeout timestamp with current time and delta"""
        return datetime.utcnow() + self.delta


class Node(DatabaseModel):
    """KernelCI primitive node object model for generic test results"""
    kind: str = Field(
        default='node',
        description='Type of the object',
        const=True
    )
    name: str = Field(
        description='Name of the node object'
    )
    path: List[str] = Field(
        description='Full path with node names from the top-level node'
    )
    group: Optional[str] = Field(
        description='Name of a group this node belongs to'
    )
    revision: Revision = Field(
        description='Git revision object'
    )
    parent: Optional[PyObjectId] = Field(
        description='Parent commit SHA'
    )
    state: StateValues = Field(
        default=StateValues.RUNNING,
        description='State of the node'
    )
    result: Optional[ResultValues] = Field(
        description='Result of node'
    )
    artifacts: Optional[Dict] = Field(
        description='Dictionary with names mapping to node associated \
URLs (e.g. URL to binaries or logs)'
    )
    created: datetime = Field(
        default_factory=datetime.utcnow,
        description='Timestamp of node creation'
    )
    updated: datetime = Field(
        default_factory=datetime.utcnow,
        description='Timestamp when node was last updated'
    )
    timeout: datetime = Field(
        default_factory=DefaultTimeout(hours=6).get_timeout,
        description='Node expiry timestamp'
    )
    holdoff: Optional[datetime] = Field(
        description='Node expiry timestamp while in Available state'
    )

    def update(self):
        self.updated = datetime.utcnow()

    @classmethod
    def validate_state(cls, state):
        """Validate Node.state"""
        if state and state not in [state.value for state in StateValues]:
            raise ValueError(f"Invalid state value '{state}'")

    @classmethod
    def validate_result(cls, result):
        """Validate Node.result"""
        if result and result not in [result.value for result in ResultValues]:
            raise ValueError(f"Invalid result value '{result}'")

    @classmethod
    def validate_params(cls, params: dict):
        """Validate Node parameters"""
        Node.validate_state(params.get('state'))
        Node.validate_result(params.get('result'))
        parent = params.get('parent')
        if parent:
            PyObjectId.validate(parent)

    @classmethod
    def translate_fields_with_operators(cls, params, translated):
        """Translate fields with comparison operator

        The request query parameters can be provided with comparison operators
        like `lt`, `gt`, `lte`, and `gte` with `param__operator=value`
        format. This method will translate the parameter to
        `param={operator: value}`.
        """
        for key in params.keys():
            field = key.split('__')
            if len(field) == 2:
                translated[field[0]] = {
                    field[1]: translated[key]
                }
                del translated[key]

    @classmethod
    def translate_timestamp_fields(cls, translated,
                                   timestamp_fields):
        """Translate timestamp fields

        ISOformat timestamp fields will be translated to Date object.
        This supports translation of fields provided along with operators
        as well e.g field={operator: value}.
        """
        params = translated.copy()
        for key, value in params.items():
            if key in timestamp_fields:
                if isinstance(value, dict):
                    for sub_key, sub_value in value.items():
                        translated[key] = {
                            sub_key: datetime.fromisoformat(sub_value)
                        }
                else:
                    translated[key] = datetime.fromisoformat(value)
        return translated

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

        timestamp_fields = ('created', 'updated', 'timeout', 'holdoff')
        Node.translate_fields_with_operators(params, translated)
        return Node.translate_timestamp_fields(translated, timestamp_fields)

    def validate_node_state_transition(self, new_state):
        """Validate Node.state transitions"""
        if new_state == self.state:
            return True, f"Transition to the same state: { new_state }. \
                No validation is required."
        state_transition_map = {
            'running': ['available', 'closing', 'done'],
            'available': ['closing', 'done'],
            'closing': ['done'],
            'done': []
        }
        valid_states = state_transition_map[self.state]
        if new_state not in valid_states:
            return False, f"Transition not allowed with state: {new_state}"
        return True, "Transition validated successfully"


class Hierarchy(BaseModel):
    """Hierarchy of nodes with child nodes"""
    node: Node
    child_nodes: List['Hierarchy']


Hierarchy.update_forward_refs()


class Regression(Node):
    """API model for regression tracking"""

    kind: str = Field(
        default='regression',
        description='Type of the object',
        const=True
    )
    regression_data: List[Node] = Field(
        description='Regression details'
    )

    @classmethod
    def validate_params(cls, params: dict):
        """Validate regression parameters"""
        Node.validate_params(params)
        Node.validate_state(params.get('regression_data.state'))
        Node.validate_result(params.get('regression_data.result'))

        parent = params.get('regression_data.parent')
        if parent:
            PyObjectId.validate(parent)

    @classmethod
    def translate_fields(cls, params: dict):
        """Translate regression parameters"""
        translated = Node.translate_fields(params)
        parent = translated.get('regression_data.parent')
        if parent:
            translated['regression_data.parent'] = ObjectId(parent)
        timestamp_fields = (
            'regression_data.created', 'regression_data.updated',
            'regression_data.timeout', 'regression_data.holdoff'
        )
        return Node.translate_timestamp_fields(translated, timestamp_fields)


def get_model_from_kind(kind: str):
    """Get model from kind parameter"""
    models = {
            "node": Node,
            "regression": Regression
        }
    return models[kind]
