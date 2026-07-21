# SPDX-License-Identifier: LGPL-2.1-or-later
#
# Copyright (C) 2026 Collabora Limited

"""Unit tests for KernelCI API telemetry aggregation handlers."""

from unittest.mock import AsyncMock

from kernelci.api.models import TelemetryEvent


def test_stats_groups_and_filters_by_lab_and_device_id(mocker, test_client):
    """Lab and physical device IDs can be used in telemetry statistics."""
    aggregate = AsyncMock(
        return_value=[
            {
                "_id": {
                    "lab": "lava-test",
                    "device_id": "board-01",
                },
                "total": 4,
                "pass": 0,
                "fail": 0,
                "incomplete": 4,
                "skip": 0,
                "infra_error": 4,
            }
        ]
    )
    mocker.patch("api.db.Database.aggregate", side_effect=aggregate)

    response = test_client.get(
        "telemetry/stats",
        params={
            "group_by": "lab,device_id",
            "kind": "job_result",
            "lab": "lava-test",
            "device_id": "board-01",
        },
    )

    assert response.status_code == 200
    assert response.json()[0]["lab"] == "lava-test"
    assert response.json()[0]["device_id"] == "board-01"
    model, pipeline = aggregate.call_args.args
    assert model is TelemetryEvent
    assert pipeline[0]["$match"] == {
        "kind": "job_result",
        "runtime": "lava-test",
        "device_id": "board-01",
    }
    assert pipeline[1]["$group"]["_id"]["lab"] == "$runtime"
    assert pipeline[1]["$group"]["_id"]["device_id"] == "$device_id"


def test_device_anomalies_use_job_results_and_physical_ids(mocker, test_client):
    """Device scope reports physical devices without per-test dilution."""
    aggregate = AsyncMock(
        side_effect=[
            [
                {
                    "_id": {
                        "runtime": "lava-test",
                        "lab": "lava-test",
                        "device_type": "board",
                        "device_id": "board-01",
                    },
                    "total": 3,
                    "pass": 0,
                    "fail": 0,
                    "incomplete": 3,
                    "skip": 0,
                    "infra_error": 3,
                    "infra_rate": 1.0,
                    "fail_rate": 1.0,
                    "last_seen": "2026-07-21T01:24:01.322000",
                    "latest_error_type": "Infrastructure",
                    "latest_error_msg": (
                        "bootloader-commands timed out after 180 seconds"
                    ),
                }
            ],
            [],
        ]
    )
    mocker.patch("api.db.Database.aggregate", side_effect=aggregate)

    response = test_client.get(
        "telemetry/anomalies",
        params={
            "scope": "device",
            "window": "48h",
            "threshold": 1.0,
            "min_total": 3,
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["scope"] == "device"
    assert data["result_anomalies"] == [
        {
            "runtime": "lava-test",
            "lab": "lava-test",
            "device_type": "board",
            "device_id": "board-01",
            "total": 3,
            "pass": 0,
            "fail": 0,
            "incomplete": 3,
            "skip": 0,
            "infra_error": 3,
            "infra_rate": 1.0,
            "fail_rate": 1.0,
            "constant_failure": True,
            "constant_infra_failure": True,
            "last_seen": "2026-07-21T01:24:01.322000",
            "latest_error_type": "Infrastructure",
            "latest_error_msg": (
                "bootloader-commands timed out after 180 seconds"
            ),
        }
    ]

    model, pipeline = aggregate.call_args_list[0].args
    assert model is TelemetryEvent
    assert pipeline[0]["$match"]["kind"] == "job_result"
    assert pipeline[0]["$match"]["device_id"] == {"$nin": [None, ""]}
    assert pipeline[1] == {"$sort": {"ts": -1}}
    assert pipeline[2]["$group"]["_id"]["lab"] == "$runtime"
    assert pipeline[2]["$group"]["_id"]["device_id"] == "$device_id"


def test_stats_rejects_conflicting_lab_and_runtime(mocker, test_client):
    aggregate = AsyncMock(return_value=[])
    mocker.patch("api.db.Database.aggregate", side_effect=aggregate)

    response = test_client.get(
        "telemetry/stats",
        params={
            "group_by": "lab,device_id",
            "lab": "lava-collabora",
            "runtime": "lava-cip",
        },
    )

    assert response.status_code == 400
    aggregate.assert_not_awaited()


def test_device_anomalies_reject_invalid_scope(test_client):
    response = test_client.get("telemetry/anomalies?scope=lab")

    assert response.status_code == 422
