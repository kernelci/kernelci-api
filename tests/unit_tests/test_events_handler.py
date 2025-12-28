# SPDX-License-Identifier: LGPL-2.1-or-later
#
# Copyright (C) 2025 Collabora Limited

"""Unit tests for KernelCI API events handler"""

from bson import ObjectId
from kernelci.api.models import EventHistory


def test_get_events_filter_by_id(mock_db_find_by_attributes, test_client):
    """GET /events?id=<id> forwards _id filter and returns items."""
    oid = ObjectId()
    mock_db_find_by_attributes.return_value = [
        {
            "_id": oid,
            "timestamp": "2025-12-11T10:00:00+00:00",
            "data": {"kind": "job", "id": "node1"},
        }
    ]

    resp = test_client.get(f"events?id={str(oid)}")

    assert resp.status_code == 200
    assert resp.json()[0]["id"] == str(oid)
    mock_db_find_by_attributes.assert_awaited_once()
    called_model, called_query = mock_db_find_by_attributes.call_args.args
    assert called_model is EventHistory
    assert called_query["_id"] == oid


def test_get_events_filter_by_ids(mock_db_find_by_attributes, test_client):
    """GET /events?ids=a,b forwards $in filter."""
    oid1, oid2 = ObjectId(), ObjectId()
    mock_db_find_by_attributes.return_value = []

    resp = test_client.get(f"events?ids={oid1},{oid2}")

    assert resp.status_code == 200
    called_model, called_query = mock_db_find_by_attributes.call_args.args
    assert called_model is EventHistory
    assert called_query["_id"]["$in"] == [oid1, oid2]


def test_get_events_rejects_both_id_and_ids(test_client):
    resp = test_client.get("events?id=deadbeefdeadbeefdeadbeef&ids=deadbeefdeadbeefdeadbeef")
    assert resp.status_code == 400


def test_get_events_rejects_invalid_id(test_client):
    resp = test_client.get("events?id=not-an-objectid")
    assert resp.status_code == 400


def test_get_events_filter_by_node_id_alias(mock_db_find_by_attributes, test_client):
    """GET /events?node_id=<id> aliases to data.id filter."""
    node_id = "693af4f5fee8383e92b6b0eb"
    mock_db_find_by_attributes.return_value = []

    resp = test_client.get(f"events?node_id={node_id}")

    assert resp.status_code == 200
    called_model, called_query = mock_db_find_by_attributes.call_args.args
    assert called_model is EventHistory
    assert called_query["data.id"] == node_id


def test_get_events_rejects_node_id_and_data_id(test_client):
    resp = test_client.get(
        "events?node_id=693af4f5fee8383e92b6b0eb&data.id=693af4f5fee8383e92b6b0eb"
    )
    assert resp.status_code == 400
