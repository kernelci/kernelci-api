# SPDX-License-Identifier: LGPL-2.1-or-later
#
# Copyright (C) 2023 Collabora Limited
# Author: Jeny Sadadia <jeny.sadadia@collabora.com>

"""
Migration for User schema
"""

name = '20231102101356_user'
dependencies = ['20221014061654_set_timeout']


def upgrade(db: "pymongo.database.Database"):
    users = db.user.find()
    db.user.drop_indexes()
    for user in users:
        db.user.replace_one(
            {
                "_id": user['_id']
            },
            {
                "_id": user['_id'],
                "email": user['profile']['email'],
                "hashed_password": user['profile']['hashed_password'],
                "is_active": 1,
                "is_superuser": 0,
                "is_verified": 0,
                "username": user['profile']['username'],
                "groups": user['profile']['groups']
            },
        )


def downgrade(db: "pymongo.database.Database"):
    pass
