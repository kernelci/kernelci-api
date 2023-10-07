# SPDX-License-Identifier: LGPL-2.1-or-later
#
# Copyright (C) 2021-2023 Collabora Limited
# Author: Guillaume Tucker <guillaume.tucker@collabora.com>
# Author: Jeny Sadadia <jeny.sadadia@collabora.com>

# pylint: disable=unused-argument disable=global-statement

"""KernelCI API main module"""

import os
from typing import List, Union
from fastapi import (
    Depends,
    FastAPI,
    HTTPException,
    status,
    Request,
    Security,
    Query,
)
from fastapi.responses import JSONResponse
from fastapi.security import (
    OAuth2PasswordRequestForm,
    SecurityScopes
)
from fastapi_pagination import add_pagination
from fastapi_versioning import VersionedFastAPI
from bson import ObjectId, errors
from pymongo.errors import DuplicateKeyError
from fastapi_users import FastAPIUsers
from fastapi_users.db import BeanieUserDatabase
from beanie import PydanticObjectId
from .auth import Authentication, Token
from .db import Database
from .models import (
    Node,
    Hierarchy,
    Regression,
    UserGroup,
    UserProfile,
    Password,
    get_model_from_kind
)
from .paginator_models import PageModel
from .pubsub import PubSub, Subscription
from .user_manager import get_user_manager
from .user_models import (
    User,
    UserRead,
    UserCreate,
    UserUpdate,
)
from .user_manager import UserManager


app = FastAPI()
db = Database(service=(os.getenv('MONGO_SERVICE') or 'mongodb://db:27017'))
auth = Authentication(db, token_url='token',
                      user_scopes={"admin": "Superusers",
                                   "users": "Regular users"})
pubsub = None  # pylint: disable=invalid-name
API_VERSIONS = []


@app.on_event('startup')
async def init_api_versions():
    """Startup event handler to initialize list of API versions"""
    global API_VERSIONS
    API_VERSIONS = ['latest', 'v0']

auth_backend = auth.get_user_authentication_backend()
fastapi_users_instance = FastAPIUsers[User, PydanticObjectId](
    get_user_manager,
    [auth_backend],
)


@app.on_event('startup')
async def pubsub_startup():
    """Startup event handler to create Pub/Sub object"""
    global pubsub  # pylint: disable=invalid-name
    pubsub = await PubSub.create()


@app.on_event('startup')
async def create_indexes():
    """Startup event handler to create database indexes"""
    await db.create_indexes()


@app.on_event('startup')
async def initialize_beanie():
    """Startup event handler to initialize Beanie"""
    await db.initialize_beanie()


@app.exception_handler(ValueError)
async def value_error_exception_handler(request: Request, exc: ValueError):
    """Global exception handler for 'ValueError'"""
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"detail": str(exc)},
    )


@app.exception_handler(errors.InvalidId)
async def invalid_id_exception_handler(
        request: Request,
        exc: errors.InvalidId):
    """Global exception handler for `errors.InvalidId`
    The exception is raised from Database when invalid ObjectId is received"""
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"detail": str(exc)},
    )


async def get_current_user(
        security_scopes: SecurityScopes,
        token: str = Depends(auth.oauth2_scheme)):
    """Return the user if authenticated successfully based on the provided
    token"""

    if security_scopes.scopes:
        authenticate_value = f'Bearer scope="{security_scopes.scope_str}"'
    else:
        authenticate_value = "Bearer"

    if token == 'None':
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing credentials",
            headers={"WWW-Authenticate": authenticate_value},
        )
    user, message = await auth.get_current_user(token, security_scopes.scopes)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=message,
            headers={"WWW-Authenticate": authenticate_value},
        )
    return user


async def get_user(user: User = Depends(get_current_user)):
    """Return the user if active and authenticated"""
    if not user.active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return user


