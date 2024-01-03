# SPDX-License-Identifier: LGPL-2.1-or-later
#
# Copyright (C) 2023 Collabora Limited
# Author: Jeny Sadadia <jeny.sadadia@collabora.com>


"""Helper function for KernelCI API listen handler"""

import asyncio
import pytest


def create_listen_task(test_async_client, subscription_id):
    """
    Create an asyncio Task to listen to pubsub events on node channel using
    API endpoint `/listen`.
    Returns the task instance.
    """
    listen_path = '/'.join(['listen', str(subscription_id)])
    task_listen = asyncio.create_task(
        test_async_client.get(
            listen_path,
            headers={
                "Accept": "application/json",
                "Authorization": f"Bearer {pytest.BEARER_TOKEN}"  # pylint: disable=no-member
            },
        )
    )
    return task_listen
