# SPDX-License-Identifier: LGPL-2.1-or-later
#
# Copyright (C) 2021 Jeny Sadadia
# Author: Jeny Sadadia <jeny.sadadia@gmail.com>

import pytest
import requests

DEFAULT_API_TEST_URL = 'http://localhost:8001/'


def test_root_endpoint():
    """
    Test Case : Test KernelCI API root endpoint
    Expected Result : HTTP Response Code 200 OK
    """
    url = "".join(DEFAULT_API_TEST_URL)
    response = requests.get(url)
    assert response.status_code == 200
