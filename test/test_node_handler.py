# SPDX-License-Identifier: LGPL-2.1-or-later
#
# Copyright (C) 2022 Jeny Sadadia
# Author: Jeny Sadadia <jeny.sadadia@gmail.com>

import pytest
from api.main import app
from api.models import User, Node, Revision
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock
import json


@pytest.fixture()
def mock_get_current_user(mocker):
    async_mock = AsyncMock()
    mocker.patch('api.auth.Authentication.get_current_user',
                 side_effect=async_mock)
    return async_mock


@pytest.fixture()
def mock_init_sub_id(mocker):
    async_mock = AsyncMock()
    mocker.patch('api.pubsub.PubSub._init_sub_id',
                 side_effect=async_mock)
    return async_mock


@pytest.fixture()
def mock_db_create(mocker):
    async_mock = AsyncMock()
    mocker.patch('api.db.Database.create',
                 side_effect=async_mock)
    return async_mock


@pytest.fixture()
def mock_publish_cloudevent(mocker):
    async_mock = AsyncMock()
    mocker.patch('api.pubsub.PubSub.publish_cloudevent',
                 side_effect=async_mock)
    return async_mock


@pytest.fixture()
def mock_db_find_by_attributes(mocker):
    async_mock = AsyncMock()
    mocker.patch('api.db.Database.find_by_attributes',
                 side_effect=async_mock)
    return async_mock


@pytest.fixture()
def mock_db_find_by_id(mocker):
    async_mock = AsyncMock()
    mocker.patch('api.db.Database.find_by_id',
                 side_effect=async_mock)
    return async_mock


def test_create_node_endpoint(mock_get_current_user, mock_init_sub_id,
                              mock_db_create, mock_publish_cloudevent):
    """
    Test Case : Test KernelCI API /node endpoint
    Expected Result :
        HTTP Response Code 200 OK
        JSON with created Node object attributes
    """
    user = User(username='bob',
                hashed_password='$2b$12$CpJZx5ooxM11bCFXT76/z.o6HWs2sPJy4iP8.'
                                'xCZGmM8jWXUXJZ4K',
                active=True)
    mock_get_current_user.return_value = user

    revision_obj = Revision(
                tree="mainline",
                url="https://git.kernel.org/pub/scm/linux/kernel/git/"
                    "torvalds/linux.git",
                branch="master",
                commit="2a987e65025e2b79c6d453b78cb5985ac6e5eb26",
                describe="v5.16-rc4-31-g2a987e65025e"
    )
    node_obj = Node(
            _id="61bda8f2eb1a63d2b7152418",
            kind="node",
            name="checkout",
            revision=revision_obj,
            parent=None,
            status=None
        )
    mock_db_create.return_value = node_obj

    with TestClient(app) as client:
        request_dict = {
            "name": "checkout",
            "revision": {
                "tree": "mainline",
                "url": "https://git.kernel.org/pub/scm/linux/kernel/git/"
                        "torvalds/linux.git",
                "branch": "master",
                "commit": "2a987e65025e2b79c6d453b78cb5985ac6e5eb26",
                "describe": "v5.16-rc4-31-g2a987e65025e"
                }
            }
        response = client.post(
            "/node",
            headers={
                "Accept": "application/json",
                "Authorization": "Bearer "
                "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
                "eyJzdWIiOiJib2IifQ.ci1smeJeuX779PptTkuaG1S"
                "Edkp5M1S1AgYvX8VdB20"
            },
            data=json.dumps(request_dict)
            )
        print("response.json()", response.json())
        assert response.status_code == 200
        assert ('_id', 'kind', 'name', 'revision', 'parent', 'status',
                'created', 'updated') == tuple(response.json().keys())


