# SPDX-License-Identifier: LGPL-2.1-or-later
#
# Copyright (C) 2022 Jeny Sadadia
# Author: Jeny Sadadia <jeny.sadadia@gmail.com>

"""Unit test function for KernelCI API root handler"""


def test_root_endpoint(test_client):
    """
    Test Case : Test KernelCI API root endpoint
    Expected Result :
        HTTP Response Code 200 OK
        HTML landing page
    """
    response = test_client.get("/")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert "KernelCI API Server" in response.text


def test_health_endpoint(test_client):
    """
    Test Case : Test KernelCI API health endpoint
    Expected Result :
        HTTP Response Code 200 OK
        JSON with health status
    """
    response = test_client.get("health")
    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "KernelCI API",
    }
