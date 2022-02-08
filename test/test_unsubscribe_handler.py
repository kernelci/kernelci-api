# SPDX-License-Identifier: LGPL-2.1-or-later
#
# Copyright (C) 2022 Jeny Sadadia
# Author: Jeny Sadadia <jeny.sadadia@gmail.com>

# pylint: disable=unused-argument

"""Unit test functions for KernelCI API unsubscribe handler"""

from fastapi.testclient import TestClient

from api.main import app
from api.models import User


def test_unsubscribe_endpoint(mock_get_current_user,
                              mock_init_sub_id, mock_unsubscribe):
    """
    Test Case : Test KernelCI API /unsubscribe endpoint positive path
    Expected Result :
        HTTP Response Code 200 OK
    """
    user = User(username='bob',
                hashed_password='$2b$12$CpJZx5ooxM11bCFXT76/z.o6HWs2sPJy4iP8.'
                                'xCZGmM8jWXUXJZ4K',
                active=True)
    mock_get_current_user.return_value = user

    with TestClient(app) as client:
        response = client.post(
            "/unsubscribe/1",
            headers={
                "Authorization": "Bearer "
                "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
                "eyJzdWIiOiJib2IifQ.ci1smeJeuX779PptTkuaG1S"
                "Edkp5M1S1AgYvX8VdB20"
            },
        )
        assert response.status_code == 200


def test_unsubscribe_endpoint_empty_response(mock_get_current_user,
                                             mock_init_sub_id):
    """
    Test Case : Test KernelCI API /unsubscribe endpoint negative path
    Expected Result :
        HTTP Response Code 404 Not Found
        JSON with 'detail' key
    """
    user = User(username='bob',
                hashed_password='$2b$12$CpJZx5ooxM11bCFXT76/z.o6HWs2sPJy4iP8.'
                                'xCZGmM8jWXUXJZ4K',
                active=True)
    mock_get_current_user.return_value = user

    with TestClient(app) as client:
        response = client.post(
            "/unsubscribe/1",
            headers={
                "Authorization": "Bearer "
                "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
                "eyJzdWIiOiJib2IifQ.ci1smeJeuX779PptTkuaG1S"
                "Edkp5M1S1AgYvX8VdB20"
            },
        )
        print("response.json()", response.json())
        assert response.status_code == 404
        assert 'detail' in response.json()