def test_get_node_by_attributes_endpoint(mock_get_current_user,
                                         mock_db_find_by_attributes,
                                         mock_init_sub_id):
    """
    Test Case : Test KernelCI API GET /nodes?attribute_name=attribute_value
    endpoint for the positive path
    Expected Result :
        HTTP Response Code 200 OK
        List with matching Node objects
    """
    user = User(username='bob',
                hashed_password='$2b$12$CpJZx5ooxM11bCFXT76/z.o6HWs2sPJy4iP8.'
                                'xCZGmM8jWXUXJZ4K',
                active=True)
    mock_get_current_user.return_value = user

    revision_obj_1 = Revision(
                tree="mainline",
                url="https://git.kernel.org/pub/scm/linux/kernel/git/"
                    "torvalds/linux.git",
                branch="master",
                commit="2a987e65025e2b79c6d453b78cb5985ac6e5eb26",
                describe="v5.16-rc4-31-g2a987e65025e"
                )
    node_obj_1 = Node(
            _id="61bda8f2eb1a63d2b7152418",
            kind="node",
            name="checkout",
            revision=revision_obj_1,
            parent=None,
            status=None
        )
    revision_obj_2 = Revision(
                tree="mainline",
                url="https://git.kernel.org/pub/scm/linux/kernel/git/"
                    "torvalds/linux.git",
                branch="master",
                commit="2a987e65025e2b79c6d453b78cb5985ac6e5eb45",
                describe="v5.16-rc4-31-g2a987e65025e"
                )
    node_obj_2 = Node(
            _id="61bda8f2eb1a63d2b7152414",
            kind="node",
            name="checkout",
            revision=revision_obj_2,
            parent=None,
            status=None
        )
    mock_db_find_by_attributes.return_value = [node_obj_1, node_obj_2]

    params = {
        "name": "checkout",
        "revision.tree": "mainline"
    }
    with TestClient(app) as client:
        response = client.get(
            "/nodes",
            params=params,
            )
        print("response.json()", response.json())
        assert response.status_code == 200
        assert len(response.json()) > 0


def test_get_node_by_attributes_endpoint_node_not_found(
        mock_get_current_user,
        mock_db_find_by_attributes,
        mock_init_sub_id):
    """
    Test Case : Test KernelCI API GET /nodes?attribute_name=attribute_value
    endpoint for the node not found
    Expected Result :
        HTTP Response Code 200 OK
        Empty list
    """
    user = User(username='bob',
                hashed_password='$2b$12$CpJZx5ooxM11bCFXT76/z.o6HWs2sPJy4iP8.'
                                'xCZGmM8jWXUXJZ4K',
                active=True)
    mock_get_current_user.return_value = user

    mock_db_find_by_attributes.return_value = []

    params = {
        "name": "checkout",
        "revision.tree": "baseline"
    }
    with TestClient(app) as client:
        response = client.get(
            "/nodes",
            params=params
            )
        print("response.json()", response.json())
        assert response.status_code == 200
        assert len(response.json()) == 0


def test_get_node_by_id_endpoint(mock_get_current_user, mock_db_find_by_id,
                                 mock_init_sub_id):
    """
    Test Case : Test KernelCI API GET /node/{node_id} endpoint
    for the positive path
    Expected Result :
        HTTP Response Code 200 OK
        JSON with Node object attributes
    """
    user = User(username='bob',
                hashed_password='$2b$12$CpJZx5ooxM11bCFXT76/z.o6HWs2sPJy4iP8.'
                                'xCZGmM8jWXUXJZ4K',
                active=True)
    mock_get_current_user.return_value = user

    revision_obj = Revision(
                tree="mainline",
                url="https://git.kernel.org/pub/scm/linux/kernel/git/"
                    "torvalds/linux.git",
                branch="master",
                commit="2a987e65025e2b79c6d453b78cb5985ac6e5eb26",
                describe="v5.16-rc4-31-g2a987e65025e"
    )
    node_obj = Node(
            _id="61bda8f2eb1a63d2b7152418",
            kind="node",
            name="checkout",
            revision=revision_obj,
            parent=None,
            status=None
        )
    mock_db_find_by_id.return_value = node_obj

    with TestClient(app) as client:
        response = client.get("/node/61bda8f2eb1a63d2b7152418")
        print("response.json()", response.json())
        assert response.status_code == 200
        assert ('_id', 'kind', 'name', 'revision', 'parent', 'status',
                'created', 'updated') == tuple(response.json().keys())


