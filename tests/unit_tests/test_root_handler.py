# SPDX-License-Identifier: LGPL-2.1-or-later
#
# Copyright (C) 2022 Jeny Sadadia
# Author: Jeny Sadadia <jeny.sadadia@gmail.com>

# pylint: disable=unused-argument

"""Unit test function for KernelCI API root handler"""


def test_root_endpoint(mock_init_sub_id, test_client):
    """
    Test Case : Test KernelCI API root endpoint
    Expected Result :
        HTTP Response Code 200 OK
        JSON with 'message' key
    """
    response = test_client.get("/latest")
    assert response.status_code == 200
    assert response.json() == {"message": "KernelCI API"}
