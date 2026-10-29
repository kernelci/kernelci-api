# SPDX-License-Identifier: LGPL-2.1-or-later

"""Unit tests for rejecting state/result changes to done nodes"""

import json

import pytest
from fastapi import HTTPException
from kernelci.api.models import Node

from api.main import NODE_INTEGRITY_CHANNEL, _check_done_node_update
from api.models import User
from tests.unit_tests.conftest import BEARER_TOKEN

NODE_ID = "6ae228345c0836a8c2f041a8"
HEADERS = {"Accept": "application/json", "Authorization": BEARER_TOKEN}


def _make_node(state="done", result="pass", node_id=NODE_ID):
    return Node(
        id=node_id,
        kind="job",
        name="baseline-arm64",
        path=["checkout", "kbuild-gcc-14-arm64", "baseline-arm64"],
        group="baseline-arm64",
        parent="6ae2138e5c0836a8c2eeeac6",
        state=state,
        result=result,
        owner="bob",
        data={"runtime": "sasha-lab", "platform": "jetson-tx1-devkit"},
    )


def _make_user(is_superuser=False):
    return User(
        id="65265305c74695807499037f",
        username="bob",
        hashed_password="hash",
        email="bob@kernelci.org",
        is_active=True,
        is_superuser=is_superuser,
        is_verified=True,
    )


def _node_payload(node, **update):
    payload = json.loads(node.model_dump_json())
    payload.update(update)
    return payload


@pytest.fixture
def mock_integrity_publish(mocker):
    """Capture events published by the done-node guard"""
    pubsub = mocker.AsyncMock()
    mocker.patch("api.main.pubsub", pubsub)
    return pubsub.publish_cloudevent


def test_put_node_rejects_result_flip(
    mock_db_find_by_id, mock_db_update, mock_integrity_publish, test_client
):
    """PUT changing pass to fail on a done node is rejected and reported"""
    node = _make_node()
    mock_db_find_by_id.return_value = node

    response = test_client.put(
        f"node/{NODE_ID}",
        headers=HEADERS,
        json=_node_payload(node, result="fail"),
    )

    assert response.status_code == 409
    mock_db_update.assert_not_called()
    mock_integrity_publish.assert_awaited_once()
    channel, data, _ = mock_integrity_publish.await_args.args
    assert channel == NODE_INTEGRITY_CHANNEL
    assert data["op"] == "done_update_rejected"
    assert data["id"] == NODE_ID
    assert data["result"] == "pass"
    assert data["attempted_result"] == "fail"
    assert data["runtime"] == "sasha-lab"


def test_put_node_allows_same_result(
    mock_db_find_by_id,
    mock_db_update,
    mock_publish_cloudevent,
    mock_integrity_publish,
    test_client,
):
    """PUT keeping the result of a done node (e.g. adding data) is allowed"""
    node = _make_node()
    mock_db_find_by_id.return_value = node
    mock_db_update.return_value = node

    response = test_client.put(
        f"node/{NODE_ID}",
        headers=HEADERS,
        json=_node_payload(node),
    )

    assert response.status_code == 200
    channels = [c.args[0] for c in mock_integrity_publish.await_args_list]
    assert NODE_INTEGRITY_CHANNEL not in channels


def test_put_node_allows_late_result_after_timeout(
    mock_db_find_by_id, mock_db_update, mock_integrity_publish, test_client
):
    """A node closed as incomplete can still get its final result"""
    node = _make_node(result="incomplete")
    mock_db_find_by_id.return_value = node
    mock_db_update.return_value = _make_node(result="fail")

    response = test_client.put(
        f"node/{NODE_ID}",
        headers=HEADERS,
        json=_node_payload(node, result="fail"),
    )

    assert response.status_code == 200
    channels = [c.args[0] for c in mock_integrity_publish.await_args_list]
    assert NODE_INTEGRITY_CHANNEL not in channels


def test_patch_node_rejects_result_flip(
    mock_db_find_by_id, mock_db_update, mock_integrity_publish, test_client
):
    """PATCH changing the result of a done node is rejected"""
    mock_db_find_by_id.return_value = _make_node()

    response = test_client.patch(
        f"node/{NODE_ID}",
        headers=HEADERS,
        json={"result": "fail"},
    )

    assert response.status_code == 409
    mock_db_update.assert_not_called()
    mock_integrity_publish.assert_awaited_once()


def test_put_nodes_rejects_hierarchy_overwrite(
    mocker, mock_db_find_by_id, mock_integrity_publish, test_client
):
    """A hierarchy re-submitted with a different root result is rejected"""
    node = _make_node()
    mock_db_find_by_id.return_value = node
    create_hierarchy = mocker.patch(
        "api.db.Database.create_hierarchy", side_effect=mocker.AsyncMock()
    )

    response = test_client.put(
        f"nodes/{NODE_ID}",
        headers=HEADERS,
        json={
            "node": _node_payload(node, result="fail"),
            "child_nodes": [],
        },
    )

    assert response.status_code == 409
    create_hierarchy.assert_not_called()
    mock_integrity_publish.assert_awaited_once()


@pytest.mark.asyncio
async def test_force_by_admin_is_allowed_and_reported(mock_integrity_publish):
    """An admin can force the change; it is still reported"""
    await _check_done_node_update(
        _make_node(), "done", "fail", _make_user(is_superuser=True), True
    )

    mock_integrity_publish.assert_awaited_once()
    assert (
        mock_integrity_publish.await_args.args[1]["op"] == "done_update_forced"
    )


@pytest.mark.asyncio
async def test_force_by_regular_user_is_rejected(mock_integrity_publish):
    """force=true is ignored for non-admin users"""
    with pytest.raises(HTTPException) as exc:
        await _check_done_node_update(
            _make_node(), "done", "fail", _make_user(), True
        )

    assert exc.value.status_code == 409
    assert (
        mock_integrity_publish.await_args.args[1]["op"]
        == "done_update_rejected"
    )


@pytest.mark.asyncio
async def test_publish_failure_still_rejects(mock_integrity_publish):
    """A failing event publish must not turn the 409 into a 500"""
    mock_integrity_publish.side_effect = RuntimeError("redis down")

    with pytest.raises(HTTPException) as exc:
        await _check_done_node_update(
            _make_node(), "done", "fail", _make_user(), None
        )

    assert exc.value.status_code == 409