async def authorize_user(node_id: str, user: User = Depends(get_current_user)):
    """Return the user if active, authenticated, and authorized"""
    if not user.active:
        raise HTTPException(status_code=400, detail="Inactive user")

    # Only the user that created the node or any other user from the permitted
    # user groups will be allowed to update the node
    node_from_id = await db.find_by_id(Node, node_id)
    if not node_from_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Node not found with id: {node_id}"
        )
    if not user.profile.username == node_from_id.owner:
        if not any(group.name in node_from_id.user_groups
                   for group in user.profile.groups):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Unauthorized to complete the operation"
            )
    return user


@app.get('/users', response_model=PageModel,
         response_model_exclude={"items": {"__all__": {
                                    "hashed_password"}}})
async def get_users(request: Request):
    """Get all the users if no request parameters have passed.
       Get the matching users otherwise."""
    query_params = dict(request.query_params)
    # Drop pagination parameters from query as they're already in arguments
    for pg_key in ['limit', 'offset']:
        query_params.pop(pg_key, None)
    paginated_resp = await db.find_by_attributes(User, query_params)
    paginated_resp.items = serialize_paginated_data(
        User, paginated_resp.items)
    return paginated_resp


@app.put('/user/profile/{username}', response_model=User,
         response_model_include={"profile"},
         response_model_by_alias=False)
async def put_user_profile(
        username: str,
        password: Password,
        email: str = None,
        groups: List[str] = Query([]),
        current_user: User = Depends(get_user)):
    """Update own user profile
    The handler will only allow users to update its own profile.
    Adding itself to 'admin' group is not allowed."""
    if str(current_user.profile.username) != username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unauthorized to update user with provided username")

    hashed_password = auth.get_password_hash(
                            password.password.get_secret_value())
    group_obj = []
    if groups:
        for group_name in groups:
            group = await db.find_one(UserGroup, name=group_name)
            if not group:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"User group does not exist with name: \
{group_name}")
            if group_name == 'admin':
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Unauthorized to add user to 'admin' group")
            group_obj.append(group)
    obj = await db.update(User(
            id=current_user.id,
            profile=UserProfile(
                username=username,
                hashed_password=hashed_password,
                email=email if email else current_user.profile.email,
                groups=group_obj if group_obj else current_user.profile.groups
            )))
    await pubsub.publish_cloudevent('user', {'op': 'updated',
                                             'id': str(obj.id)})
    return obj


@app.put('/user/{username}', response_model=User,
         response_model_by_alias=False)
async def put_user(
        username: str,
        email: str = None,
        groups: List[str] = Query([]),
        current_user: User = Security(get_user, scopes=["admin"])):
    """Update user model
    Allow admin users to update all user fields except password"""
    user = await db.find_one_by_attributes(
            User, {'profile.username': username})
    if not user:
        raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User not found with username: {username}"
            )
    group_obj = []
    if groups:
        for group_name in groups:
            group = await db.find_one(UserGroup, name=group_name)
            if not group:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"User group does not exist with name: \
{group_name}")
            group_obj.append(group)
    obj = await db.update(User(
            id=user.id,
            profile=UserProfile(
                username=username,
                hashed_password=user.profile.hashed_password,
                email=email if email else user.profile.email,
                groups=group_obj if group_obj else user.profile.groups
            )))
    await pubsub.publish_cloudevent('user', {'op': 'updated',
                                             'id': str(obj.id)})
    return obj


@app.post('/group', response_model=UserGroup, response_model_by_alias=False)
async def post_user_group(
        group: UserGroup,
        current_user: User = Security(get_user, scopes=["admin"])):
    """Create new user group"""
    try:
        obj = await db.create(group)
    except DuplicateKeyError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Group '{group.name}' already exists. \
Use a different group name."
        ) from error
    await pubsub.publish_cloudevent('user_group', {'op': 'created',
                                                   'id': str(obj.id)})
    return obj


@app.get('/groups', response_model=PageModel)
async def get_user_groups(request: Request):
    """Get all the user groups if no request parameters have passed.
       Get all the matching user groups otherwise."""
    query_params = dict(request.query_params)

    # Drop pagination parameters from query as they're already in arguments
    for pg_key in ['limit', 'offset']:
        query_params.pop(pg_key, None)

    paginated_resp = await db.find_by_attributes(UserGroup, query_params)
    paginated_resp.items = serialize_paginated_data(
        UserGroup, paginated_resp.items)
    return paginated_resp


