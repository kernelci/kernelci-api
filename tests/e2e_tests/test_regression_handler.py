# SPDX-License-Identifier: LGPL-2.1-or-later
#
# Copyright (C) 2023 Collabora Limited
# Author: Jeny Sadadia <jeny.sadadia@collabora.com>


"""End-to-end test function for KernelCI API regression handler"""

import json
import pytest

from .test_node_handler import create_node, get_node_by_attribute


async def create_regression(test_async_client, regression_node):
    """
    Test Case : Test KernelCI API POST '/regression' endpoint
    Expected Result :
        HTTP Response Code 200 OK
        JSON with created Regression object attributes
    """
    response = await test_async_client.post(
        "regression",
        headers={
            "Accept": "application/json",
            "Authorization": f"Bearer {pytest.BEARER_TOKEN}"
        },
        data=json.dumps(regression_node)
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
            'path',
            'parent',
            'result',
            'revision',
            'regression_data',
            'state',
            'timeout',
            'updated',
        }


@pytest.mark.dependency(
    depends=[
        "e2e_tests/test_pipeline.py::test_node_pipeline"],
    scope="session")
@pytest.mark.asyncio
async def test_regression_handler(test_async_client):
    """
    The function is used to test creation of a regression object.

    First, it will get 'checkout' node. After getting the parent node,
    two 'kver' child nodes having different name and result ('pass' and
    'fail') will be created. Based on child nodes, a regression
    node will be generated and added to database using 'create_regression'
    method.
    """
    # Get "checkout" node
    response = await get_node_by_attribute(
        test_async_client, {"name": "checkout"}
    )
    checkout_node = response.json()["items"][0]

    # Create a 'kver' passed node
    passed_node = {
        "name": "passed_kver",
        "path": ["checkout", "kver"],
        "group": "kver",
        "parent": checkout_node["id"],
        "revision": {
            "tree": "mainline",
            "url": "https://git.kernel.org/pub/scm/linux/kernel/git/"
                    "torvalds/linux.git",
            "branch": "master",
            "commit": "2a987e65025e2b79c6d453b78cb5985ac6e5eb26",
            "describe": "v5.16-rc4-31-g2a987e65025e",
        },
        "state": "done",
        "result": "pass",
    }

    passed_node_obj = (
        await create_node(test_async_client, passed_node)
    ).json()

    # Create a 'kver' failed node
    failed_node = passed_node.copy()
    failed_node["name"] = "failed_kver"
    failed_node["result"] = "fail"

    failed_node_obj = (
        await create_node(test_async_client, failed_node)
    ).json()

    # Create a "kver" regression node
    regression_fields = [
            'group', 'name', 'path', 'revision', 'result', 'state',
        ]
    regression_node = {
        field: failed_node_obj[field]
        for field in regression_fields
    }

    regression_node["parent"] = failed_node_obj["id"]
    regression_node["regression_data"] = [failed_node_obj, passed_node_obj]
    await create_regression(test_async_client, regression_node)
