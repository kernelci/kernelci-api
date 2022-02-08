# SPDX-License-Identifier: LGPL-2.1-or-later
#
# Copyright (C) 2022 Jeny Sadadia
# Author: Jeny Sadadia <jeny.sadadia@gmail.com>

# pylint: disable=unused-argument

"""Unit test function for KernelCI API subscribe handler"""

from fastapi.testclient import TestClient

from api.main import app
from api.models import User
from api.pubsub import Subscription


def test_subscribe_endpoint(mock_get_current_user, mock_init_sub_id,
                            mock_subscribe):
    """
    Test Case : Test KernelCI API /subscribe endpoint
    Expected Result :
        HTTP Response Code 200 OK
        JSON with 'id' and 'channel' keys
    """
    user = User(username='bob',
                hashed_password='$2b$12$CpJZx5ooxM11bCFXT76/z.o6HWs2sPJy4iP8.'
                                'xCZGmM8jWXUXJZ4K',
                active=True)
    mock_get_current_user.return_value = user

    subscribe = Subscription(id=1, channel='abc')
    mock_subscribe.return_value = subscribe

    with TestClient(app) as client:
        # Use context manager to trigger a startup event on the app object
        response = client.post(
            "/subscribe/abc",
            headers={
                "Authorization": "Bearer "
                "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
                "eyJzdWIiOiJib2IifQ.ci1smeJeuX779PptTkuaG1S"
                "Edkp5M1S1AgYvX8VdB20"
            },
        )
        print("response.json()", response.json())
        assert response.status_code == 200
        assert ('id', 'channel') == tuple(response.json().keys())
