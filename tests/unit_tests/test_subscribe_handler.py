# SPDX-License-Identifier: LGPL-2.1-or-later
#
# Copyright (C) 2022 Jeny Sadadia
# Author: Jeny Sadadia <jeny.sadadia@gmail.com>

# pylint: disable=unused-argument

"""Unit test function for KernelCI API subscribe handler"""

from tests.unit_tests.conftest import BEARER_TOKEN
from api.models import Subscription


def test_subscribe_endpoint(mock_subscribe, test_client):
    """
    Test Case : Test KernelCI API /subscribe endpoint
    Expected Result :
        HTTP Response Code 200 OK
        JSON with 'id' and 'channel' keys
    """
    subscribe = Subscription(id=1, channel='abc', user='test')
    mock_subscribe.return_value = subscribe

    response = test_client.post(
        "subscribe/abc",
        headers={
            "Authorization": BEARER_TOKEN
        },
    )
    print("response.json()", response.json())
    assert response.status_code == 200
    assert ('id', 'channel', 'user') == tuple(response.json().keys())
