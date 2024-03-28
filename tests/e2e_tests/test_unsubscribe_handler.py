# SPDX-License-Identifier: LGPL-2.1-or-later
#
# Copyright (C) 2023 Collabora Limited
# Author: Jeny Sadadia <jeny.sadadia@collabora.com>


"""End-to-end test functions for KernelCI API unsubscribe handler"""

import pytest


@pytest.mark.asyncio
@pytest.mark.dependency(
    depends=[
        'tests/e2e_tests/test_subscribe_handler.py::test_subscribe_node_channel'],
    scope='session')
@pytest.mark.order("last")
async def test_unsubscribe_node_channel(test_async_client):
    """
    Test Case : Test KernelCI API '/unsubscribe' endpoint with 'node' channel
    Expected Result :
        HTTP Response Code 200 OK
    """
    response = await test_async_client.post(
        f"unsubscribe/{pytest.node_channel_subscription_id}",  # pylint: disable=no-member
        headers={
            "Authorization": f"Bearer {pytest.BEARER_TOKEN}"  # pylint: disable=no-member
        },
    )
    assert response.status_code == 200


@pytest.mark.asyncio
@pytest.mark.dependency(
    depends=[
        'tests/e2e_tests/test_subscribe_handler.py::test_subscribe_test_channel'],
    scope='session')
@pytest.mark.order("last")
async def test_unsubscribe_test_channel(test_async_client):
    """
    Test Case : Test KernelCI API '/unsubscribe' endpoint with 'test_channel'
    Expected Result :
        HTTP Response Code 200 OK
    """
    response = await test_async_client.post(
        f"unsubscribe/{pytest.test_channel_subscription_id}",  # pylint: disable=no-member
        headers={
            "Authorization": f"Bearer {pytest.BEARER_TOKEN}"  # pylint: disable=no-member
        },
    )
    assert response.status_code == 200
