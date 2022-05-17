#!/usr/bin/env python3
#
# SPDX-License-Identifier: LGPL-2.1-or-later
#
# Copyright (C) 2022 Collabora Limited
# Author: Jeny Sadadia <jeny.sadadia@collabora.com>

"""Command line utility for admin operations"""

import argparse
import urllib.parse
import requests
import json

from _settings import TOKEN


DEFAULT_URL = 'http://localhost:8001'


def cmd_create_user(args):
    """Command line utility to create new user"""
    headers = {
        'Authorization': f"Bearer {TOKEN}",
    }
    path = '/'.join(['user', args.username])

    if args.is_admin:
        path = '?'.join([path, 'is_admin='+str(args.is_admin)])

    url = urllib.parse.urljoin(args.url, path)

    data = {'password': args.password}
    res = requests.post(url, data=json.dumps(data), headers=headers)
    print(res.json())
    res.raise_for_status()


if __name__ == "__main__":

    parser = argparse.ArgumentParser("KernelCI API Admin:")
    sub_parsers = parser.add_subparsers(title="Commands")

    parser_create_user = sub_parsers.add_parser('create_user',
                                                help="Create a user")
    parser_create_user.set_defaults(func=cmd_create_user)
    parser_create_user.add_argument('username', help="User name")
    parser_create_user.add_argument('password', help="User password")
    parser_create_user.add_argument('--url', default=DEFAULT_URL,
                                    help="API host URL")
    parser_create_user.add_argument('--is_admin', default=0,
                                    help="Provide 1 if the user is admin \
0 otherwise"
                                    )

    args = parser.parse_args()
    try:
        args.func(args)
    except AttributeError as err:
        parser.error("too few arguments")
