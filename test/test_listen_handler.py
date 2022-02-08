# SPDX-License-Identifier: LGPL-2.1-or-later
#
# Copyright (C) 2022 Collabora Limited
# Author: Alexandra Pereira <alexandra.pereira@collabora.com>

# Copyright (C) 2022 Jeny Sadadia
# Author: Jeny Sadadia <jeny.sadadia@gmail.com>

# pylint: disable=unused-argument

"""Unit test functions for KernelCI API listen handler"""

from fastapi.testclient import TestClient

from api.main import app
from api.models import User


def test_listen_endpoint(mock_get_current_user,
                         mock_init_sub_id,
                         mock_listen):
    """
    Test Case : Test KernelCI API GET /listen endpoint for the
    positive path
    Expected Result :
        HTTP Response Code 200 OK
        Listen for events on a channel.
    """
    user = User(username='bob',
                hashed_password='$2b$12$CpJZx5ooxM11bCFXT76/z.o6HWs2sPJy4iP8.'
                                'xCZGmM8jWXUXJZ4K',
                active=True)
    mock_get_current_user.return_value = user
    mock_listen.return_value = 'Listening for events on channel 1'

    with TestClient(app) as client:
        response = client.get(
            "/listen/1",
            headers={
                "Authorization": "Bearer "
                "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
                "eyJzdWIiOiJib2IifQ.ci1smeJeuX779PptTkuaG1S"
                "Edkp5M1S1AgYvX8VdB20"
            },
        )
        assert response.status_code == 200


def test_listen_endpoint_not_found(mock_get_current_user,
                                   mock_init_sub_id):
    """
    Test Case : Test KernelCI API GET /listen endpoint for the
    negative path
    Expected Result :
        HTTP Response Code 404 Not Found
        JSON with 'detail' key
        No existing pub/sub subscription with provided id
    """
    user = User(username='bob',
                hashed_password='$2b$12$CpJZx5ooxM11bCFXT76/z.o6HWs2sPJy4iP8.'
                                'xCZGmM8jWXUXJZ4K',
                active=True)
    mock_get_current_user.return_value = user

    with TestClient(app) as client:
        response = client.get(
            "/listen/1",
            headers={
                "Authorization": "Bearer "
                "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
                "eyJzdWIiOiJib2IifQ.ci1smeJeuX779PptTkuaG1S"
                "Edkp5M1S1AgYvX8VdB20"
            },
        )
        assert response.status_code == 404
        assert 'detail' in response.json()


def test_listen_endpoint_without_token(mock_get_current_user,
                                       mock_init_sub_id):
    """
    Test Case : Test KernelCI API GET /listen endpoint for the
    negative path
    Expected Result :
        HTTP Response Code 401 Unauthorized
        The request requires user authentication by token in header
    """
    user = User(username='bob',
                hashed_password='$2b$12$CpJZx5ooxM11bCFXT76/z.o6HWs2sPJy4iP8.'
                                'xCZGmM8jWXUXJZ4K',
                active=True)
    mock_get_current_user.return_value = user

    with TestClient(app) as client:
        response = client.get(
            "/listen/1",
            headers={
                "Accept": "application/json"
            },
        )
        assert response.status_code == 401
