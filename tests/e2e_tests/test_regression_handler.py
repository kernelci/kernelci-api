# SPDX-License-Identifier: LGPL-2.1-or-later
#
# Copyright (C) 2023 Collabora Limited
# Author: Jeny Sadadia <jeny.sadadia@collabora.com>


"""End-to-end test function for KernelCI API regression handler"""

import pytest

from .test_node_handler import create_node, get_node_by_attribute


@pytest.mark.dependency(
    depends=[
        "tests/e2e_tests/test_pipeline.py::test_node_pipeline"],
    scope="session")
@pytest.mark.asyncio
async def test_regression_handler(test_async_client):
    """
    The function is used to test creation of a regression object.

    First, it will get 'checkout' node. After getting the parent node,
    two 'kver' child nodes having different name and result ('pass' and
    'fail') will be created. Based on child nodes, a regression
    node will be generated and added to database using 'create_node'
    method.
    """
    # Get "checkout" node
    response = await get_node_by_attribute(
        test_async_client, {"name": "checkout"}
    )
    checkout_node = response.json()["items"][0]

    # Create a 'kver' passed node
    passed_node = {
        "name": "kver",
        "kind": "test",
        "path": "checkout/kver",
        "group": "kver",
        "parent": checkout_node["id"],
        "data": {
            "kernel_revision": {
                "tree": "mainline",
                "url": "https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git",
                "branch": "master",
                "commit": "2a987e65025e2b79c6d453b78cb5985ac6e5eb26",
                "describe": "v5.16-rc4-31-g2a987e65025e",
            },
        },
        "state": "done",
        "result": "pass",
    }

    passed_node_obj = (
        await create_node(test_async_client, passed_node)
    ).json()

    # Create a 'kver' failed node
    failed_node = passed_node.copy()
    failed_node["result"] = "fail"

    failed_node_obj = (
        await create_node(test_async_client, failed_node)
    ).json()

    # Create a "kver" regression node
    regression_fields = ['group', 'name', 'path', 'state']
    regression_node = {
        field: failed_node_obj[field]
        for field in regression_fields
    }

    regression_node["kind"] = "regression"
    regression_node["data"] = {
        "fail_node": failed_node_obj["id"],
        "pass_node": passed_node_obj["id"]
    }
    await create_node(test_async_client, regression_node)
