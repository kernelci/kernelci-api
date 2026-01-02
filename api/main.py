# SPDX-License-Identifier: LGPL-2.1-or-later
#
# Copyright (C) 2021-2025 Collabora Limited
# Author: Guillaume Tucker <guillaume.tucker@collabora.com>
# Author: Jeny Sadadia <jeny.sadadia@collabora.com>
# Author: Denys Fedoryshchenko <denys.f@collabora.com>

# pylint: disable=unused-argument,global-statement,too-many-lines

"""KernelCI API main module"""

import os
import re
import asyncio
import traceback
import secrets
import ipaddress
from typing import List, Union, Optional
from datetime import datetime, timedelta, timezone
from contextlib import asynccontextmanager
from fastapi import (
    Depends,
    FastAPI,
    HTTPException,
    status,
    Request,
    Form,
    Header,
    Query,
    Body,
)
from fastapi.encoders import jsonable_encoder
from fastapi.responses import (
    JSONResponse,
    PlainTextResponse,
    FileResponse,
    HTMLResponse
)
from fastapi.security import OAuth2PasswordRequestForm
from fastapi_pagination import add_pagination
from fastapi_versioning import VersionedFastAPI
from bson import ObjectId, errors
from fastapi_users import FastAPIUsers
from beanie import PydanticObjectId
from pydantic import BaseModel
from jose import jwt
from jose.exceptions import JWTError
from kernelci.api.models import (
    Node,
    Hierarchy,
    PublishEvent,
    parse_node_obj,
    KernelVersion,
    EventHistory,
)
from .auth import Authentication
from .db import Database
from .pubsub_mongo import PubSub
from .user_manager import get_user_manager, create_user_manager
from .models import (
    PageModel,
    Subscription,
    SubscriptionStats,
    User,
    UserRead,
    UserCreate,
    UserCreateRequest,
    UserInviteRequest,
    UserInviteResponse,
    UserUpdate,
    UserUpdateRequest,
    UserGroup,
    InviteAcceptRequest,
    InviteUrlResponse,
)
from .metrics import Metrics
from .maintenance import purge_old_nodes
from .config import AuthSettings

SUBSCRIPTION_CLEANUP_INTERVAL_MINUTES = 15  # How often to run cleanup task
SUBSCRIPTION_MAX_AGE_MINUTES = 15           # Max age before stale
SUBSCRIPTION_CLEANUP_RETRY_MINUTES = 1      # Retry interval if cleanup fails


@asynccontextmanager
async def lifespan(app: FastAPI):  # pylint: disable=redefined-outer-name
    """Lifespan functions for startup and shutdown events"""
    await pubsub_startup()
    await create_indexes()
    await initialize_beanie()
    await ensure_legacy_node_editors()
    yield

# List of all the supported API versions.  This is a placeholder until the API
# actually supports multiple versions with different sets of endpoints and
# models etc.
API_VERSIONS = ['v0']

metrics = Metrics()
app = FastAPI(lifespan=lifespan, debug=True, docs_url=None, redoc_url=None)
db = Database(service=(os.getenv('MONGO_SERVICE') or 'mongodb://db:27017'))
auth = Authentication(token_url="user/login")
pubsub = None  # pylint: disable=invalid-name

auth_backend = auth.get_user_authentication_backend()
fastapi_users_instance = FastAPIUsers[User, PydanticObjectId](
    get_user_manager,
    [auth_backend],
)
user_manager = create_user_manager()


async def pubsub_startup():
    """Startup event handler to create Pub/Sub object"""
    global pubsub  # pylint: disable=invalid-name
    pubsub = await PubSub.create()


async def subscription_cleanup_task():
    """Background task to cleanup stale subscriptions"""
    while True:
        try:
            await asyncio.sleep(SUBSCRIPTION_CLEANUP_INTERVAL_MINUTES * 60)
            cleaned = await pubsub.cleanup_stale_subscriptions(
                SUBSCRIPTION_MAX_AGE_MINUTES)
            if cleaned > 0:
                metrics.add('subscriptions_cleaned', 1)
                print(f"Cleaned up {cleaned} stale subscriptions")
        except (ConnectionError, OSError, RuntimeError) as e:
            print(f"Subscription cleanup error: {e}")
            await asyncio.sleep(SUBSCRIPTION_CLEANUP_RETRY_MINUTES * 60)


async def start_background_tasks():
    """Start background cleanup tasks"""
    asyncio.create_task(subscription_cleanup_task())


async def create_indexes():
    """Startup event handler to create database indexes"""
    await db.create_indexes()


async def initialize_beanie():
    """Startup event handler to initialize Beanie"""
    await db.initialize_beanie()


async def ensure_legacy_node_editors():
    """Grant legacy node edit privileges to specific users."""
    legacy_usernames = {'staging.kernelci.org', 'production'}
    group_name = 'node:edit:any'
    group = await db.find_one(UserGroup, name=group_name)
    if not group:
        group = await db.create(UserGroup(name=group_name))
    for username in legacy_usernames:
        user = await db.find_one(User, username=username)
        if not user:
            continue
        if any(existing.name == group_name for existing in user.groups):
            continue
        user.groups.append(group)
        await db.update(user)


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


@app.get('/')
async def root():
    """Root endpoint handler"""
    metrics.add('http_requests_total', 1)
    root_dir = os.path.dirname(os.path.abspath(__file__))
    index_path = os.path.join(root_dir, 'templates', 'index.html')
    with open(index_path, 'r', encoding='utf-8') as file:
        return HTMLResponse(file.read())

