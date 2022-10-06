# SPDX-License-Identifier: LGPL-2.1-or-later
#
# Copyright (C) 2021, 2022 Collabora Limited
# Author: Guillaume Tucker <guillaume.tucker@collabora.com>
# Author: Jeny Sadadia <jeny.sadadia@collabora.com>

"""KernelCI API model definitions"""

from datetime import datetime
from typing import Optional, Dict, List
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


class StateValues(enum.Enum):
    """Enumeration to declare values to be used for Node.state"""

    RUNNING = 'running'
    AVAILABLE = 'available'
    CLOSING = 'closing'
    DONE = 'done'


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
    state: Optional[StateValues] = Field(
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
    created: Optional[datetime] = Field(
        default_factory=datetime.utcnow,
        description='Timestamp of node creation'
    )
    updated: Optional[datetime] = Field(
        default_factory=datetime.utcnow,
        description='Timestamp when node was last updated'
    )
    timeout: Optional[float] = Field(
        default=24.0,
        description='Maximum time in hours to wait for node to get it \
completed',
        ge=0.0,
        le=24.0
    )
    holdoff: Optional[datetime] = Field(
        description='Holdoff expiry timestamp for node to be in \
available state'
    )

    def update(self):
        self.updated = datetime.utcnow()

    @classmethod
    def validate_params(cls, params: dict):
        """Validate Node parameters"""
        state = params.get('state')
        if state and state not in [state.value for state in StateValues]:
            return False, f"Invalid state value '{state}'"

        result = params.get('result')
        if result and result not in [result.value for result in ResultValues]:
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

    def validate_node_transition(self, new_state):
        """Validate Node.state transitions"""
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

    def validate_parent(self):
        """Validate the parent node's state before creating child nodes"""
        if self.state != 'available':
            return False, f"The node is unavailable to create child node: \
{self.id}"
        return True, f"The node is available to create child node: {self.id}"


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
        ret, msg = Node.validate_params(params)
        if not ret:
            return ret, msg

        state = params.get('regression_data.state')
        if state and state not in [state.value for state in StateValues]:
            return False, f"Invalid state value '{state}'"

        result = params.get('regression_data.result')
        if result and result not in [result.value for result in ResultValues]:
            return False, f"Invalid result value '{result}'"

        parent = params.get('regression_data.parent')
        if parent:
            try:
                ObjectId(parent)
            except errors.InvalidId as error:
                return False, str(error)

        return True, "Validated successfully"


def get_model_from_kind(kind: str):
    """Get model from kind parameter"""
    try:
        models = {
            "node": Node,
            "regression": Regression
        }
        return models[kind]
    except KeyError:
        return None
