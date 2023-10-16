# SPDX-License-Identifier: LGPL-2.1-or-later
#
# Copyright (C) 2022 Collabora Limited
# Author: Jeny Sadadia <jeny.sadadia@collabora.com>

# pylint: disable=unused-argument

"""Unit test functions for KernelCI API count handler"""


def test_count_nodes(mock_db_count, test_client):
    """
    Test Case : Test KernelCI API GET /count endpoint
    Expected Result :
        HTTP Response Code 200 OK
        Total number of nodes available
    """
    mock_db_count.return_value = 10
    response = test_client.get("count")
    print("response.json()", response.json())
    assert response.status_code == 200
    assert response.json() >= 0


def test_count_nodes_matching_attributes(mock_db_count, test_client):
    """
    Test Case : Test KernelCI API GET /count endpoint with attributes
    Expected Result :
        HTTP Response Code 200 OK
        Number of nodes matching attributes
    """
    mock_db_count.return_value = 1
    response = test_client.get("count?name=checkout")
    print("response.json()", response.json())
    assert response.status_code == 200
    assert response.json() == 1