# -----------------------------------------------------------------------------
# Users


def get_current_user(user: User = Depends(
        fastapi_users_instance.current_user(active=True))):
    """Get current active user"""
    return user


def get_current_superuser(user: User = Depends(
        fastapi_users_instance.current_user(active=True, superuser=True))):
    """Get current active superuser"""
    return user


async def _resolve_user_groups(group_names: List[str]) -> List[UserGroup]:
    groups: List[UserGroup] = []
    for group_name in group_names:
        group = await db.find_one(UserGroup, name=group_name)
        if not group:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"User group does not exist with name: {group_name}",
            )
        groups.append(group)
    return groups


def _create_invite_token(user: User) -> str:
    settings = AuthSettings()
    now = datetime.now(timezone.utc)
    exp = now + timedelta(seconds=settings.invite_token_expire_seconds)
    payload = {
        "sub": str(user.id),
        "email": user.email,
        "purpose": "invite",
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp()),
    }
    return jwt.encode(
        payload,
        settings.secret_key,
        algorithm=settings.algorithm,
    )


def _decode_invite_token(token: str) -> dict:
    settings = AuthSettings()
    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.algorithm],
        )
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired invite token",
        ) from exc
    if payload.get("purpose") != "invite":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid invite token",
        )
    return payload


def _resolve_public_base_url(request: Request) -> str:
    settings = AuthSettings()
    if settings.public_base_url:
        return settings.public_base_url.rstrip("/")

    def _is_proxy_addr() -> bool:
        client = request.client
        if not client or not client.host:
            return False
        try:
            ip_addr = ipaddress.ip_address(client.host)
        except ValueError:
            return False
        return not ip_addr.is_global

    forwarded_host = None
    forwarded_proto = None
    forwarded_header = request.headers.get("forwarded")
    if forwarded_header and _is_proxy_addr():
        first_hop = forwarded_header.split(",", 1)[0]
        for pair in first_hop.split(";"):
            if "=" not in pair:
                continue
            key, value = pair.split("=", 1)
            key = key.strip().lower()
            value = value.strip().strip('"')
            if key == "host":
                forwarded_host = value
            elif key == "proto":
                forwarded_proto = value

    if _is_proxy_addr():
        forwarded_host = forwarded_host or request.headers.get(
            "x-forwarded-host"
        )
        forwarded_proto = forwarded_proto or request.headers.get(
            "x-forwarded-proto"
        )

    if forwarded_host:
        scheme = forwarded_proto or request.url.scheme
        return f"{scheme}://{forwarded_host}".rstrip("/")

    return str(request.base_url).rstrip("/")


def _accept_invite_url(public_base_url: str) -> str:
    return f"{public_base_url}/user/accept-invite"


async def _find_existing_user_for_invite(
        invite: UserInviteRequest,
) -> User | None:
    existing_by_username = await db.find_one(User, username=invite.username)
    if existing_by_username:
        return existing_by_username
    return await db.find_one(User, email=invite.email)


def _validate_invite_resend(existing_user: User, invite: UserInviteRequest):
    if not invite.resend_if_exists:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User already exists",
        )
    if existing_user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User already verified",
        )
    if existing_user.username != invite.username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Existing user has a different username",
        )
    if existing_user.email != invite.email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Existing user has a different email",
        )


async def _create_user_for_invite(
        request: Request,
        invite: UserInviteRequest,
) -> User:
    groups: List[UserGroup] = []
    if invite.groups:
        groups = await _resolve_user_groups(invite.groups)

    random_password = secrets.token_urlsafe(32)
    user_create = UserCreate(
        username=invite.username,
        email=invite.email,
        password=random_password,
        is_superuser=invite.is_superuser,
    )
    user_create.groups = groups

    created_user = await register_router.routes[0].endpoint(
        request, user_create, user_manager)

    if invite.is_superuser:
        user_from_id = await db.find_by_id(User, created_user.id)
        user_from_id.is_superuser = True
        created_user = await db.update(user_from_id)

    return created_user


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
async def register(request: Request, user: UserCreateRequest,
                   current_user: User = Depends(get_current_superuser)):
    """User registration route

    Custom user registration router to ensure unique username.
    `user` from request has a list of user group name strings.
    This handler will convert them to `UserGroup` objects and
    insert user object to database.
    """
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="User registration is disabled; use /user/invite instead.",
    )


@app.get("/user/invite", response_class=HTMLResponse, include_in_schema=False)
async def invite_user_page():
    """Web UI for inviting a user (admin token required)"""
    metrics.add('http_requests_total', 1)
    root_dir = os.path.dirname(os.path.abspath(__file__))
    page_path = os.path.join(root_dir, 'templates', 'invite.html')
    with open(page_path, 'r', encoding='utf-8') as file:
        return HTMLResponse(file.read())


@app.post("/user/invite", response_model=UserInviteResponse, tags=["user"],
          response_model_by_alias=False)