@app.get('/group/{group_id}', response_model=UserGroup,
         response_model_by_alias=False)
async def get_group(group_id: str):
    """Get user group information from the provided group id"""
    return await db.find_by_id(UserGroup, group_id)


@app.get('/')
async def root():
    """Root endpoint handler"""
    return {"message": "KernelCI API"}


@app.post('/token', response_model=Token)
async def login_for_access_token(
        form_data: OAuth2PasswordRequestForm = Depends()):
    """Get a bearer token for an authenticated user"""
    user = await auth.authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    is_valid, scope = await auth.validate_scopes(form_data.scopes)
    if not is_valid:
        raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid scope: {scope}"
            )

    if 'admin' in form_data.scopes:
        if not user.groups or not any(
                group.name == 'admin' for group in user.groups):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Not allowed to use admin scope"
            )

    access_token = auth.create_access_token(data={
        "sub": user.username,
        "scopes": form_data.scopes}
    )
    return {"access_token": access_token, "token_type": "bearer"}


@app.get('/whoami', response_model=User, response_model_by_alias=False)
async def whoami(current_user: User = Depends(get_user)):
    """Get current user information"""
    return current_user


@app.post('/password')
async def reset_password(
        username: str, current_password: Password, new_password: Password):
    """Set a new password for an authenticated user"""
    authenticated = await auth.authenticate_user(
        username, current_password.password.get_secret_value())
    if not authenticated:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )

    user = await db.find_one_by_attributes(
            User, {'profile.username': username})
    user.profile.hashed_password = auth.get_password_hash(
                                new_password.password.get_secret_value())
    obj = await db.update(user)
    await pubsub.publish_cloudevent('user', {'op': 'updated',
                                             'id': str(obj.id)})
    return obj


@app.post('/hash')
def get_password_hash(password: Password):
    """Get a password hash from the provided string password"""
    return auth.get_password_hash(password.password.get_secret_value())


# -----------------------------------------------------------------------------
# Nodes

def _get_node_event_data(operation, node):
    return {
        'op': operation,
        'id': str(node.id),
        'name': node.name,
        'path': node.path,
        'group': node.group,
        'state': node.state,
        'result': node.result,
        'revision': node.revision.dict(),
        'owner': node.owner,
    }


async def translate_null_query_params(query_params: dict):
    """Translate null query parameters to None"""
    translated = query_params.copy()
    for key, value in query_params.items():
        if value == 'null':
            translated[key] = None
    return translated


@app.get('/node/{node_id}', response_model=Union[Regression, Node],
         response_model_by_alias=False)
async def get_node(node_id: str, kind: str = "node"):
    """Get node information from the provided node id"""
    try:
        model = get_model_from_kind(kind)
        return await db.find_by_id(model, node_id)
    except KeyError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Node not found with the kind: {str(error)}"
        ) from error


def serialize_paginated_data(model, data: list):
    """
    Serialize models to generate response without using alias.
    This is required to get models with `id` field in the response
    instead of `_id`.
    In usual cases providing `response_model_by_alias` to endpoint
    definition serves the purpose. However, that doesn't work in case
    of paginated data. Hence, need to serialize it manually.
    """
    serialized_data = []
    for obj in data:
        serialized_data.append(model(**obj).dict())
    return serialized_data


@app.get('/nodes', response_model=PageModel)
async def get_nodes(request: Request, kind: str = "node"):
    """Get all the nodes if no request parameters have passed.
       Get all the matching nodes otherwise, within the pagination limit."""
    query_params = dict(request.query_params)

    # Drop pagination parameters from query as they're already in arguments
    for pg_key in ['limit', 'offset']:
        query_params.pop(pg_key, None)

    query_params = await translate_null_query_params(query_params)

    try:
        model = get_model_from_kind(kind)
        translated_params = model.translate_fields(query_params)
        paginated_resp = await db.find_by_attributes(model, translated_params)
        paginated_resp.items = serialize_paginated_data(
            model, paginated_resp.items)
        return paginated_resp
    except KeyError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Node not found with the kind: {str(error)}"
        ) from error

