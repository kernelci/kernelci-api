# SPDX-License-Identifier: LGPL-2.1-or-later
#
# Copyright (C) 2025 Collabora Limited

"""Unit tests for authorization helpers and user self-update."""

# pylint: disable=duplicate-code

import json

from kernelci.api.models import Node, Revision
from api.main import _user_can_edit_node
from api.models import User, UserGroup
from tests.unit_tests.conftest import BEARER_TOKEN


def _make_user(username="alice", is_superuser=False, groups=None):
    """Return a basic user fixture for authz tests."""
    return User(
        id="65265305c74695807499037f",
        username=username,
        hashed_password="$2b$12$CpJZx5ooxM11bCFXT76/z.o6HWs2sPJy4iP8.xCZGmM8jWXUXJZ4L",
        email=f"{username}@kernelci.org",
        groups=groups or [],
        is_active=True,
        is_superuser=is_superuser,
        is_verified=True,
    )


def _make_node(owner="bob", user_groups=None, runtime=None):
    """Return a basic node fixture for authz tests."""
    revision_obj = Revision(
        tree="mainline",
        url="https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git",
        branch="master",
        commit="2a987e65025e2b79c6d453b78cb5985ac6e5eb26",
        describe="v5.16-rc4-31-g2a987e65025e",
    )
    data = {"kernel_revision": revision_obj}
    if runtime:
        data["runtime"] = runtime
    return Node(
        id="61bda8f2eb1a63d2b7152418",
        kind="checkout",
        name="checkout",
        path=["checkout"],
        group="debug",
        data=data,
        parent=None,
        state="closing",
        result=None,
        treeid="61bda8f2eb1a63d2b7152418",
        owner=owner,
        user_groups=user_groups or [],
    )


def test_user_can_edit_node_as_owner():
    """Owner can edit their own node."""
    user = _make_user(username="bob")
    node = _make_node(owner="bob")
    assert _user_can_edit_node(user, node)


def test_user_can_edit_node_with_matching_group():
    """Matching user group grants edit access."""
    user = _make_user(groups=[UserGroup(name="team-a")])
    node = _make_node(user_groups=["team-a"])
    assert _user_can_edit_node(user, node)


def test_user_can_edit_node_with_runtime_editor_group():
    """Runtime editor group grants edit access."""
    user = _make_user(groups=[UserGroup(name="runtime:lava-collabora:node-editor")])
    node = _make_node(runtime="lava-collabora")
    assert _user_can_edit_node(user, node)


def test_user_can_edit_node_with_runtime_admin_group():
    """Runtime admin group grants edit access."""
    user = _make_user(groups=[UserGroup(name="runtime:lava-collabora:node-admin")])
    node = _make_node(runtime="lava-collabora")
    assert _user_can_edit_node(user, node)


def test_user_can_edit_node_with_global_group():
    """Global edit group grants access."""
    user = _make_user(groups=[UserGroup(name="node:edit:any")])
    node = _make_node()
    assert _user_can_edit_node(user, node)


def test_user_can_edit_node_as_superuser():
    """Superuser can edit any node."""
    user = _make_user(is_superuser=True)
    node = _make_node()
    assert _user_can_edit_node(user, node)


def test_user_cannot_edit_node_without_access():
    """Unrelated user cannot edit when no access applies."""
    user = _make_user(username="alice")
    node = _make_node(owner="bob", user_groups=["team-a"], runtime="lava-collabora")
    assert not _user_can_edit_node(user, node)


def test_user_me_rejects_groups_update(test_client):
    """Self-update rejects user group changes."""
    payload = {"groups": ["node:edit:any"]}
    response = test_client.patch(
        "user/me",
        headers={
            "Accept": "application/json",
            "Authorization": BEARER_TOKEN,
        },
        data=json.dumps(payload),
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "User groups can only be updated by an admin user"