async def invite_user(request: Request, invite: UserInviteRequest,
                      current_user: User = Depends(get_current_superuser)):
    """Invite a user (admin-only)

    Creates the user with a random password and sends a single invite link
    to set a password and verify the account.
    """
    metrics.add('http_requests_total', 1)
    existing_user = await _find_existing_user_for_invite(invite)
    if existing_user:
        _validate_invite_resend(existing_user, invite)
        created_user = existing_user
    else:
        created_user = await _create_user_for_invite(request, invite)

    public_base_url = _resolve_public_base_url(request)
    accept_invite_url = _accept_invite_url(public_base_url)
    token = _create_invite_token(created_user)
    invite_url = f"{accept_invite_url}?token={token}"

    email_sent = False
    if invite.send_email:
        try:
            await user_manager.send_invite_email(
                created_user,
                token,
                invite_url,
            )
            email_sent = True
        except Exception as exc:  # pylint: disable=broad-exception-caught
            print(f"Failed to send invite email: {exc}")

    return UserInviteResponse(
        user=created_user,
        email_sent=email_sent,
        public_base_url=public_base_url,
        accept_invite_url=accept_invite_url,
        invite_url=invite_url if invite.return_token else None,
        token=token if invite.return_token else None,
    )


@app.get(
    "/user/accept-invite",
    response_class=HTMLResponse,
    include_in_schema=False,
)
async def accept_invite_page():
    """Web UI for accepting an invite (sets password + verifies)"""
    metrics.add('http_requests_total', 1)
    root_dir = os.path.dirname(os.path.abspath(__file__))
    page_path = os.path.join(root_dir, 'templates', 'accept-invite.html')
    with open(page_path, 'r', encoding='utf-8') as file:
        return HTMLResponse(file.read())


@app.get("/user/invite/url", response_model=InviteUrlResponse, tags=["user"])
async def invite_url_preview(request: Request,
                             current_user: User = Depends(
                                 get_current_superuser)):
    """Preview the resolved public URL used in invite links (admin-only)"""
    metrics.add('http_requests_total', 1)
    public_base_url = _resolve_public_base_url(request)
    return InviteUrlResponse(
        public_base_url=public_base_url,
        accept_invite_url=_accept_invite_url(public_base_url),
    )


@app.post("/user/accept-invite", response_model=UserRead, tags=["user"],
          response_model_by_alias=False)
async def accept_invite(accept: InviteAcceptRequest):
    """Accept an invite token, set password, and verify the user"""
    metrics.add('http_requests_total', 1)
    payload = _decode_invite_token(accept.token)
    user_id = payload.get("sub")
    email = payload.get("email")

    user_from_id = await db.find_by_id(User, user_id)
    if not user_from_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    if not user_from_id.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is inactive",
        )
    if user_from_id.email != email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid invite token",
        )
    if user_from_id.is_verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invite already accepted",
        )

    user_from_id.hashed_password = user_manager.password_helper.hash(
        accept.password
    )
    user_from_id.is_verified = True
    updated_user = await db.update(user_from_id)

    try:
        await user_manager.send_invite_accepted_email(updated_user)
    except Exception as exc:  # pylint: disable=broad-exception-caught
        print(f"Failed to send invite accepted email: {exc}")
    return updated_user


app.include_router(
    fastapi_users_instance.get_reset_password_router(),
    prefix="/user",
    tags=["user"],
)

users_router = fastapi_users_instance.get_users_router(
    UserRead, UserUpdate, requires_verification=True)

app.add_api_route(
    path="/whoami",
    tags=["user"],
    methods=["GET"],
    description="Get current user information",
    endpoint=users_router.routes[0].endpoint)
app.add_api_route(
    path="/user/{id}",
    tags=["user"],
    methods=["GET"],
    description="Get user information by ID",
    dependencies=[Depends(get_current_user)],
    endpoint=users_router.routes[2].endpoint)
app.add_api_route(
    path="/user/{id}",
    tags=["user"],
    methods=["DELETE"],
    description="Delete user by ID",
    dependencies=[Depends(get_current_superuser)],
    endpoint=users_router.routes[4].endpoint)


@app.patch("/user/me", response_model=UserRead, tags=["user"],
           response_model_by_alias=False)
async def update_me(request: Request, user: UserUpdateRequest,
                    current_user: User = Depends(get_current_user)):
    """User update route

    Custom user update router handler will only allow users to update
    its own profile.
    """
    metrics.add('http_requests_total', 1)
    if user.groups:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User groups can only be updated by an admin user",
        )
    if user.username and user.username != current_user.username:
        existing_user = await db.find_one(User, username=user.username)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Username already exists: {user.username}",
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
    user_update = UserUpdate(**(user.model_dump(
         exclude={'groups', 'is_superuser'}, exclude_none=True)))
    if groups:
        user_update.groups = groups
    return await users_router.routes[1].endpoint(
        request, user_update, current_user, user_manager)


@app.patch("/user/{user_id}", response_model=UserRead, tags=["user"],
           response_model_by_alias=False)
async def update_user(user_id: str, request: Request, user: UserUpdateRequest,
                      current_user: User = Depends(get_current_superuser)):
    """Router to allow admin users to update other user account"""
    metrics.add('http_requests_total', 1)
    user_from_id = await db.find_by_id(User, user_id)
    if not user_from_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User not found with id: {user_id}",
        )

    if user.username and user.username != user_from_id.username:
        existing_user = await db.find_one(User, username=user.username)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Username already exists: {user.username}",
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
    user_update = UserUpdate(**(user.model_dump(
         exclude={'groups'}, exclude_none=True)))

    if groups:
        user_update.groups = groups

    updated_user = await users_router.routes[3].endpoint(
        user_update, request, user_from_id, user_manager
    )
    # Update superuser explicitly since fastapi-users update route ignores it.
    if user.is_superuser is not None:
        user_from_id = await db.find_by_id(User, updated_user.id)
        user_from_id.is_superuser = user.is_superuser
        updated_user = await db.update(user_from_id)
    return updated_user


