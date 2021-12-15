# SPDX-License-Identifier: LGPL-2.1-or-later
#
# Copyright (C) 2021 Jeny Sadadia
# Author: Jeny Sadadia <jeny.sadadia@gmail.com>

import pytest
from .main import app
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    return TestClient(app)


def test_root_endpoint(client):
    """
    Test Case : Test KernelCI API root endpoint
    Expected Result :
        HTTP Response Code 200 OK
        JSON with 'message' key
    """
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "KernelCI API"}
