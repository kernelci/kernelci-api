# SPDX-License-Identifier: LGPL-2.1-or-later
#
# Copyright (C) 2023 Collabora Limited
# Author: Jeny Sadadia <jeny.sadadia@collabora.com>


"""End-to-end test functions for KernelCI API unsubscribe handler"""

import pytest


@pytest.mark.dependency(
    depends=[
        'e2e_tests/test_subscribe_handler.py::test_subscribe_node_channel'],
    scope='session')
@pytest.mark.order("last")
def test_unsubscribe_node_channel(test_client):
    """
    Test Case : Test KernelCI API '/unsubscribe' endpoint with 'node' channel
    Expected Result :
        HTTP Response Code 200 OK
    """
    response = test_client.post(
        f"unsubscribe/{pytest.node_channel_subscription_id}",
        headers={
            "Authorization": f"Bearer {pytest.BEARER_TOKEN}"
        },
    )
    assert response.status_code == 200


@pytest.mark.dependency(
    depends=[
        'e2e_tests/test_subscribe_handler.py::test_subscribe_test_channel'],
    scope='session')
@pytest.mark.order("last")
def test_unsubscribe_test_channel(test_client):
    """
    Test Case : Test KernelCI API '/unsubscribe' endpoint with 'test_channel'
    Expected Result :
        HTTP Response Code 200 OK
    """
    response = test_client.post(
        f"unsubscribe/{pytest.test_channel_subscription_id}",
        headers={
            "Authorization": f"Bearer {pytest.BEARER_TOKEN}"
        },
    )
    assert response.status_code == 200