def _get_node_runtime(node: Node) -> Optional[str]:
    """Best-effort runtime lookup from node data."""
    data = getattr(node, 'data', None)
    if isinstance(data, dict):
        return data.get('runtime')
    return getattr(data, 'runtime', None)


def _user_can_edit_node(user: User, node: Node) -> bool:
    """Return True when user can update the given node."""
    if user.is_superuser:
        return True
    if user.username == node.owner:
        return True
    user_group_names = {group.name for group in user.groups}
    if 'node:edit:any' in user_group_names:
        return True
    if any(group_name in user_group_names
           for group_name in getattr(node, 'user_groups', [])):
        return True
    runtime = _get_node_runtime(node)
    if runtime:
        runtime_editor = f'runtime:{runtime}:node-editor'
        runtime_admin = f'runtime:{runtime}:node-admin'
        if (runtime_editor in user_group_names
                or runtime_admin in user_group_names):
            return True
    return False


async def authorize_user(node_id: str,
                         user: User = Depends(get_current_user)):
    """Return the user if active, authenticated, and authorized"""

    # Only the user that created the node or any other user from the permitted
    # user groups will be allowed to update the node
    node_from_id = await db.find_by_id(Node, node_id)
    if not node_from_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Node not found with id: {node_id}"
        )
    if not _user_can_edit_node(user, node_from_id):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized to complete the operation"
        )
    return user


@app.get('/users', response_model=PageModel, tags=["user"],
         response_model_exclude={"items": {"__all__": {
                                    "hashed_password"}}})
async def get_users(request: Request,
                    current_user: User = Depends(get_current_user)):
    """Get all the users if no request parameters have passed.
       Get the matching users otherwise."""
    metrics.add('http_requests_total', 1)
    query_params = dict(request.query_params)
    # Drop pagination parameters from query as they're already in arguments
    for pg_key in ['limit', 'offset']:
        query_params.pop(pg_key, None)
    paginated_resp = await db.find_by_attributes(User, query_params)
    paginated_resp.items = serialize_paginated_data(
        User, paginated_resp.items)
    return paginated_resp


@app.post("/user/update-password", tags=["user"])
async def update_password(request: Request,
                          credentials: OAuth2PasswordRequestForm = Depends(),
                          new_password: str = Form(None)):
    """Update user password"""
    metrics.add('http_requests_total', 1)
    user = await user_manager.authenticate(credentials)
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="LOGIN_BAD_CREDENTIALS",
        )
    user_update = UserUpdate(password=new_password)
    user_from_username = await db.find_one(User, username=credentials.username)
    await users_router.routes[3].endpoint(
        user_update, request, user_from_username, user_manager
    )


# EventHistory is now stored by pubsub.publish_cloudevent()
# No need for separate _get_eventhistory function


def _parse_event_id_filter(query_params: dict, event_id: str,
                           event_ids: str) -> None:
    """Parse and validate event id/ids filter parameters.

    Modifies query_params in place to add _id filter.
    Raises HTTPException on validation errors.
    """
    if event_id and event_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provide either id or ids, not both"
        )
    if event_id:
        try:
            query_params['_id'] = ObjectId(event_id)
        except (errors.InvalidId, TypeError) as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid id format"
            ) from exc
    elif event_ids:
        try:
            ids_list = [ObjectId(x.strip())
                        for x in event_ids.split(',') if x.strip()]
        except (errors.InvalidId, TypeError) as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid ids format"
            ) from exc
        if not ids_list:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="ids must contain at least one id"
            )
        query_params['_id'] = {'$in': ids_list}


def _build_events_query(query_params: dict) -> tuple:
    """Extract and process event query parameters.

    Returns (recursive, processed_query_params).
    Raises HTTPException on validation errors.
    """
    recursive = query_params.pop('recursive', None)
    limit = query_params.pop('limit', None)
    kind = query_params.pop('kind', None)
    state = query_params.pop('state', None)
    result = query_params.pop('result', None)
    from_ts = query_params.pop('from', None)
    node_id = query_params.pop('node_id', None)
    event_id = query_params.pop('id', None)
    event_ids = query_params.pop('ids', None)

    if node_id:
        if 'data.id' in query_params:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Provide either node_id or data.id, not both"
            )
        query_params['data.id'] = node_id

    _parse_event_id_filter(query_params, event_id, event_ids)

    if from_ts:
        if isinstance(from_ts, str):
            from_ts = datetime.fromisoformat(from_ts)
        query_params['timestamp'] = {'$gt': from_ts}
    if kind:
        query_params['data.kind'] = kind
    if state:
        query_params['data.state'] = state
    if result:
        query_params['data.result'] = result
    if limit:
        query_params['limit'] = int(limit)

    if recursive and (not limit or int(limit) > 1000):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Recursive limit is too large, max is 1000"
        )

    return recursive, query_params


