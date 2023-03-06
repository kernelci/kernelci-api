# SPDX-License-Identifier: LGPL-2.1-or-later
#
# Copyright (C) 2022 Jeny Sadadia
# Author: Jeny Sadadia <jeny.sadadia@gmail.com>

# pylint: disable=unused-argument

"""Unit test function for KernelCI API subscribe handler"""

from tests.unit_tests.conftest import BEARER_TOKEN
from api.pubsub import Subscription


def test_subscribe_endpoint(mock_get_current_user, mock_init_sub_id,
                            mock_subscribe, test_client):
    """
    Test Case : Test KernelCI API /subscribe endpoint
    Expected Result :
        HTTP Response Code 200 OK
        JSON with 'id' and 'channel' keys
    """
    subscribe = Subscription(id=1, channel='abc')
    mock_subscribe.return_value = subscribe

    response = test_client.post(
        "subscribe/abc",
        headers={
            "Authorization": BEARER_TOKEN
        },
    )
    print("response.json()", response.json())
    assert response.status_code == 200
    assert ('id', 'channel') == tuple(response.json().keys())
