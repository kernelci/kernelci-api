# SPDX-License-Identifier: LGPL-2.1-or-later
#
# Copyright (C) 2021, 2022 Collabora Limited
# Author: Guillaume Tucker <guillaume.tucker@collabora.com>
# Author: Jeny Sadadia <jeny.sadadia@collabora.com>

# pylint: disable=unused-argument disable=global-statement

"""KernelCI API main module"""

from typing import List, Union
from fastapi import Depends, FastAPI, HTTPException, status, Request, Security
from fastapi.security import (
    OAuth2PasswordRequestForm,
    SecurityScopes
)
from bson import ObjectId, errors
from .auth import Authentication, Token
from .db import Database
from .models import Node, Regression, User, Password, get_model_from_kind
from .pubsub import PubSub, Subscription

app = FastAPI()
db = Database()
auth = Authentication(db, token_url='token',
                      user_scopes={"admin": "Superusers",
                                    "users": "Regular users"})
pubsub = None  # pylint: disable=invalid-name


@app.on_event('startup')
async def pubsub_startup():
    """Startup event handler to create Pub/Sub object"""
    global pubsub  # pylint: disable=invalid-name
    pubsub = await PubSub.create()


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


@app.post('/user/{username}', response_model=User)
async def post_user(
        username: str, password: Password, is_admin: bool = False,
        current_user: User = Security(get_user, scopes=["admin"])):
    """Create new user"""
    try:
        hashed_password = auth.get_password_hash(
                                password.password.get_secret_value())
        obj = await db.create(User(
                                username=username,
                                hashed_password=hashed_password,
                                is_admin=is_admin))
        operation = 'created'
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(error)
        ) from error
    await pubsub.publish_cloudevent('user', {'op': operation,
                                             'id': str(obj.id)})
    return obj


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
        if user.is_admin is not True:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Not allowed to use admin scope"
            )

    access_token = auth.create_access_token(data={
        "sub": user.username,
        "scopes": form_data.scopes}
    )
    return {"access_token": access_token, "token_type": "bearer"}


@app.get('/me', response_model=User)
async def read_users_me(current_user: User = Depends(get_user)):
    """Get user information"""
    return current_user


@app.post('/hash')
def get_password_hash(password: Password):
    """Get a password hash from the provided string password"""
    return auth.get_password_hash(password.password.get_secret_value())


# -----------------------------------------------------------------------------
# Nodes

@app.get('/node/{node_id}', response_model=Union[Regression, Node])
async def get_node(node_id: str, kind: str = "node"):
    """Get node information from the provided node id"""
    try:
        model = get_model_from_kind(kind)
        if model is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid kind: {kind}"
            )
        return await db.find_by_id(model, node_id)
    except errors.InvalidId as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(error)
        ) from error


@app.get('/nodes', response_model=List[Union[Regression, Node]])
async def get_nodes(request: Request, kind: str = "node"):
    """Get all the nodes if no request parameters have passed.
       Get all the matching nodes otherwise."""
    model = get_model_from_kind(kind)
    if model is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid kind: {kind}"
        )

    query_params = dict(request.query_params)
    is_valid, msg = model.validate_params(query_params)
    if not is_valid:
        raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid request parameters: {msg}"
            )
    translated_params = model.translate_fields(query_params)
    return await db.find_by_attributes(model, translated_params)


@app.get('/get_root_node/{node_id}', response_model=Node)
async def get_root_node(node_id: str):
    """Get root node information"""
    while node_id:
        try:
            node = await db.find_by_id(Node, node_id)
        except errors.InvalidId as error:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(error)
            ) from error
        if node is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Node not found with id: {node_id}"
            )
        node_id = node.parent
    return node


@app.post('/node', response_model=Node)
async def post_node(node: Node, token: str = Depends(get_user)):
    """Create a new node"""
    try:
        obj = await db.create(node)
        operation = 'created'
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(error)
        ) from error
    await pubsub.publish_cloudevent('node', {'op': operation,
                                             'id': str(obj.id)})
    return obj


@app.put('/node/{node_id}', response_model=Node)
async def put_node(node_id: str, node: Node, token: str = Depends(get_user)):
    """Update an already added node"""
    try:
        node.id = ObjectId(node_id)
        obj = await db.update(node)
        operation = 'updated'
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(error)
        ) from error
    await pubsub.publish_cloudevent('node', {'op': operation,
                                             'id': str(obj.id)})
    return obj


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
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error)
        ) from error


@app.get('/listen/{sub_id}')
async def listen(sub_id: int, user: User = Depends(get_user)):
    """Listen messages from a subscribed Pub/Sub channel"""
    try:
        return await pubsub.listen(sub_id)
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error)
        ) from error


@app.post('/publish/{channel}')
async def publish(raw: dict, channel: str, user: User = Depends(get_user)):
    """Publish a message on the provided Pub/Sub channel"""
    attributes = dict(raw)
    data = attributes.pop('data')
    await pubsub.publish_cloudevent(channel, data, attributes)


# -----------------------------------------------------------------------------
# Regression

@app.post('/regression')
async def post_regression(regression: Regression,
                          token: str = Depends(get_user)):
    """Create a new regression"""
    try:
        obj = await db.create(regression)
        operation = 'created'
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(error)
        ) from error
    await pubsub.publish_cloudevent('regression', {'op': operation,
                                                   'id': str(obj.id)})
    return obj


@app.put('/regression/{regression_id}', response_model=Regression)
async def put_regression(regression_id: str, regression: Regression,
                         token: str = Depends(get_user)):
    """Update an already added regression"""
    try:
        regression.id = ObjectId(regression_id)
        obj = await db.update(regression)
        operation = 'updated'
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(error)
        ) from error
    await pubsub.publish_cloudevent('regression', {'op': operation,
                                                   'id': str(obj.id)})
    return obj