# TBD: Restrict response by Pydantic model
@app.get('/events')
async def get_events(request: Request):
    """Get all the events if no request parameters have passed.
       Format: [{event1}, {event2}, ...] or if recursive is set to true,
       then we add to each event the node information.
       Get all the matching events otherwise.
       Query parameters can be used to filter the events:
       - limit: Number of events to return
       - from: Start timestamp (unix epoch) to filter events
       - kind: Event kind to filter events
       - state: Event state to filter events
       - result: Event result to filter events
       - id / ids: Event document id(s) to filter events
       - node_id: Node id to filter events (alias for data.id)
       - recursive: Retrieve node together with event
    This API endpoint is under development and may change in future.
    """
    metrics.add('http_requests_total', 1)
    query_params = dict(request.query_params)
    recursive, query_params = _build_events_query(query_params)

    resp = await db.find_by_attributes_nonpaginated(EventHistory, query_params)
    resp_list = []
    for item in resp:
        item['id'] = str(item['_id'])
        item.pop('_id')
        if recursive:
            node = await db.find_by_id(Node, item['data']['id'])
            if node:
                item['node'] = node
        resp_list.append(item)
    json_comp = jsonable_encoder(resp_list)
    return JSONResponse(content=json_comp)


# -----------------------------------------------------------------------------
# Nodes
def _get_node_event_data(operation, node, is_hierarchy=False):
    return {
        'op': operation,
        'id': str(node.id),
        'kind': node.kind,
        'name': node.name,
        'path': node.path,
        'group': node.group,
        'state': node.state,
        'result': node.result,
        'owner': node.owner,
        'data': node.data,
        'is_hierarchy': is_hierarchy,
    }


async def translate_null_query_params(query_params: dict):
    """Translate null query parameters to None"""
    translated = query_params.copy()
    for key, value in query_params.items():
        if value == 'null':
            translated[key] = None
    return translated


@app.get('/node/{node_id}', response_model=Union[Node, None],
         response_model_by_alias=False)
async def get_node(node_id: str):
    """Get node information from the provided node id"""
    metrics.add('http_requests_total', 1)
    try:
        return await db.find_by_id(Node, node_id)
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
        serialized_data.append(model(**obj).model_dump(mode='json'))
    return serialized_data


@app.get('/nodes', response_model=PageModel)
async def get_nodes(request: Request):
    """Get all the nodes if no request parameters have passed.
       Get all the matching nodes otherwise, within the pagination limit."""
    metrics.add('http_requests_total', 1)
    query_params = dict(request.query_params)

    # Drop pagination parameters from query as they're already in arguments
    for pg_key in ['limit', 'offset']:
        query_params.pop(pg_key, None)

    query_params = await translate_null_query_params(query_params)

    try:
        # Query using the base Node model, regardless of the specific
        # node type
        model = Node
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


async def db_find_node_nonpaginated(query_params):
    """Find all the matching nodes without pagination"""
    model = Node
    translated_params = model.translate_fields(query_params)
    return await db.find_by_attributes_nonpaginated(model, translated_params)


@app.get('/nodes/fast', response_model=List[Node])
async def get_nodes_fast(request: Request):
    """Get all the nodes if no request parameters have passed.
    This is non-paginated version of get_nodes.
    Still options limit=NNN and offset=NNN works and forwarded
    as limit and skip to the MongoDB.
    """
    query_params = dict(request.query_params)

    query_params = await translate_null_query_params(query_params)

    try:
        # Query using the base Node model, regardless of the specific
        # node type, use asyncio.wait_for with timeout 30 seconds
        resp = await asyncio.wait_for(
            db_find_node_nonpaginated(query_params),
            timeout=15
        )
        return resp
    except asyncio.TimeoutError as error:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail=f"Timeout while fetching nodes: {str(error)}"
        ) from error
    except KeyError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Node not found with the kind: {str(error)}"
        ) from error


@app.get('/count', response_model=int)
async def get_nodes_count(request: Request):
    """Get the count of all the nodes if no request parameters have passed.
       Get the count of all the matching nodes otherwise."""
    metrics.add('http_requests_total', 1)
    query_params = dict(request.query_params)

    query_params = await translate_null_query_params(query_params)

    try:
        # Query using the base Node model, regardless of the specific
        # node type
        model = Node
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


def _translate_version_fields(node: Node):
    """Translate Node version fields"""
    data = node.data
    if data:
        version = data.get('kernel_revision', {}).get('version')
        if version:
            version = KernelVersion.translate_version_fields(version)
            node.data['kernel_revision']['version'] = version
    return node


@app.post('/node', response_model=Node, response_model_by_alias=False)
async def post_node(node: Node,
                    authorization: str | None = Header(default=None),
                    current_user: User = Depends(get_current_user)):
    """Create a new node"""
    metrics.add('http_requests_total', 1)
    # [TODO] Remove translation below once we can use it in the pipeline
    node = _translate_version_fields(node)

    # Explicit pydantic model validation
    parse_node_obj(node)

    # [TODO] Implement sanity checks depending on the node kind
    if node.parent:
        parent = await db.find_by_id(Node, node.parent)
        if not parent:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Parent not found with id: {node.parent}"
            )

    await _verify_user_group_existence(node.user_groups)
    node.owner = current_user.username

    # The node is handled as a generic Node by the DB, regardless of its
    # specific kind. The concrete Node submodel (Kbuild, Checkout, etc.)
    # is only used for data format validation
    obj = await db.create(node)
    data = _get_node_event_data('created', obj)
    attributes = {}
    if data.get('owner', None):
        attributes['owner'] = data['owner']
    # publish_cloudevent now stores to eventhistory collection
    await pubsub.publish_cloudevent('node', data, attributes)
    return obj


