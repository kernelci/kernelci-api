# SPDX-License-Identifier: LGPL-2.1-or-later
#
# Copyright (C) 2022 Jeny Sadadia
# Author: Jeny Sadadia <jeny.sadadia@gmail.com>
#
# Copyright (C) 2022 Collabora Limited
# Author: Jeny Sadadia <jeny.sadadia@collabora.com>

# pylint: disable=unused-argument

"""Unit test functions for KernelCI API node handler"""

import json

from tests.unit_tests.conftest import BEARER_TOKEN
from api.models import Node, Revision


def test_create_node_endpoint(mock_get_current_user, mock_init_sub_id,
                              mock_db_create, mock_publish_cloudevent,
                              test_client):
    """
    Test Case : Test KernelCI API /node endpoint
    Expected Result :
        HTTP Response Code 200 OK
        JSON with created Node object attributes
    """
    revision_obj = Revision(
                tree="mainline",
                url="https://git.kernel.org/pub/scm/linux/kernel/git/"
                    "torvalds/linux.git",
                branch="master",
                commit="2a987e65025e2b79c6d453b78cb5985ac6e5eb26",
                describe="v5.16-rc4-31-g2a987e65025e"
    )
    node_obj = Node(
            _id="61bda8f2eb1a63d2b7152418",
            kind="node",
            name="checkout",
            path=["checkout"],
            group="debug",
            revision=revision_obj,
            parent=None,
            state="closing",
            result=None,
        )
    mock_db_create.return_value = node_obj

    request_dict = {
        "name": "checkout",
        "path": ["checkout"],
        "revision": {
            "tree": "mainline",
            "url": "https://git.kernel.org/pub/scm/linux/kernel/git/"
                    "torvalds/linux.git",
            "branch": "master",
            "commit": "2a987e65025e2b79c6d453b78cb5985ac6e5eb26",
            "describe": "v5.16-rc4-31-g2a987e65025e"
            }
        }
    response = test_client.post(
        "node",
        headers={
            "Accept": "application/json",
            "Authorization": BEARER_TOKEN
        },
        data=json.dumps(request_dict)
        )
    print("response.json()", response.json())
    assert response.status_code == 200
    assert response.json().keys() == {
        '_id',
        'artifacts',
        'created',
        'group',
        'holdoff',
        'kind',
        'name',
        'path',
        'parent',
        'result',
        'revision',
        'state',
        'timeout',
        'updated',
    }


def test_get_nodes_by_attributes_endpoint(mock_get_current_user,
                                          mock_db_find_by_attributes,
                                          mock_init_sub_id, test_client):
    """
    Test Case : Test KernelCI API GET /nodes?attribute_name=attribute_value
    endpoint for the positive path
    Expected Result :
        HTTP Response Code 200 OK
        List with matching Node objects
    """
    revision_obj_1 = Revision(
                tree="mainline",
                url="https://git.kernel.org/pub/scm/linux/kernel/git/"
                    "torvalds/linux.git",
                branch="master",
                commit="2a987e65025e2b79c6d453b78cb5985ac6e5eb26",
                describe="v5.16-rc4-31-g2a987e65025e"
                )
    node_obj_1 = Node(
            _id="61bda8f2eb1a63d2b7152418",
            kind="node",
            name="checkout",
            path=["checkout"],
            revision=revision_obj_1,
            parent="61bda8f2eb1a63d2b7152410",
            state="closing",
            result=None,
        )
    revision_obj_2 = Revision(
                tree="mainline",
                url="https://git.kernel.org/pub/scm/linux/kernel/git/"
                    "torvalds/linux.git",
                branch="master",
                commit="2a987e65025e2b79c6d453b78cb5985ac6e5eb45",
                describe="v5.16-rc4-31-g2a987e65025e"
                )
    node_obj_2 = Node(
            _id="61bda8f2eb1a63d2b7152414",
            kind="node",
            name="checkout",
            path=["checkout"],
            revision=revision_obj_2,
            parent="61bda8f2eb1a63d2b7152410",
            state="closing",
            result=None,
        )
    mock_db_find_by_attributes.return_value = {
        'items': [node_obj_1, node_obj_2],
        'total': 2,
        'limit': 50,
        'offset': 0
    }

    params = {
        "name": "checkout",
        "revision.tree": "mainline",
        "revision.branch": "master",
        "state": "closing",
        "parent": "61bda8f2eb1a63d2b7152410",
    }
    response = test_client.get(
        "nodes",
        params=params,
        )
    print("response.json()", response.json())
    assert response.status_code == 200
    assert len(response.json()['items']) > 0


def test_get_nodes_by_attributes_endpoint_node_not_found(
        mock_get_current_user,
        mock_db_find_by_attributes,
        mock_init_sub_id,
        test_client):
    """
    Test Case : Test KernelCI API GET /nodes?attribute_name=attribute_value
    endpoint for the node not found
    Expected Result :
        HTTP Response Code 200 OK
        Empty list
    """

    mock_db_find_by_attributes.return_value = {
        'items': [],
        'total': 0,
        'limit': 50,
        'offset': 0
    }

    params = {
        "name": "checkout",
        "revision.tree": "baseline"
    }
    response = test_client.get(
        "nodes",
        params=params
        )
    print("response.json()", response.json())
    assert response.status_code == 200
    assert response.json().get('total') == 0


