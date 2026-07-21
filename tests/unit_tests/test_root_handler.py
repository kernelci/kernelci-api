# SPDX-License-Identifier: LGPL-2.1-or-later
#
# Copyright (C) 2022 Jeny Sadadia
# Author: Jeny Sadadia <jeny.sadadia@gmail.com>

"""Unit tests for KernelCI API HTML page handlers."""

import pytest
from fastapi import HTTPException

from api.main import _serve_template


def test_root_endpoint(test_client):
    """The root endpoint serves the index as HTML without forced no-cache."""
    response = test_client.get("/")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert "KernelCI API Server" in response.text
    assert "cache-control" not in response.headers


@pytest.mark.parametrize(
    "path, marker",
    [
        ("viewer", "Maestro API Viewer"),
        ("dashboard", "KernelCI Dashboard"),
        ("manage", "Maestro API Manage"),
        ("analytics", "KernelCI Pipeline Analytics"),
        ("stats", "KernelCI API Statistics"),
    ],
)
def test_dynamic_html_pages_disable_caching(test_client, path, marker):
    """Frequently updated HTML tools use one consistent cache policy."""
    response = test_client.get(path)

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert marker in response.text
    assert response.headers["cache-control"] == (
        "no-cache, no-store, must-revalidate"
    )
    assert response.headers["pragma"] == "no-cache"
    assert response.headers["expires"] == "0"


@pytest.mark.parametrize("name", ["invite-email.jinja2", "../index.html"])
def test_template_helper_rejects_non_allowlisted_files(name):
    """The shared helper cannot expose email templates or traverse paths."""
    with pytest.raises(HTTPException) as error:
        _serve_template(name)

    assert error.value.status_code == 404
