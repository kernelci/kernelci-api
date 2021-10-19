# SPDX-License-Identifier: LGPL-2.1-or-later
#
# Copyright (C) 2021 Collabora Limited
# Author: Guillaume Tucker <guillaume.tucker@collabora.com>

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from .auth import Authentication, Token
from .db import Database
from .models import Thing, User

app = FastAPI()
db = Database()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
auth = Authentication(db)


async def get_current_user(token: str = Depends(oauth2_scheme)):
    user = auth.get_current_user(token)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


async def get_current_active_user(user: User = Depends(get_current_user)):
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
async def read_users_me(current_user: User = Depends(get_current_active_user)):
    return current_user


@app.get('/hash/{password}')
def get_password_hash(password):
    return auth.get_password_hash(password)


@app.get('/thing/{thing_id}')
def thing(thing_id: str):
    return {'thing': db.find_by_id(Thing, thing_id)}


@app.get('/things')
def things():
    return {'things': db.find_all(Thing)}


@app.post('/thing')
def create_thing(thing: Thing, token: str = Depends(get_current_user)):
    return {'thing': db.create(thing)}
