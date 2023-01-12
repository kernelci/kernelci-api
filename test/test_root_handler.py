# SPDX-License-Identifier: LGPL-2.1-or-later
#
# Copyright (C) 2022 Jeny Sadadia
# Author: Jeny Sadadia <jeny.sadadia@gmail.com>

"""Unit test function for KernelCI API root handler"""

from test.conftest import API_VERSION


def test_root_endpoint(client):
    """
    Test Case : Test KernelCI API root endpoint
    Expected Result :
        HTTP Response Code 200 OK
        JSON with 'message' key
    """
    response = client.get(API_VERSION + "/")
    assert response.status_code == 200
    assert response.json() == {"message": "KernelCI API"}
