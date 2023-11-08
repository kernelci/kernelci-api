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
from kernelci.api.models import Node, Revision
from api.models import PageModel


def test_create_node_endpoint(mock_db_create, mock_publish_cloudevent,
                              test_client):
    """
    Test Case : Test KernelCI API /node endpoint
    Expected Result :
        HTTP Response Code 200 OK
        JSON with created Node object attributes
    """
    revision_data = {
        "tree": "mainline",
        "url": "https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git",
        "branch": "master",
        "commit": "2a987e65025e2b79c6d453b78cb5985ac6e5eb26",
        "describe": "v5.16-rc4-31-g2a987e65025e",
    }

    revision_obj = Revision.parse_obj(revision_data)
    node_obj = Node(
        id="61bda8f2eb1a63d2b7152418",
        kind="checkout",
        name="checkout",
        path=["checkout"],
        group="debug",
        data= {'kernel_revision': revision_obj},
        parent=None,
        state="closing",
        result=None,
    )
    mock_db_create.return_value = node_obj

    request_dict = {
        "name": "checkout",
        "kind": "checkout",
        "path": ["checkout"],
        "data": {"kernel_revision": revision_data},
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
        'id',
        'artifacts',
        'created',
        'data',
        'group',
        'holdoff',
        'kind',
        'name',
        'owner',
        'path',
        'parent',
        'result',
        'state',
        'timeout',
        'updated',
        'user_groups',
    }


def test_get_nodes_by_attributes_endpoint(mock_db_find_by_attributes,
                                          test_client):
    """
    Test Case : Test KernelCI API GET /nodes?attribute_name=attribute_value
    endpoint for the positive path
    Expected Result :
        HTTP Response Code 200 OK
        List with matching Node objects
    """
    node_obj_1 = {
        "id": "61bda8f2eb1a63d2b7152418",
        "kind": "checkout",
        "name": "checkout",
        "path": ["checkout"],
        "data": {
            "kernel_revision": {
                "tree": "mainline",
                "url": "https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git",
                "branch": "master",
                "commit": "2a987e65025e2b79c6d453b78cb5985ac6e5eb26",
                "describe": "v5.16-rc4-31-g2a987e65025e",
            },
        },
        "parent": "61bda8f2eb1a63d2b7152410",
        "state": "closing",
        "result": None,
    }
    node_obj_2 = {
        "id": "61bda8f2eb1a63d2b7152414",
        "kind": "checkout",
        "name": "checkout",
        "path": ["checkout"],
        "data": {
            "kernel_revision": {
                "tree": "mainline",
                "url": "https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git",
                "branch": "master",
                "commit": "2a987e65025e2b79c6d453b78cb5985ac6e5eb45",
                "describe": "v5.16-rc4-31-g2a987e65025e",
            },
        },
        "parent": "61bda8f2eb1a63d2b7152410",
        "state": "closing",
        "result": None,
    }
    mock_db_find_by_attributes.return_value = PageModel(
        items=[node_obj_1, node_obj_2],
        total=2,
        limit=50,
        offset=0
    )

    params = {
        "name": "checkout",
        "data.kernel_revision.tree": "mainline",
        "data.kernel_revision.branch": "master",
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
        mock_db_find_by_attributes,
        test_client):
    """
    Test Case : Test KernelCI API GET /nodes?attribute_name=attribute_value
    endpoint for the node not found
    Expected Result :
        HTTP Response Code 200 OK
        Empty list
    """

    mock_db_find_by_attributes.return_value = PageModel(
        items=[],
        total=0,
        limit=50,
        offset=0
    )

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


