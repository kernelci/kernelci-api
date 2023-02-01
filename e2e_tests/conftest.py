# SPDX-License-Identifier: LGPL-2.1-or-later
#
# Copyright (C) 2023 Collabora Limited
# Author: Jeny Sadadia <jeny.sadadia@collabora.com>


"""pytest fixtures for KernelCI API end-to-end tests"""

import pytest

from fastapi.testclient import TestClient

from api.main import app

BASE_URL = 'http://api:8000/latest/'


@pytest.fixture(scope='session')
def test_client():
    """Fixture to get FastAPI Test client instance"""
    with TestClient(app=app, base_url=BASE_URL) as client:
        yield client
