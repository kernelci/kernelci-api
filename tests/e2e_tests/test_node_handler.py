# SPDX-License-Identifier: LGPL-2.1-or-later
#
# Copyright (C) 2023 Collabora Limited
# Author: Jeny Sadadia <jeny.sadadia@collabora.com>


"""Test functions for KernelCI API node handler"""

import json
import pytest


async def create_node(test_async_client, node):
    """
    Test Case : Test KernelCI API POST '/node' endpoint
    Expected Result :
        HTTP Response Code 200 OK
        JSON with created Node object attributes
    """
    response = await test_async_client.post(
        "node",
        headers={
            "Accept": "application/json",
            "Authorization": f"Bearer {pytest.BEARER_TOKEN}"
        },
        data=json.dumps(node)
        )
    assert response.status_code == 200
    assert response.json().keys() == {
            'id',
            'artifacts',
            'created',
            'data',
            'group',
            'holdoff',
            'kind',
            'name',
            'owner',
            'path',
            'parent',
            'result',
            'revision',
            'state',
            'timeout',
            'updated',
            'user_groups',
        }
    return response


async def get_node_by_id(test_async_client, node_id):
    """
    Test Case : Test KernelCI API GET /node/{node_id} endpoint
    Expected Result :
        HTTP Response Code 200 OK
        JSON with Node object attributes
    """
    response = await test_async_client.get(
        f"node/{node_id}",
        headers={
            "Accept": "application/json",
            "Authorization": f"Bearer {pytest.BEARER_TOKEN}"
        },
    )
    assert response.status_code == 200
    assert response.json().keys() == {
            'id',
            'artifacts',
            'created',
            'data',
            'group',
            'holdoff',
            'kind',
            'name',
            'owner',
            'path',
            'parent',
            'result',
            'revision',
            'state',
            'timeout',
            'updated',
            'user_groups',
        }
    return response


async def get_node_by_attribute(test_async_client, params):
    """
    Test Case : Test KernelCI API GET /nodes matching query parameters
    Expected Result :
        HTTP Response Code 200 OK
        Returns dictionary with matching Node objects, total number of nodes
        returned along with limit and offset values
    """
    response = await test_async_client.get(
        "nodes",
        params=params,
        headers={
            "Accept": "application/json",
            "Authorization": f"Bearer {pytest.BEARER_TOKEN}"
        },
    )
    assert response.status_code == 200
    assert response.json().keys() == {
            'items',
            'total',
            'limit',
            'offset',
        }
    assert response.json()['total'] >= 0
    return response


async def update_node(test_async_client, node):
    """
    Test Case : Test KernelCI API PUT /node/{node_id} endpoint
    Expected Result :
        HTTP Response Code 200 OK
        JSON with updated Node object
    """
    response = await test_async_client.put(
        f"node/{node['id']}",
        headers={
            "Accept": "application/json",
            "Authorization": f"Bearer {pytest.BEARER_TOKEN}"
        },
        data=json.dumps(node)
    )
    assert response.status_code == 200
    assert response.json().keys() == {
            'id',
            'artifacts',
            'created',
            'data',
            'group',
            'holdoff',
            'kind',
            'name',
            'owner',
            'path',
            'parent',
            'result',
            'revision',
            'state',
            'timeout',
            'updated',
            'user_groups',
        }
