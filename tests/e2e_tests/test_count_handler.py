# SPDX-License-Identifier: LGPL-2.1-or-later
#
# Copyright (C) 2023 Collabora Limited
# Author: Jeny Sadadia <jeny.sadadia@collabora.com>


"""End-to-end test functions for KernelCI API count handler"""


import pytest


@pytest.mark.asyncio
@pytest.mark.dependency(
    depends=[
        'tests/e2e_tests/test_pipeline.py::test_node_pipeline'],
    scope='session')
async def test_count_nodes(test_async_client):
    """
    Test Case : Test KernelCI API GET /count endpoint
    Expected Result :
        HTTP Response Code 200 OK
        Total number of nodes available
    """
    response = await test_async_client.get("count")
    assert response.status_code == 200
    assert response.json() >= 0


@pytest.mark.asyncio
@pytest.mark.dependency(
    depends=[
        'tests/e2e_tests/test_pipeline.py::test_node_pipeline'],
    scope='session')
async def test_count_nodes_matching_attributes(test_async_client):
    """
    Test Case : Test KernelCI API GET /count endpoint with attributes
    Expected Result :
        HTTP Response Code 200 OK
        Number of nodes matching attributes
    """
    response = await test_async_client.get("count?name=checkout")
    assert response.status_code == 200
    assert response.json() >= 0