def test_get_node_by_id_endpoint(mock_db_find_by_id,
                                 test_client):
    """
    Test Case : Test KernelCI API GET /node/{node_id} endpoint
    for the positive path
    Expected Result :
        HTTP Response Code 200 OK
        JSON with Node object attributes
    """
    revision_obj = Revision(
        tree="mainline",
        url="https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git",
        branch="master",
        commit="2a987e65025e2b79c6d453b78cb5985ac6e5eb26",
        describe="v5.16-rc4-31-g2a987e65025e"
    )
    node_obj = Node(
        id="61bda8f2eb1a63d2b7152418",
        kind="checkout",
        name="checkout",
        path=["checkout"],
        group="blah",
        data = {'kernel_revision': revision_obj},
        parent=None,
        state="closing",
        result=None,
    )
    mock_db_find_by_id.return_value = node_obj

    response = test_client.get("node/61bda8f2eb1a63d2b7152418")
    print("response.json()", response.json())
    assert response.status_code == 200
    assert response.json().keys() == {
        'id',
        'artifacts',
        'created',
        'data',
        'group',
        'holdoff',
        'kind',
        'name',
        'owner',
        'path',
        'parent',
        'result',
        'state',
        'timeout',
        'updated',
        'user_groups',
    }


def test_get_node_by_id_endpoint_empty_response(mock_db_find_by_id,
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


def test_get_all_nodes(mock_db_find_by_attributes,
                       test_client):
    """
    Test Case : Test KernelCI API GET /nodes endpoint for the
    positive path
    Expected Result :
        HTTP Response Code 200 OK
        List of all the node objects.
    """
    node_obj_1 = {
        "id": "61bda8f2eb1a63d2b7152418",
        "kind": "checkout",
        "name": "checkout",
        "path": ["checkout"],
        "data": {
            "kernel_revision": {
                "tree": "mainline",
                "url": "https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git",
                "branch": "master",
                "commit": "2a987e65025e2b79c6d453b78cb5985ac6e5eb26",
                "describe": "v5.16-rc4-31-g2a987e65025e",
                "version": None,
            },
        },
        "parent": None,
        "state": "closing",
        "result": None,
    }

    node_obj_2 = {
        "id": "61bda8f2eb1a63d2b7152414",
        "kind": "checkout",
        "name": "test_node",
        "path": ["checkout", "test_suite", "test_node"],
        "group": None,
        "data": {
            "kernel_revision": {
                "tree": "mainline",
                "url": "https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git",
                "branch": "master",
                "commit": "2a987e65025e2b79c6d453b78cb5985ac6e5eb45",
                "describe": "v5.16-rc4-31-g2a987e65025e",
                "version": None,
            },
        },
        "parent": None,
        "state": "closing",
        "result": None,
    }

    node_obj_3 = {
        "id": "61bda8f2eb1a63d2b7152421",
        "kind": "checkout",
        "name": "test",
        "path": ["checkout", "group", "test"],
        "group": None,
        "data": {
            "kernel_revision": {
                "tree": "baseline",
                "url": "https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git",
                "branch": "master",
                "commit": "2a987e65025e2b79c6d453b78cb5985ac6e5eb26",
                "describe": "v5.16-rc4-31-g2a987e65025e",
                "version": None,
            },
        },
        "parent": None,
        "state": "closing",
        "result": None,
    }

    mock_db_find_by_attributes.return_value = PageModel(
        items=[node_obj_1, node_obj_2, node_obj_3],
        total=3,
        limit=50,
        offset=0
    )

    response = test_client.get("nodes")
    print("response.json()", response.json())
    assert response.status_code == 200
    assert len(response.json()) > 0


def test_get_all_nodes_empty_response(mock_db_find_by_attributes,
                                      test_client):
    """
    Test Case : Test KernelCI API GET /nodes endpoint for the
    negative path
    Expected Result :
        HTTP Response Code 200 OK
        Empty list as no Node object is added.
    """
    mock_db_find_by_attributes.return_value = PageModel(
        items=[],
        total=0,
        limit=50,
        offset=0
    )

    response = test_client.get("nodes")
    print("response.json()", response.json())
    assert response.status_code == 200
    assert response.json().get('total') == 0
