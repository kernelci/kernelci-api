#!/usr/bin/env python3
#
# SPDX-License-Identifier: LGPL-2.1-or-later
#
# Copyright (C) 2022, 2023 Collabora Limited
# Author: Jeny Sadadia <jeny.sadadia@collabora.com>
# Author: Michal Galka <michal.galka@collabora.com>
# Author: Guillaume Tucker <guillaume.tucker@collabora.com>

"""Command line utility for creating an admin user"""

import asyncio
import argparse
import sys

import getpass

from .auth import Authentication
from .db import Database
from .models import UserGroup
from .user_models import User


async def setup_admin_group(db, admin_group):
    group_obj = await db.find_one(UserGroup, name=admin_group)
    if group_obj is None:
        print(f"Creating {admin_group} group...")
        group_obj = await db.create(UserGroup(name=admin_group))
    return group_obj


async def setup_admin_user(db, username, email, admin_group):
    user_obj = await db.find_one_by_attributes(User,
                                               {'profile.username': username})
    if user_obj:
        print(f"User {username} already exists, aborting.")
        print(user_obj.json())
        return None
    password = getpass.getpass(f"Password for user '{args.username}': ")
    retyped = getpass.getpass(f"Retype password for user '{args.username}': ")
    if password != retyped:
        print("Sorry, passwords do not match, aborting.")
        return None
    hashed_password = Authentication.get_password_hash(password)
    print(f"Creating {username} user...")
    return await db.create(User(
        username=username,
        hashed_password=hashed_password,
        email=email,
        groups=[admin_group],
        is_superuser=1,
        is_verified=1,
    ))


async def main(args):
    db = Database(args.mongo, args.database)
    await db.initialize_beanie()
    group = await setup_admin_group(db, args.admin_group)
    user = await setup_admin_user(db, args.username, args.email, group)
    return True


if __name__ == '__main__':
    parser = argparse.ArgumentParser("Create KernelCI API admin user")
    parser.add_argument('--mongo', default='mongodb://db:27017',
                        help="Mongo server connection string")
    parser.add_argument('--username', default='admin',
                        help="Admin username")
    parser.add_argument('--admin-group', default='admin',
                        help="Admin group name")
    parser.add_argument('--database', default='kernelci',
                        help="KernelCI database name")
    parser.add_argument('--email', required=True,
                        help="Admin user email address")
    args = parser.parse_args()
    sys.exit(0 if asyncio.run(main(args)) else 1)
