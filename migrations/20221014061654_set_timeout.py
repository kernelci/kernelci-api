# SPDX-License-Identifier: LGPL-2.1-or-later
#
# Copyright (C) 2022 Collabora Limited
# Author: Jeny Sadadia <jeny.sadadia@collabora.com>

"""
Migration to update Node.timeout
"""

from datetime import timedelta

name = '20221014061654_set_timeout'
dependencies = []


def upgrade(db: "pymongo.database.Database"):
    nodes = db.node.find()
    for node in nodes:
        timeout = node['created'] + timedelta(hours=6)
        db.node.update_one(
            {
                "_id": node['_id']
            },
            {
                "$set": {
                    "timeout": timeout
                }
            },
        )


def downgrade(db: "pymongo.database.Database"):
    pass
