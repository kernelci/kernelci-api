# SPDX-License-Identifier: LGPL-2.1-or-later
#
# Copyright (C) 2023 Collabora Limited
# Author: Ricardo Cañuelo <ricardo.canuelo@collabora.com>

"""Migration for Node objects to comply with the models after commit:

    api.main: handle new Node path format in node submission

"""

from bson.objectid import ObjectId

name = '20240319103200_node_paths'
dependencies = ['20231102101356_user',
                '20231215122000_node_models']


def path_list_to_string(path_list, is_parent=False):
    """Converts a path list into a slash-separated path string. If
    'is_parent' is True, it adds a trailing slash"""
    path_string = '/'.join(path_list)
    if is_parent:
        path_string += '/'
    return path_string


def path_string_to_list(path_string):
    """Opposite of path_list_to_string. No special case for parent
    nodes"""
    return path_string.rstrip('/').split('/')


def upgrade(db: "pymongo.database.Database"):
    nodes = db.node.find()
    for node in nodes:
        if isinstance(node['path'], list):
            is_parent = db.node.find_one({'parent': node['_id']})
            new_path = path_list_to_string(node['path'], bool(is_parent))
            db.node.update_one(
                {'_id': node['_id']},
                {'$set': {'path': new_path}}
            )


def downgrade(db: 'pymongo.database.Database'):
    nodes = db.node.find()
    for node in nodes:
        if isinstance(node['path'], str):
            new_path = path_string_to_list(node['path'])
            db.node.update_one(
                {'_id': node['_id']},
                {'$set': {'path': new_path}}
            )