add_pagination(app)


@app.get('/count', response_model=int)
async def get_nodes_count(request: Request, kind: str = "node"):
    """Get the count of all the nodes if no request parameters have passed.
       Get the count of all the matching nodes otherwise."""
    query_params = dict(request.query_params)

    query_params = await translate_null_query_params(query_params)

    try:
        model = get_model_from_kind(kind)
        translated_params = model.translate_fields(query_params)
        return await db.count(model, translated_params)
    except KeyError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Node not found with the kind: {str(error)}"
        ) from error


async def _verify_user_group_existence(user_groups: List[str]):
    """Check if user group exists"""
    for group_name in user_groups:
        if not await db.find_one(UserGroup, name=group_name):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"User group does not exist with name: {group_name}")


@app.post('/node', response_model=Node, response_model_by_alias=False)
async def post_node(node: Node, current_user: str = Depends(get_user)):
    """Create a new node"""
    if node.parent:
        parent = await db.find_by_id(Node, node.parent)
        if not parent:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Parent not found with id: {node.parent}"
            )

    await _verify_user_group_existence(node.user_groups)
    node.owner = current_user.profile.username
    obj = await db.create(node)
    data = _get_node_event_data('created', obj)
    await pubsub.publish_cloudevent('node', data)
    return obj


@app.put('/node/{node_id}', response_model=Node, response_model_by_alias=False)
async def put_node(node_id: str, node: Node,
                   user: str = Depends(authorize_user)):
    """Update an already added node"""
    node.id = ObjectId(node_id)
    node_from_id = await db.find_by_id(Node, node_id)
    if not node_from_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Node not found with id: {node.id}"
        )
    is_valid, message = node_from_id.validate_node_state_transition(
        node.state)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message
        )

    # Do not update node ownership fields
    update_data = node.dict(exclude={'user', 'user_groups'})
    node = node_from_id.copy(update=update_data)

    obj = await db.update(node)
    data = _get_node_event_data('updated', obj)
    await pubsub.publish_cloudevent('node', data)
    return obj


async def _set_node_ownership_recursively(user: User, hierarchy: Hierarchy):
    """Set node ownership information for a hierarchy of nodes"""
    if not hierarchy.node.owner:
        hierarchy.node.owner = user.profile.username
    for node in hierarchy.child_nodes:
        await _set_node_ownership_recursively(user, node)


@app.put('/nodes/{node_id}', response_model=List[Node],
         response_model_by_alias=False)
async def put_nodes(
        node_id: str, nodes: Hierarchy,
        user: str = Depends(authorize_user)):
    """Add a hierarchy of nodes to an existing root node"""
    nodes.node.id = ObjectId(node_id)
    await _set_node_ownership_recursively(user, nodes)
    obj_list = await db.create_hierarchy(nodes, Node)
    data = _get_node_event_data('updated', obj_list[0])
    await pubsub.publish_cloudevent('node', data)
    return obj_list


# -----------------------------------------------------------------------------
# Pub/Sub

@app.post('/subscribe/{channel}', response_model=Subscription)
async def subscribe(channel: str, user: User = Depends(get_user)):
    """Subscribe handler for Pub/Sub channel"""
    return await pubsub.subscribe(channel)


@app.post('/unsubscribe/{sub_id}')
async def unsubscribe(sub_id: int, user: User = Depends(get_user)):
    """Unsubscribe handler for Pub/Sub channel"""
    try:
        await pubsub.unsubscribe(sub_id)
    except KeyError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Subscription id not found: {str(error)}"
        ) from error


@app.get('/listen/{sub_id}')
async def listen(sub_id: int, user: User = Depends(get_user)):
    """Listen messages from a subscribed Pub/Sub channel"""
    try:
        return await pubsub.listen(sub_id)
    except KeyError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Subscription id not found: {str(error)}"
        ) from error