def is_same_flags(old_node, new_node):
    """ Compare processed_by_kcidb_bridge flags
    Returns True if flags are same, False otherwise
    """
    old_flag = old_node.processed_by_kcidb_bridge
    new_flag = new_node.processed_by_kcidb_bridge
    if old_flag == new_flag:
        return True
    return False


@app.put('/node/{node_id}', response_model=Node, response_model_by_alias=False)
async def put_node(node_id: str, node: Node,
                   user: str = Depends(authorize_user),
                   noevent: Optional[bool] = Query(None)):
    """Update an already added node"""
    metrics.add('http_requests_total', 1)
    node.id = ObjectId(node_id)
    node_from_id = await db.find_by_id(Node, node_id)
    if not node_from_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Node not found with id: {node.id}"
        )

    # [TODO] Remove translation below once we can use it in the pipeline
    node = _translate_version_fields(node)

    # Sanity checks
    # Note: do not update node ownership fields, don't update 'state'
    # until we've checked the state transition is valid.
    update_data = node.model_dump(
        exclude={'owner', 'submitter', 'user_groups', 'state'})
    new_node_def = node_from_id.model_copy(update=update_data)
    # 1- Parse and validate node to specific subtype
    specialized_node = parse_node_obj(new_node_def)

    # 2 - State transition checks
    is_valid, message = specialized_node.validate_node_state_transition(
        node.state)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message
        )
    # if state changes, reset processed_by_kcidb_bridge flag
    if node.state != new_node_def.state:
        new_node_def.processed_by_kcidb_bridge = False
    # Now we can update the state
    new_node_def.state = node.state

    # KCIDB flags are reset on any update, because this means we need
    # to reprocess updated node.
    # So reset flag, unless flag is changed in the request
    if is_same_flags(node_from_id, node):
        new_node_def.processed_by_kcidb_bridge = False

    # Update node in the DB
    obj = await db.update(new_node_def)
    data = _get_node_event_data('updated', obj)
    attributes = {}
    if data.get('owner', None):
        attributes['owner'] = data['owner']
    if not noevent:
        # publish_cloudevent now stores to eventhistory collection
        await pubsub.publish_cloudevent('node', data, attributes)
    return obj


class NodeUpdateRequest(BaseModel):
    """Request model for updating multiple nodes"""
    nodes: List[str]
    field: str
    value: str


@app.put('/batch/nodeset', response_model=int)
async def put_batch_nodeset(data: NodeUpdateRequest,
                            user: str = Depends(get_current_user)):
    """
    Set a field to a value for multiple nodes
    TBD: Make db.bulkupdate to update multiple nodes in one go
    """
    metrics.add('http_requests_total', 1)
    updated = 0
    nodes = data.nodes
    field = data.field
    value = data.value
    for node_id in nodes:
        node_from_id = await db.find_by_id(Node, node_id)
        if not node_from_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Node not found with id: {node_id}"
            )
        # Verify authorization, and ignore if not permitted.
        if not _user_can_edit_node(user, node_from_id):
            continue
        # right now we support only field:
        # processed_by_kcidb_bridge, also value should be boolean
        if field == 'processed_by_kcidb_bridge':
            if value in ['true', 'True']:
                value = True
            elif value in ['false', 'False']:
                value = False
            setattr(node_from_id, field, value)
            await db.update(node_from_id)
            updated += 1
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Field not supported"
            )
    return updated


async def _set_node_ownership_recursively(user: User, hierarchy: Hierarchy,
                                          submitter: str, treeid: str):
    """Set node ownership information for a hierarchy of nodes"""
    if not hierarchy.node.owner:
        hierarchy.node.owner = user.username
    hierarchy.node.submitter = submitter
    hierarchy.node.treeid = treeid
    for node in hierarchy.child_nodes:
        await _set_node_ownership_recursively(user, node, submitter, treeid)


@app.put('/nodes/{node_id}', response_model=List[Node],
         response_model_by_alias=False)
async def put_nodes(
        node_id: str, nodes: Hierarchy,
        authorization: str | None = Header(default=None),
        user: str = Depends(authorize_user)):
    """Add a hierarchy of nodes to an existing root node"""
    metrics.add('http_requests_total', 1)
    nodes.node.id = ObjectId(node_id)
    # Retrieve the root node from the DB and submitter
    node_from_id = await db.find_by_id(Node, node_id)
    if not node_from_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Node not found with id: {node_id}"
        )
    submitter = node_from_id.submitter
    treeid = node_from_id.treeid

    await _set_node_ownership_recursively(user, nodes, submitter, treeid)
    obj_list = await db.create_hierarchy(nodes, Node)
    data = _get_node_event_data('updated', obj_list[0], True)
    attributes = {}
    if data.get('owner', None):
        attributes['owner'] = data['owner']
    # publish_cloudevent now stores to eventhistory collection
    await pubsub.publish_cloudevent('node', data, attributes)
    return obj_list


# -----------------------------------------------------------------------------
# Key/Value namespace enabled store
@app.get('/kv/{namespace}/{key}', response_model=Union[str, None])
async def get_kv(namespace: str, key: str,
                 user: User = Depends(get_current_user)):

    """Get a key value pair from the store"""
    metrics.add('http_requests_total', 1)
    return await db.get_kv(namespace, key)


