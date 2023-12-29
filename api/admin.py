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
import pymongo

from .auth import Authentication
from .db import Database
from .user_models import User


async def setup_admin_user(db, username, email):
    """Create an admin user"""
    password = getpass.getpass(f"Password for user '{username}': ")
    retyped = getpass.getpass(f"Retype password for user '{username}': ")
    if password != retyped:
        print("Sorry, passwords do not match, aborting.")
        return None
    hashed_password = Authentication.get_password_hash(password)
    print(f"Creating {username} user...")
    try:
        return await db.create(User(
            username=username,
            hashed_password=hashed_password,
            email=email,
            is_superuser=1,
            is_verified=1,
        ))
    except pymongo.errors.DuplicateKeyError as exc:
        err = str(exc)
        if "username" in err:
            print(f"User {username} already exists, aborting.")
        elif "email" in err:
            print(f"User with {email} already exists, aborting.")
        return None


async def main(args):
    db = Database(args.mongo, args.database)
    await db.initialize_beanie()
    await db.create_indexes()
    await setup_admin_user(db, args.username, args.email)
    return True


if __name__ == '__main__':
    parser = argparse.ArgumentParser("Create KernelCI API admin user")
    parser.add_argument('--mongo', default='mongodb://db:27017',
                        help="Mongo server connection string")
    parser.add_argument('--username', default='admin',
                        help="Admin username")
    parser.add_argument('--database', default='kernelci',
                        help="KernelCI database name")
    parser.add_argument('--email', required=True,
                        help="Admin user email address")
    args = parser.parse_args()
    sys.exit(0 if asyncio.run(main(args)) else 1)
