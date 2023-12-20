# SPDX-License-Identifier: LGPL-2.1-or-later
#
# Copyright (C) 2023 Collabora Limited
# Author: Jeny Sadadia <jeny.sadadia@collabora.com>

"""
Migration for User schema after the adoption of fastapi-users for
user management in commit:

    api.main: update/add user management routes

"""

name = '20231102101356_user'
dependencies = []

def user_upgrade_needed(user):
    """Checks if a DB user passed as a parameter needs to be migrated
    with this script.

    Parameters:
      user: a mongodb document (dict) defining a KernelCI user

    Returns:
      True if the user needs to be migrated, False otherwise

    """
    # The existence of a 'profile' key seems to be enough to detect a
    # pre-migration user
    if 'profile' in user:
        return True
    else:
        return False


def upgrade(db: "pymongo.database.Database"):
    users = db.user.find()
    db.user.drop_indexes()
    for user in users:
        # Skip users that don't need any changes
        if not user_upgrade_needed(user):
            continue
        # Check if the user is an admin (superuser), remove it from the
        # "admin" user group if it is
        is_superuser = False
        new_groups_list = [g for g in user['profile']['groups']
                           if g['name'] != 'admin']
        if len(new_groups_list) != len(user['profile']['groups']):
            is_superuser = True
            user['profile']['groups'] = new_groups_list
        # User update
        db.user.replace_one(
            {
                "_id": user['_id']
            },
            {
                "_id": user['_id'],
                "email": user['profile']['email'],
                "hashed_password": user['profile']['hashed_password'],
                "is_active": user['active'],
                "is_superuser": is_superuser,
                "is_verified": False,
                "username": user['profile']['username'],
                "groups": user['profile']['groups']
            },
        )
    # Sanity check: check if there are any old-format users in the
    # "admin" group. Remove the group if there aren't any
    remaining_admins = db.user.count(
        {
            "groups": {
                "$elemMatch": {"name": "admin"}
            }
        }
    )
    if remaining_admins == 0:
        db.usergroup.delete_one({"name": "admin"})
    else:
        print("Some old 'admin' users still remain")


def downgrade(db: "pymongo.database.Database"):
    superusers = db.user.find({'is_superuser': True})
    if superusers:
        # Create the 'admin' group if it doesn't exist
        db.usergroup.update_one(
            {'name': 'admin'},
            {'$setOnInsert': {'name': 'admin'}},
            upsert=True
        )
        admin_group = db.usergroup.find_one({'name': 'admin'})

    users = db.user.find()
    db.user.drop_indexes()
    for user in users:
        # Skip users that weren't migrated (unlikely corner case)
        if user_upgrade_needed(user):
            continue
        if user.get('is_superuser') == True:
            # Add user to admin group
            new_groups_list = [g for g in user['groups']
                               if g['name'] != 'admin']
            new_groups_list.append(admin_group)
            user['groups'] = new_groups_list

        db.user.replace_one(
            {
                '_id': user['_id'],
            },
            {
                '_id': user['_id'],
                'active': user['is_active'],
                'profile': {
                    'email': user['email'],
                    'hashed_password': user['hashed_password'],
                    'username': user['username'],
                    'groups': user['groups'],
                }
            }
        )
