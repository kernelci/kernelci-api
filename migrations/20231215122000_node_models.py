# SPDX-License-Identifier: LGPL-2.1-or-later
#
# Copyright (C) 2023 Collabora Limited
# Author: Ricardo Cañuelo <ricardo.canuelo@collabora.com>

"""Migration for Node objects to comply with the models after commits:

    api.models: basic definitions of Node submodels
    api.main: use node endpoints for all type of Node subtypes
    api.db: remove regression collection

"""

from bson.objectid import ObjectId

name = '20231215122000_node_models'
dependencies = ['20231102101356_user']


def node_upgrade_needed(node):
    """Checks if a DB Node passed as a parameter needs to be migrated
    with this script.

    Parameters:
      user: a mongodb document (dict) defining a KernelCI Node

    Returns:
      True if the node needs to be migrated, False otherwise

    """
    # The existence of a 'revision' key seems to be enough to detect a
    # pre-migration Node
    if 'revision' in node:
        return True
    else:
        return False


def upgrade(db: "pymongo.database.Database"):
    # Update nodes
    nodes = db.node.find()
    for node in nodes:
        # Skip any node that's not in the old format
        if not node_upgrade_needed(node):
            continue
        if not node.get('data'):
            # Initialize 'data' field if it's empty: a generic Node
            # with no specific type may have an emtpy 'data' field
            db.node.update_one(
                {'_id': node['_id']},
                {'$set': {'data': {}}}
            )
        # move 'revision' to 'data.kernel_revision'
        db.node.update_one(
            {'_id': node['_id']},
            {
                '$set': {
                    'data.kernel_revision': node['revision']
                },
                '$unset': {'revision': ''}
            }
        )

    # Re-format regressions: move them from "regression" to "node"
    regressions = db.regression.find()
    for regression in regressions:
        db.node.insert_one(
            {
                'name': regression.get('name'),
                'group': regression.get('group'),
                'path': regression.get('path'),
                'kind': 'regression',
                'data': {
                    'pass_node': ObjectId(regression['regression_data'][0]),
                    'fail_node': ObjectId(regression['regression_data'][1])
                },
                'artifacts': regression.get('artifacts'),
                'created': regression.get('created'),
                'updated': regression.get('updated'),
                'timeout': regression.get('timeout'),
                'owner': regression.get('owner'),
            }
        )
        db.regression.delete_one({'_id': regression['_id']})


def downgrade(db: 'pymongo.database.Database'):
    # Move regressions back to "regression"
    regressions = db.node.find({'kind': 'regression'})
    for regression in regressions:
        fail_node = db.node.find_one(
            {'_id': ObjectId(regression['data']['fail_node'])}
        )
        db.regression.insert_one(
            {
                'name': regression.get('name'),
                'group': regression.get('group'),
                'path': regression.get('path'),
                'kind': 'regression',
                'parent': regression['data']['fail_node'],
                'regression_data': [
                    regression['data']['pass_node'],
                    regression['data']['fail_node']
                ],
                'revision': fail_node['data']['kernel_revision'],
                'artifacts': regression.get('artifacts'),
                'created': regression.get('created'),
                'updated': regression.get('updated'),
                'timeout': regression.get('timeout'),
                'owner': regression.get('owner'),
            }
        )
        db.node.delete_one({'_id': regression['_id']})

    # Downgrade node format
    nodes = db.node.find()
    for node in nodes:
        # Skip any node that's already in the old format
        if node_upgrade_needed(node):
            continue
        # move 'data.kernel_revision' to 'revision'
        db.node.update_one(
            {'_id': node['_id']},
            {
                '$set': {
                    'revision': node['data']['kernel_revision']
                },
                '$unset': {'data.kernel_revision': ''}
            }
        )
        # unset 'data' if it's empty
        node['data'].pop('kernel_revision', None)
        if len(node['data']) == 0:
            db.node.update_one(
                {'_id': node['_id']},
                {'$unset': {'data': ''}}
            )
