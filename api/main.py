# SPDX-License-Identifier: LGPL-2.1-or-later
#
# Copyright (C) 2021 Collabora Limited
# Author: Guillaume Tucker <guillaume.tucker@collabora.com>

from cloudevents.http import CloudEvent, to_json
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from .auth import Authentication, Token
from .db import Database
from .models import Thing, User
from .pubsub import PubSub

app = FastAPI()
db = Database()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
auth = Authentication(db)
pubsub = PubSub()


async def get_current_user(token: str = Depends(oauth2_scheme)):
    user = auth.get_current_user(token)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


async def get_current_active_user(user: User):
    user = await get_current_user
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
# Things

@app.get('/thing/{thing_id}')
async def thing(thing_id: str):
    return {'thing': await db.find_by_id(Thing, thing_id)}


@app.get('/things')
async def things():
    return {'things': await db.find_all(Thing)}


@app.post('/thing')
async def create_thing(thing: Thing, token: str = Depends(get_current_user)):
    return {'thing': await db.create(thing)}


# -----------------------------------------------------------------------------
# Pub/Sub

@app.post('/subscribe/{channel}')
async def subscribe(channel: str, user: User = Depends(get_user)):
    res = await pubsub.subscribe(user, channel)
    if res is False:
        raise HTTPException(
            status_code=status.HTTP_204_NO_CONTENT,
            detail=f"Already subscribed to channel: {channel}"
        )


@app.post('/unsubscribe/{channel}')
async def unsubscribe(channel: str, user: User = Depends(get_user)):
    res = await pubsub.unsubscribe(user, channel)
    if res is False:
        raise HTTPException(
            status_code=status.HTTP_204_NO_CONTENT,
            detail=f"Already unsubscribed from channel: {channel}"
        )


@app.get('/listen/{channel}')
async def listen(channel: str, user: User = Depends(get_user)):
    msg = await pubsub.listen(user, channel)
    if msg is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Not subscribed to channel: {channel}"
        )
    return msg


@app.post('/publish/{channel}')
async def publish(raw: dict, channel: str, user: User = Depends(get_user)):
    attributes = dict(raw)
    data = attributes.pop('data')
    event = CloudEvent(attributes=attributes, data=data)
    await pubsub.publish(user, channel, to_json(event))
