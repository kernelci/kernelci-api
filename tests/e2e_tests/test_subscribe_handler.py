# SPDX-License-Identifier: LGPL-2.1-or-later
#
# Copyright (C) 2023 Collabora Limited
# Author: Jeny Sadadia <jeny.sadadia@collabora.com>


"""End-to-end test functions for KernelCI API subscribe handler"""

import pytest


@pytest.mark.asyncio
@pytest.mark.dependency(
    depends=['tests/e2e_tests/test_user_creation.py::test_create_regular_user'],
    scope='session')
@pytest.mark.order(3)
async def test_subscribe_node_channel(test_async_client):
    """
    Test Case : Test KernelCI API '/subscribe' endpoint with 'node' channel
    Expected Result :
        HTTP Response Code 200 OK
        JSON with subscription 'id' and 'channel' keys
    """
    response = await test_async_client.post(
        "subscribe/node",
        headers={
            "Authorization": f"Bearer {pytest.BEARER_TOKEN}"  # pylint: disable=no-member
        },
    )
    pytest.node_channel_subscription_id = response.json()['id']
    assert response.status_code == 200
    # only id, channel, user is mandatory in the response
    assert 'id' in response.json()
    assert 'channel' in response.json()
    assert 'user' in response.json()
    assert response.json().get('channel') == 'node'


@pytest.mark.asyncio
@pytest.mark.dependency(
    depends=['tests/e2e_tests/test_user_creation.py::test_create_regular_user'],
    scope='session')
@pytest.mark.order(3)
async def test_subscribe_test_channel(test_async_client):
    """
    Test Case : Test KernelCI API '/subscribe' endpoint with 'test_channel'
    Expected Result :
        HTTP Response Code 200 OK
        JSON with subscription 'id' and 'channel' keys
    """
    response = await test_async_client.post(
        "subscribe/test_channel",
        headers={
            "Authorization": f"Bearer {pytest.BEARER_TOKEN}"  # pylint: disable=no-member
        },
    )
    pytest.test_channel_subscription_id = response.json()['id']
    assert response.status_code == 200
    # only id, channel, user is mandatory in the response
    assert 'id' in response.json()
    assert 'channel' in response.json()
    assert 'user' in response.json()
    assert response.json().get('channel') == 'test_channel'


@pytest.mark.asyncio
@pytest.mark.dependency(
    depends=['tests/e2e_tests/test_user_creation.py::test_create_regular_user'],
    scope='session')
@pytest.mark.order(3)
async def test_subscribe_user_group_channel(test_async_client):
    """
    Test Case : Test KernelCI API '/subscribe' endpoint with 'user_group'
    channel
    Expected Result :
        HTTP Response Code 200 OK
        JSON with subscription 'id' and 'channel' keys
    """
    response = await test_async_client.post(
        "subscribe/user_group",
        headers={
            "Authorization": f"Bearer {pytest.BEARER_TOKEN}"  # pylint: disable=no-member
        },
    )
    pytest.user_group_channel_subscription_id = response.json()['id']
    assert response.status_code == 200
    # only id, channel, user is mandatory in the response
    assert 'id' in response.json()
    assert 'channel' in response.json()
    assert 'user' in response.json()
    assert response.json().get('channel') == 'user_group'