def test_get_node_by_id_endpoint_empty_response(mock_get_current_user,
                                                mock_db_find_by_id,
                                                mock_init_sub_id):
    """
    Test Case : Test KernelCI API GET /node/{node_id} endpoint
    for negative path
    Expected Result :
        HTTP Response Code 200 OK
        Response JSON None
    """
    user = User(username='bob',
                hashed_password='$2b$12$CpJZx5ooxM11bCFXT76/z.o6HWs2sPJy4iP8.'
                                'xCZGmM8jWXUXJZ4K',
                active=True)
    mock_get_current_user.return_value = user

    mock_db_find_by_id.return_value = None

    with TestClient(app) as client:
        request_dict = {
            "name": "checkout",
            "revision": {
                "tree": "mainline",
                "url": "https://git.kernel.org/pub/scm/linux/kernel/git/"
                        "torvalds/linux.git",
                "branch": "master",
                "commit": "2a987e65025e2b79c6d453b78cb5985ac6e5eb26",
                "describe": "v5.16-rc4-31-g2a987e65025e"
                }
            }
        response = client.get("/node/61bda8f2eb1a63d2b7152419")
        print("response.json()", response.json())
        assert response.status_code == 200
        assert response.json() is None


def test_get_all_nodes(mock_get_current_user, mock_db_find_by_attributes,
                       mock_init_sub_id):
    """
    Test Case : Test KernelCI API GET /nodes endpoint for the
    positive path
    Expected Result :
        HTTP Response Code 200 OK
        List of all the node objects.
    """
    user = User(username='bob',
                hashed_password='$2b$12$CpJZx5ooxM11bCFXT76/z.o6HWs2sPJy4iP8.'
                                'xCZGmM8jWXUXJZ4K',
                active=True)
    mock_get_current_user.return_value = user

    revision_obj_1 = Revision(
                tree="mainline",
                url="https://git.kernel.org/pub/scm/linux/kernel/git/"
                    "torvalds/linux.git",
                branch="master",
                commit="2a987e65025e2b79c6d453b78cb5985ac6e5eb26",
                describe="v5.16-rc4-31-g2a987e65025e"
                )
    node_obj_1 = Node(
            _id="61bda8f2eb1a63d2b7152418",
            kind="node",
            name="checkout",
            revision=revision_obj_1,
            parent=None,
            status=None
        )
    revision_obj_2 = Revision(
                tree="mainline",
                url="https://git.kernel.org/pub/scm/linux/kernel/git/"
                    "torvalds/linux.git",
                branch="master",
                commit="2a987e65025e2b79c6d453b78cb5985ac6e5eb45",
                describe="v5.16-rc4-31-g2a987e65025e"
                )
    node_obj_2 = Node(
            _id="61bda8f2eb1a63d2b7152414",
            kind="node",
            name="test_node",
            revision=revision_obj_2,
            parent=None,
            status=None
        )
    revision_obj_3 = Revision(
                tree="baseline",
                url="https://git.kernel.org/pub/scm/linux/kernel/git/"
                    "torvalds/linux.git",
                branch="master",
                commit="2a987e65025e2b79c6d453b78cb5985ac6e5eb26",
                describe="v5.16-rc4-31-g2a987e65025e"
                )
    node_obj_3 = Node(
            _id="61bda8f2eb1a63d2b7152421",
            kind="node",
            name="test",
            revision=revision_obj_3,
            parent=None,
            status=None
        )
    mock_db_find_by_attributes.return_value = [node_obj_1, node_obj_2,
                                               node_obj_3]

    with TestClient(app) as client:
        response = client.get("/nodes")
        print("response.json()", response.json())
        assert response.status_code == 200
        assert len(response.json()) > 0


def test_get_all_nodes_empty_response(mock_get_current_user,
                                      mock_db_find_by_attributes,
                                      mock_init_sub_id):
    """
    Test Case : Test KernelCI API GET /nodes endpoint for the
    negative path
    Expected Result :
        HTTP Response Code 200 OK
        Empty list as no Node object is added.
    """
    user = User(username='bob',
                hashed_password='$2b$12$CpJZx5ooxM11bCFXT76/z.o6HWs2sPJy4iP8.'
                                'xCZGmM8jWXUXJZ4K',
                active=True)
    mock_get_current_user.return_value = user

    mock_db_find_by_attributes.return_value = []

    with TestClient(app) as client:
        response = client.get("/nodes")
        print("response.json()", response.json())
        assert response.status_code == 200
        assert len(response.json()) == 0
