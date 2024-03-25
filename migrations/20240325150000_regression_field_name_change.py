# SPDX-License-Identifier: LGPL-2.1-or-later
#
# Copyright (C) 2024 Collabora Limited
# Author: Ricardo Cañuelo <ricardo.canuelo@collabora.com>

"""Migration for Regression objects to comply with the models after
kernelci-core commit:

    models: rename regression.data.failed_kernel_revision to kernel_revision

"""

from bson.objectid import ObjectId

name = '20240325150000_regression_field_name_change'
dependencies = ['20231215122000_node_models']


def upgrade(db: "pymongo.database.Database"):
    # Update regression nodes
    regressions = db.node.find({'kind': 'regression'})
    for regression in regressions:
        if 'kernel_revision' in regression['data']:
            continue
        db.node.update_one(
            {'_id': regression['_id']},
            {
                '$set': {
                    'data.kernel_revision': regression['data']['failed_kernel_version']
                },
                '$unset': {'data.failed_kernel_version': ''}
            }
        )


def downgrade(db: 'pymongo.database.Database'):
    # Downgrade regression nodes
    regressions = db.node.find({'kind': 'regression'})
    for regression in regressions:
        if 'failed_kernel_version' in regression['data']:
            continue
        db.node.update_one(
            {'_id': regression['_id']},
            {
                '$set': {
                    'data.failed_kernel_version': regression['data']['kernel_revision']
                },
                '$unset': {'data.kernel_revision': ''}
            }
        )
