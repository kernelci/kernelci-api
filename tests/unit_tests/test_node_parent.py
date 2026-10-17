# SPDX-License-Identifier: LGPL-2.1-or-later

"""Parent invariants at the node write boundaries."""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from bson import ObjectId
from fastapi import HTTPException
from kernelci.api.models import Hierarchy, Node

from api import main

NODE_ID = ObjectId("6ac66968a3f195e1aa4bb5ca")
PARENT_ID = ObjectId("6ac62dc4a3f195e1aa48a680")


def make_node(kind="job", **fields):
    return Node(kind=kind, name=kind, path=[kind], **fields)


@pytest.fixture
def writes(mocker):
    database = SimpleNamespace(
        find_by_id=AsyncMock(return_value=make_node(id=PARENT_ID)),
        create=AsyncMock(side_effect=lambda node: node),
        update=AsyncMock(side_effect=lambda node: node),
        create_hierarchy=AsyncMock(side_effect=lambda tree, cls: [tree.node]),
    )
    mocker.patch.object(main, "db", database)
    mocker.patch.object(
        main, "pubsub", SimpleNamespace(publish_cloudevent=AsyncMock())
    )
    return database


@pytest.mark.asyncio
@pytest.mark.parametrize("kind", ["kbuild", "job", "test", "process"])
async def test_create_requires_parent(kind, writes):
    with pytest.raises(HTTPException) as exc:
        await main.post_node(
            make_node(kind), current_user=SimpleNamespace(username="lab")
        )
    assert exc.value.status_code == 400
    assert "Parent is required" in exc.value.detail
    writes.create.assert_not_awaited()
    main.pubsub.publish_cloudevent.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("kind", ["checkout", "regression"])
async def test_legitimate_roots_can_be_created(kind, writes):
    result = await main.post_node(
        make_node(kind), current_user=SimpleNamespace(username="lab")
    )
    assert result.parent is None
    writes.create.assert_awaited_once()


@pytest.mark.asyncio
@pytest.mark.parametrize("kind", ["kbuild", "job", "test", "process"])
async def test_create_with_existing_parent(kind, writes):
    result = await main.post_node(
        make_node(kind, parent=PARENT_ID),
        current_user=SimpleNamespace(username="lab"),
    )
    assert result.parent == PARENT_ID
    writes.find_by_id.assert_awaited_once_with(Node, PARENT_ID)
    writes.create.assert_awaited_once()


@pytest.mark.asyncio
@pytest.mark.parametrize("hierarchy", [False, True])
@pytest.mark.parametrize("parent_fields", [{}, {"parent": None}])
async def test_updates_preserve_missing_or_null_parent(
    hierarchy, parent_fields, writes
):
    stored = make_node(id=NODE_ID, parent=PARENT_ID)
    writes.find_by_id.side_effect = [stored, make_node(id=PARENT_ID)]
    incoming = make_node(**parent_fields)
    if hierarchy:
        tree = Hierarchy(node=incoming, child_nodes=[])
        result = await main.put_nodes(
            str(NODE_ID), tree, user=SimpleNamespace(username="lab")
        )
        assert result[0].parent == PARENT_ID
        assert (
            writes.create_hierarchy.call_args.args[0].node.parent == PARENT_ID
        )
    else:
        result = await main.put_node(str(NODE_ID), incoming, noevent=False)
        assert result.parent == PARENT_ID
        assert writes.update.call_args.args[0].parent == PARENT_ID


@pytest.mark.asyncio
@pytest.mark.parametrize("endpoint", ["create", "update", "hierarchy", "patch"])
async def test_unrecoverable_orphan_rejected_before_writing(endpoint, writes):
    writes.find_by_id.return_value = make_node(id=NODE_ID)
    with pytest.raises(HTTPException) as exc:
        if endpoint == "create":
            await main.post_node(make_node())
        elif endpoint == "update":
            await main.put_node(str(NODE_ID), make_node())
        elif endpoint == "hierarchy":
            await main.put_nodes(
                str(NODE_ID), Hierarchy(node=make_node(), child_nodes=[])
            )
        else:
            await main.patch_node(
                str(NODE_ID), main.NodePatchRequest(result="pass")
            )
    assert exc.value.status_code == 400
    writes.create.assert_not_awaited()
    writes.update.assert_not_awaited()
    writes.create_hierarchy.assert_not_awaited()
    main.pubsub.publish_cloudevent.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("endpoint", ["create", "update", "hierarchy"])
@pytest.mark.parametrize("self_parent", [False, True])
async def test_invalid_parent_rejected(endpoint, self_parent, writes):
    stored = make_node(id=NODE_ID, parent=PARENT_ID)
    writes.find_by_id.side_effect = (
        [None] if endpoint == "create" else [stored, None]
    )
    node = make_node(id=NODE_ID, parent=NODE_ID if self_parent else PARENT_ID)
    with pytest.raises(HTTPException) as exc:
        if endpoint == "create":
            await main.post_node(node)
        elif endpoint == "update":
            await main.put_node(str(NODE_ID), node)
        else:
            await main.put_nodes(
                str(NODE_ID), Hierarchy(node=node, child_nodes=[])
            )
    assert exc.value.status_code == (400 if self_parent else 404)
    writes.create.assert_not_awaited()
    writes.update.assert_not_awaited()
    writes.create_hierarchy.assert_not_awaited()


@pytest.mark.asyncio
async def test_hierarchy_children_get_enclosing_parent(mocker, writes):
    """Exercise actual hierarchy persistence with a parentless child payload."""
    from api.db import Database

    stored = make_node(id=NODE_ID, parent=PARENT_ID)
    documents = {NODE_ID: stored.model_dump(by_alias=True)}

    async def replace_one(query, document):
        documents[query["_id"]] = document
        return SimpleNamespace(matched_count=1)

    async def insert_one(document):
        oid = ObjectId()
        documents[oid] = dict(document, _id=oid)
        return SimpleNamespace(inserted_id=oid)

    collection = SimpleNamespace(
        replace_one=AsyncMock(side_effect=replace_one),
        insert_one=AsyncMock(side_effect=insert_one),
        find_one=AsyncMock(side_effect=lambda oid: documents[oid]),
    )
    database = Database.__new__(Database)
    mocker.patch.object(database, "_get_collection", return_value=collection)
    writes.create_hierarchy.side_effect = database.create_hierarchy
    writes.find_by_id.side_effect = [stored, make_node(id=PARENT_ID)]
    result = await main.put_nodes(
        str(NODE_ID),
        Hierarchy(
            node=make_node(parent=None),
            child_nodes=[Hierarchy(node=make_node("test"), child_nodes=[])],
        ),
        user=SimpleNamespace(username="lab"),
    )
    assert result[0].parent == PARENT_ID
    assert result[1].parent == NODE_ID
    assert documents[NODE_ID]["parent"] == PARENT_ID