@app.post('/kv/{namespace}/{key}', response_model=Optional[str])
async def post_kv(namespace: str, key: str,
                  value: Optional[str] = Body(default=None),
                  user: User = Depends(get_current_user)):
    """Set a key-value pair in the store
    namespace and key are part of the URL
    value is part of the request body.
    If value is not provided, we need to call delete_kv to remove the key.
    """
    metrics.add('http_requests_total', 1)
    if not value:
        await db.del_kv(namespace, key)
        return "OK"
    ret = await db.set_kv(namespace, key, value)
    if ret:
        return "OK"
    raise HTTPException(status_code=500, detail="Failed to set key-value pair")


# Delete a key-value pair from the store
@app.delete('/kv/{namespace}/{key}', response_model=Optional[str])
async def delete_kv(namespace: str, key: str,
                    user: User = Depends(get_current_user)):
    """Delete a key-value pair from the store"""
    metrics.add('http_requests_total', 1)
    await db.del_kv(namespace, key)
    response = "Key-value pair deleted successfully"
    return response


# -----------------------------------------------------------------------------
# Pub/Sub

@app.post('/subscribe/{channel}', response_model=Subscription)
async def subscribe(channel: str, user: User = Depends(get_current_user),
                    promisc: Optional[bool] = Query(None),
                    subscriber_id: Optional[str] = Query(
                        None,
                        description="Unique subscriber ID for durable "
                                    "delivery. If provided, missed events "
                                    "will be delivered on reconnection. "
                                    "Without this, events are "
                                    "fire-and-forget."
                    )):
    """Subscribe handler for Pub/Sub channel

    Args:
        channel: Channel name to subscribe to
        promisc: If true, receive all messages regardless of owner
        subscriber_id: Optional unique ID for durable event delivery.
            When provided, the subscriber's position is tracked and
            missed events are delivered on reconnection. Use a stable
            identifier like "scheduler-prod-1" or "dashboard-main".
            Without subscriber_id, standard fire-and-forget pub/sub.
    """
    metrics.add('http_requests_total', 1)
    options = {}
    if promisc:
        options['promiscuous'] = promisc
    if subscriber_id:
        options['subscriber_id'] = subscriber_id
    return await pubsub.subscribe(channel, user.username, options)


@app.post('/unsubscribe/{sub_id}')
async def unsubscribe(sub_id: int, user: User = Depends(get_current_user)):
    """Unsubscribe handler for Pub/Sub channel"""
    metrics.add('http_requests_total', 1)
    try:
        await pubsub.unsubscribe(sub_id, user.username)
    except KeyError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Subscription id not found: {str(error)}"
        ) from error
    except RuntimeError as error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(error)
        ) from error


@app.get('/listen/{sub_id}')
async def listen(sub_id: int, user: User = Depends(get_current_user)):
    """Listen messages from a subscribed Pub/Sub channel"""
    metrics.add('http_requests_total', 1)
    try:
        return await pubsub.listen(sub_id, user.username)
    except KeyError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Subscription id not found: {str(error)}"
        ) from error
    except RuntimeError as error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error while listening to sub id {sub_id}: {str(error)}"
        ) from error


@app.post('/publish/{channel}')
async def publish(event: PublishEvent, channel: str,
                  user: User = Depends(get_current_user)):
    """Publish an event on the provided Pub/Sub channel"""
    metrics.add('http_requests_total', 1)
    event_dict = PublishEvent.dict(event)
    # 1 - Extract data and attributes from the event
    # 2 - Add the owner as an extra attribute
    # 3 - Collect all the other extra attributes, if available, without
    #     overwriting any of the standard ones in the dict
    data = event_dict.pop('data')
    extra_attributes = event_dict.pop("attributes")
    attributes = event_dict
    attributes['owner'] = user.username
    if extra_attributes:
        for k in extra_attributes:
            if k not in attributes:
                attributes[k] = extra_attributes[k]
    await pubsub.publish_cloudevent(channel, data, attributes)


@app.post('/push/{list_name}')
async def push(raw: dict, list_name: str,
               user: User = Depends(get_current_user)):
    """Push a message on the provided list"""
    metrics.add('http_requests_total', 1)
    attributes = dict(raw)
    data = attributes.pop('data')
    await pubsub.push_cloudevent(list_name, data, attributes)


@app.get('/pop/{list_name}')
async def pop(list_name: str, user: User = Depends(get_current_user)):
    """Pop a message from a given list"""
    metrics.add('http_requests_total', 1)
    return await pubsub.pop(list_name)


@app.get('/stats/subscriptions', response_model=List[SubscriptionStats])
async def stats(user: User = Depends(get_current_superuser)):
    """Get details of all existing subscriptions"""
    metrics.add('http_requests_total', 1)
    return await pubsub.subscription_stats()


@app.get('/viewer')
async def viewer():
    """Serve simple HTML page to view the API /static/viewer.html
    Set various no-cache tag we might update it often"""
    metrics.add('http_requests_total', 1)
    root_dir = os.path.dirname(os.path.abspath(__file__))
    viewer_path = os.path.join(root_dir, 'templates', 'viewer.html')
    with open(viewer_path, 'r', encoding='utf-8') as file:
        # set header to text/html and no-cache stuff
        hdr = {
            'Content-Type': 'text/html',
            'Cache-Control': 'no-cache, no-store, must-revalidate',
            'Pragma': 'no-cache',
            'Expires': '0'
        }
        return PlainTextResponse(file.read(), headers=hdr)