def test_get_node_by_id_endpoint(mock_get_current_user, mock_db_find_by_id,
                                 mock_init_sub_id, test_client):
    """
    Test Case : Test KernelCI API GET /node/{node_id} endpoint
    for the positive path
    Expected Result :
        HTTP Response Code 200 OK
        JSON with Node object attributes
    """
    revision_obj = Revision(
                tree="mainline",
                url="https://git.kernel.org/pub/scm/linux/kernel/git/"
                    "torvalds/linux.git",
                branch="master",
                commit="2a987e65025e2b79c6d453b78cb5985ac6e5eb26",
                describe="v5.16-rc4-31-g2a987e65025e"
    )
    node_obj = Node(
            _id="61bda8f2eb1a63d2b7152418",
            kind="node",
            name="checkout",
            path=["checkout"],
            group="blah",
            revision=revision_obj,
            parent=None,
            state="closing",
            result=None,
        )
    mock_db_find_by_id.return_value = node_obj

    response = test_client.get("node/61bda8f2eb1a63d2b7152418")
    print("response.json()", response.json())
    assert response.status_code == 200
    assert response.json().keys() == {
        '_id',
        'artifacts',
        'created',
        'group',
        'holdoff',
        'kind',
        'name',
        'path',
        'parent',
        'result',
        'revision',
        'state',
        'timeout',
        'updated',
    }


def test_get_node_by_id_endpoint_empty_response(mock_get_current_user,
                                                mock_db_find_by_id,
                                                mock_init_sub_id,
                                                test_client):
    """
    Test Case : Test KernelCI API GET /node/{node_id} endpoint
    for negative path
    Expected Result :
        HTTP Response Code 200 OK
        Response JSON None
    """
    mock_db_find_by_id.return_value = None

    response = test_client.get("node/61bda8f2eb1a63d2b7152419")
    print("response.json()", response.json())
    assert response.status_code == 200
    assert response.json() is None


def test_get_all_nodes(mock_get_current_user, mock_db_find_by_attributes,
                       mock_init_sub_id, test_client):
    """
    Test Case : Test KernelCI API GET /nodes endpoint for the
    positive path
    Expected Result :
        HTTP Response Code 200 OK
        List of all the node objects.
    """
    revision_obj_1 = Revision(
                tree="mainline",
                url="https://git.kernel.org/pub/scm/linux/kernel/git/"
                    "torvalds/linux.git",
                branch="master",
                commit="2a987e65025e2b79c6d453b78cb5985ac6e5eb26",
                describe="v5.16-rc4-31-g2a987e65025e"
                )
    node_obj_1 = Node(
            _id="61bda8f2eb1a63d2b7152418",
            kind="node",
            name="checkout",
            path=["checkout"],
            revision=revision_obj_1,
            parent=None,
            state="closing",
            result=None,
        )
    revision_obj_2 = Revision(
                tree="mainline",
                url="https://git.kernel.org/pub/scm/linux/kernel/git/"
                    "torvalds/linux.git",
                branch="master",
                commit="2a987e65025e2b79c6d453b78cb5985ac6e5eb45",
                describe="v5.16-rc4-31-g2a987e65025e"
                )
    node_obj_2 = Node(
            _id="61bda8f2eb1a63d2b7152414",
            kind="node",
            name="test_node",
            path=["checkout", "test_suite", "test_node"],
            revision=revision_obj_2,
            parent=None,
            state="closing",
            result=None,
        )
    revision_obj_3 = Revision(
                tree="baseline",
                url="https://git.kernel.org/pub/scm/linux/kernel/git/"
                    "torvalds/linux.git",
                branch="master",
                commit="2a987e65025e2b79c6d453b78cb5985ac6e5eb26",
                describe="v5.16-rc4-31-g2a987e65025e"
                )
    node_obj_3 = Node(
            _id="61bda8f2eb1a63d2b7152421",
            kind="node",
            name="test",
            path=["checkout", "group", "test"],
            revision=revision_obj_3,
            parent=None,
            state="closing",
            result=None,
        )

    mock_db_find_by_attributes.return_value = {
        'items': [node_obj_1, node_obj_2, node_obj_3],
        'total': 3,
        'limit': 50,
        'offset': 0
    }

    response = test_client.get("nodes")
    print("response.json()", response.json())
    assert response.status_code == 200
    assert len(response.json()) > 0


def test_get_all_nodes_empty_response(mock_get_current_user,
                                      mock_db_find_by_attributes,
                                      mock_init_sub_id, test_client):
    """
    Test Case : Test KernelCI API GET /nodes endpoint for the
    negative path
    Expected Result :
        HTTP Response Code 200 OK
        Empty list as no Node object is added.
    """
    mock_db_find_by_attributes.return_value = {
        'items': [],
        'total': 0,
        'limit': 50,
        'offset': 0
    }

    response = test_client.get("nodes")
    print("response.json()", response.json())
    assert response.status_code == 200
    assert response.json().get('total') == 0
