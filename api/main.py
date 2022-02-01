# SPDX-License-Identifier: LGPL-2.1-or-later
#
# Copyright (C) 2021 Collabora Limited
# Author: Guillaume Tucker <guillaume.tucker@collabora.com>

from fastapi import Depends, FastAPI, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from .auth import Authentication, Token
from .db import Database
from .models import Node, User
from .pubsub import PubSub, Subscription
from typing import List
from bson import ObjectId

app = FastAPI()
db = Database()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
auth = Authentication(db)
pubsub = None


@app.on_event('startup')
async def pubsub_startup():
    global pubsub
    pubsub = await PubSub.create()


async def get_current_user(token: str = Depends(oauth2_scheme)):
    if token == 'None':
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user = await auth.get_current_user(token)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


async def get_user(user: User = Depends(get_current_user)):
    if not user.active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return user


@app.get('/')
async def root():
    return {"message": "KernelCI API"}


@app.post('/token', response_model=Token)
async def login_for_access_token(
        form_data: OAuth2PasswordRequestForm = Depends()):
    user = await auth.authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = auth.create_access_token(data={"sub": user.username})
    return {"access_token": access_token, "token_type": "bearer"}


@app.get('/me', response_model=User)
async def read_users_me(current_user: User = Depends(get_user)):
    return current_user


@app.get('/hash/{password}')
def get_password_hash(password):
    return auth.get_password_hash(password)


# -----------------------------------------------------------------------------
# Nodes

@app.get('/node/{node_id}', response_model=Node)
async def get_node(node_id: str):
    return await db.find_by_id(Node, node_id)


@app.get('/nodes', response_model=List[Node])
async def get_nodes(request: Request):
    return await db.find_by_attributes(Node, dict(request.query_params))


@app.post('/node', response_model=Node)
async def post_node(node: Node, token: str = Depends(get_user)):
    try:
        obj = await db.create(node)
        op = 'created'
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    await pubsub.publish_cloudevent('node', {'op': op, 'id': str(obj.id)})
    return obj


@app.put('/node/{node_id}', response_model=Node)
async def put_node(node_id: str, node: Node, token: str = Depends(get_user)):
    try:
        node.id = ObjectId(node_id)
        obj = await db.update(Node, node)
        op = 'updated'
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    await pubsub.publish_cloudevent('node', {'op': op, 'id': str(obj.id)})
    return obj


# -----------------------------------------------------------------------------
# Pub/Sub

@app.post('/subscribe/{channel}', response_model=Subscription)
async def subscribe(channel: str, user: User = Depends(get_user)):
    return await pubsub.subscribe(channel)


@app.post('/unsubscribe/{sub_id}')
async def unsubscribe(sub_id: int, user: User = Depends(get_user)):
    res = await pubsub.unsubscribe(sub_id)
    if res is False:
        raise HTTPException(
            status_code=status.HTTP_204_NO_CONTENT,
            detail=f"Already unsubscribed: {sub_id}"
        )


@app.get('/listen/{sub_id}')
async def listen(sub_id: int, user: User = Depends(get_user)):
    msg = await pubsub.listen(sub_id)
    if msg is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Not subscribed to channel with id: {sub_id}"
        )
    return msg


@app.post('/publish/{channel}')
async def publish(raw: dict, channel: str, user: User = Depends(get_user)):
    attributes = dict(raw)
    data = attributes.pop('data')
    await pubsub.publish_cloudevent(channel, data, attributes)