@app.get('/dashboard')
async def dashboard():
    """Serve simple HTML page to view the API dashboard.html
    Set various no-cache tag we might update it often"""
    metrics.add('http_requests_total', 1)
    root_dir = os.path.dirname(os.path.abspath(__file__))
    dashboard_path = os.path.join(root_dir, 'templates', 'dashboard.html')
    with open(dashboard_path, 'r', encoding='utf-8') as file:
        # set header to text/html and no-cache stuff
        hdr = {
            'Content-Type': 'text/html',
            'Cache-Control': 'no-cache, no-store, must-revalidate',
            'Pragma': 'no-cache',
            'Expires': '0'
        }
        return PlainTextResponse(file.read(), headers=hdr)


@app.get('/manage')
async def manage():
    """Serve simple HTML page to submit custom nodes"""
    metrics.add('http_requests_total', 1)
    root_dir = os.path.dirname(os.path.abspath(__file__))
    manage_path = os.path.join(root_dir, 'templates', 'manage.html')
    with open(manage_path, 'r', encoding='utf-8') as file:
        # set header to text/html and no-cache stuff
        hdr = {
            'Content-Type': 'text/html',
            'Cache-Control': 'no-cache, no-store, must-revalidate',
            'Pragma': 'no-cache',
            'Expires': '0'
        }
        return PlainTextResponse(file.read(), headers=hdr)


@app.get('/stats')
async def stats_page():
    """Serve simple HTML page to view infrastructure statistics"""
    metrics.add('http_requests_total', 1)
    root_dir = os.path.dirname(os.path.abspath(__file__))
    stats_path = os.path.join(root_dir, 'templates', 'stats.html')
    with open(stats_path, 'r', encoding='utf-8') as file:
        # set header to text/html and no-cache stuff
        hdr = {
            'Content-Type': 'text/html',
            'Cache-Control': 'no-cache, no-store, must-revalidate',
            'Pragma': 'no-cache',
            'Expires': '0'
        }
        return PlainTextResponse(file.read(), headers=hdr)


@app.get('/icons/{icon_name}')
async def icons(icon_name: str):
    """Serve icons from /static/icons"""
    metrics.add('http_requests_total', 1)
    root_dir = os.path.dirname(os.path.abspath(__file__))
    if not re.match(r'^[A-Za-z0-9_.-]+\.png$', icon_name):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid icon name"
        )
    icon_path = os.path.join(root_dir, 'templates', icon_name)
    return FileResponse(icon_path)


@app.get('/metrics')
async def get_metrics():
    """Get metrics"""
    metrics.add('http_requests_total', 1)
    # return metrics as plaintext in prometheus format
    all_metrics = metrics.all()
    response = ''
    for key, value in all_metrics.items():
        response += f'{key}{{instance="api"}} {value}\n'
    return PlainTextResponse(response)


@app.get('/maintenance/purge-old-nodes')
async def purge_handler(current_user: User = Depends(get_current_superuser),
                        days: int = 180,
                        batch_size: int = 1000):
    """Purge old nodes from the database
    This is a maintenance operation and should be performed
    only by superusers.
    Accepts GET parameters:
    - days: Number of days to keep nodes, default is 180.
    - batch_size: Number of nodes to delete in one batch, default is 1000.
    """
    metrics.add('http_requests_total', 1)
    return await purge_old_nodes(age_days=days, batch_size=batch_size)


versioned_app = VersionedFastAPI(app,
                                 version_format='{major}',
                                 prefix_format='/v{major}',
                                 enable_latest=True,
                                 default_version=(0, 0),
                                 on_startup=[
                                     pubsub_startup,
                                     create_indexes,
                                     initialize_beanie,
                                     ensure_legacy_node_editors,
                                     start_background_tasks,
                                 ])


# traceback_exception_handler is a global exception handler that will be
# triggered for all exceptions that are not handled by specific exception
def traceback_exception_handler(request: Request, exc: Exception):
    """Global exception handler to print traceback"""
    print(f"Exception: {exc}")
    traceback.print_exception(type(exc), exc, exc.__traceback__)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"message": "Internal server error, check container logs"}
    )


# Workaround to use global exception handlers for versioned API.
# The issue has already been reported here:
# https://github.com/DeanWay/fastapi-versioning/issues/30
for sub_app in versioned_app.routes:
    if hasattr(sub_app.app, "add_exception_handler"):
        sub_app.app.add_exception_handler(
            ValueError, value_error_exception_handler
        )
        sub_app.app.add_exception_handler(
            errors.InvalidId, invalid_id_exception_handler
        )
        # print traceback for all other exceptions
        sub_app.app.add_exception_handler(
            Exception, traceback_exception_handler
        )


@versioned_app.middleware("http")
async def redirect_http_requests(request: Request, call_next):
    """Redirect request with version prefix when no version is provided"""
    response = None
    path = request.scope['path']
    match = re.match(r'^/(v[\d.]+)', path)
    if match:
        prefix = match.group(1)
        if prefix not in API_VERSIONS:
            response = PlainTextResponse(
                f"Unsupported API version: {prefix}",
                status_code=status.HTTP_400_BAD_REQUEST
            )
    elif not path.startswith('/latest'):
        request.scope['path'] = '/latest' + path
    return response or await call_next(request)