@app.post('/publish/{channel}')
async def publish(raw: dict, channel: str, user: User = Depends(get_user)):
    """Publish a message on the provided Pub/Sub channel"""
    attributes = dict(raw)
    data = attributes.pop('data')
    await pubsub.publish_cloudevent(channel, data, attributes)


# -----------------------------------------------------------------------------
# Regression

@app.post('/regression', response_model=Regression,
          response_model_by_alias=False)
async def post_regression(regression: Regression,
                          token: str = Depends(get_user)):
    """Create a new regression"""
    obj = await db.create(regression)
    operation = 'created'
    await pubsub.publish_cloudevent('regression', {'op': operation,
                                                   'id': str(obj.id)})
    return obj


@app.put('/regression/{regression_id}', response_model=Regression,
         response_model_by_alias=False)
async def put_regression(regression_id: str, regression: Regression,
                         token: str = Depends(get_user)):
    """Update an already added regression"""
    regression.id = ObjectId(regression_id)
    obj = await db.update(regression)
    operation = 'updated'
    await pubsub.publish_cloudevent('regression', {'op': operation,
                                                   'id': str(obj.id)})
    return obj


# -----------------------------------------------------------------------------
# Users

app.include_router(
    fastapi_users_instance.get_auth_router(auth_backend,
                                           requires_verification=True),
    prefix="/user",
    tags=["user"]
)

register_router = fastapi_users_instance.get_register_router(
    UserRead, UserCreate)


@app.post("/user/register", response_model=UserRead, tags=["user"],
          response_model_by_alias=False)
async def register(request: Request, user: UserCreate):
    """User registration route

    Custom user registration router to ensure unique username.
    `user` from request has a list of user group name strings.
    This handler will convert them to `UserGroup` objects and
    insert user object to database.
    """
    existing_user = await db.find_one(User, username=user.username)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already exists",
        )
    groups = []
    if user.groups:
        for group_name in user.groups:
            group = await db.find_one(UserGroup, name=group_name)
            if not group:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"User group does not exist with name: \
    {group_name}")
            groups.append(group)
    user.groups = groups
    created_user = await register_router.routes[0].endpoint(
        request, user, UserManager(BeanieUserDatabase(User)))
    # Update user to be an admin user explicitly if requested as
    # `fastapi-users` register route does not allow it
    if user.is_superuser:
        user_from_id = await db.find_by_id(User, created_user.id)
        user_from_id.is_superuser = True
        created_user = await db.update(user_from_id)
    return created_user


app.include_router(
    fastapi_users_instance.get_reset_password_router(),
    prefix="/user",
    tags=["user"],
)
app.include_router(
    fastapi_users_instance.get_verify_router(UserRead),
    prefix="/user",
    tags=["user"],
)
app.include_router(
    fastapi_users_instance.get_users_router(UserRead, UserUpdate,
                                            requires_verification=True),
    prefix="/user",
    tags=["user"],
)


app = VersionedFastAPI(
        app,
        version_format='{major}',
        prefix_format='/v{major}',
        enable_latest=True,
        default_version=(0, 0),
        on_startup=[
            pubsub_startup,
            create_indexes,
            init_api_versions,
            initialize_beanie,
        ]
    )


"""Workaround to use global exception handlers for versioned API.
The issue has already been reported here:
https://github.com/DeanWay/fastapi-versioning/issues/30
"""
for sub_app in app.routes:
    if hasattr(sub_app.app, "add_exception_handler"):
        sub_app.app.add_exception_handler(
            ValueError, value_error_exception_handler
        )
        sub_app.app.add_exception_handler(
            errors.InvalidId, invalid_id_exception_handler
        )


@app.middleware("http")
async def redirect_http_requests(request: Request, call_next):
    """Redirect request with version prefix when no version is provided"""
    path = request.scope['path']
    prefix = path.split('/')[1]
    if prefix not in API_VERSIONS:
        request.scope['path'] = '/latest' + path
    response = await call_next(request)
    return response
