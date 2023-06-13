# SPDX-License-Identifier: LGPL-2.1-or-later
#
# Copyright (C) 2023 Collabora Limited
# Author: Jeny Sadadia <jeny.sadadia@collabora.com>

"""End-to-end test functions for KernelCI API user group creation"""

import pytest

from api.models import UserGroup
from api.db import Database
from e2e_tests.conftest import db_create


@pytest.mark.dependency()
@pytest.mark.order(1)
@pytest.mark.asyncio
async def test_create_user_groups():
    """
    Test Case : Create default user groups
    """
    default_user_groups = ['admin']
    for group in default_user_groups:
        obj = await db_create(
            Database.COLLECTIONS[UserGroup],
            UserGroup(name=group))
        assert obj is not None
