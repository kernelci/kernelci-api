#!/usr/bin/env bash
# SPDX-License-Identifier: LGPL-2.1-or-later
#
# Copyright (C) 2026 Collabora Limited

set -euo pipefail

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
api_dir=$(cd -- "$script_dir/.." && pwd)
stack_dir=$(cd -- "$api_dir/.." && pwd)
core_dir=${KERNELCI_CORE_DIR:-"$stack_dir/kernelci-core"}

python_image=${KERNELCI_TEST_PYTHON_IMAGE:-python:3.12-slim}
redis_image=${KERNELCI_TEST_REDIS_IMAGE:-redis:6.2}
mongo_image=${KERNELCI_TEST_MONGO_IMAGE:-mongo:5.0}
run_id="$$-${RANDOM}"
network="kernelci-api-checks-$run_id"
redis_container="kernelci-api-redis-$run_id"
mongo_container="kernelci-api-mongo-$run_id"

if [[ ! -f "$core_dir/pyproject.toml" ]]; then
    echo "kernelci-core not found at $core_dir" >&2
    echo "Set KERNELCI_CORE_DIR to its checkout path." >&2
    exit 2
fi

if [[ $# -gt 0 ]]; then
    pytest_args=("$@")
else
    pytest_args=(
        -q
        tests/unit_tests/test_db.py
        tests/unit_tests/test_telemetry_handler.py
        tests/unit_tests/test_root_handler.py
    )
fi

cleanup() {
    local exit_code=$?
    trap - EXIT INT TERM
    docker stop "$redis_container" "$mongo_container" >/dev/null 2>&1 || true
    docker network rm "$network" >/dev/null 2>&1 || true
    exit "$exit_code"
}
trap cleanup EXIT INT TERM

echo "Creating isolated test services"
docker network create "$network" >/dev/null
docker run -d --rm \
    --name "$redis_container" \
    --network "$network" \
    --network-alias redis \
    "$redis_image" >/dev/null
docker run -d --rm \
    --name "$mongo_container" \
    --network "$network" \
    --network-alias db \
    "$mongo_image" >/dev/null

echo "Running pytest and Ruff in $python_image"
docker run --rm \
    --network "$network" \
    --volume "$api_dir:/workspace/kernelci-api:ro" \
    --volume "$core_dir:/workspace/kernelci-core:ro" \
    --workdir /tmp \
    --env SECRET_KEY=test-secret \
    --env KCI_INITIAL_PASSWORD=test-password \
    --env PYTEST_ADDOPTS=--asyncio-mode=auto \
    --env PIP_ROOT_USER_ACTION=ignore \
    --env RUFF_CACHE_DIR=/tmp/ruff-cache \
    "$python_image" \
    sh -lc '
        cp -a /workspace/kernelci-api /tmp/kernelci-api
        cp -a /workspace/kernelci-core /tmp/kernelci-core
        pip install --disable-pip-version-check -q \
            "/tmp/kernelci-api[tests]" requests pyyaml jinja2 ruff==0.15.12
        export PYTHONPATH="/tmp/kernelci-core${PYTHONPATH:+:$PYTHONPATH}"
        cd /tmp/kernelci-api
        pytest "$@"
        ruff check \
            api/db.py \
            api/main.py \
            tests/unit_tests/test_db.py \
            tests/unit_tests/test_telemetry_handler.py \
            tests/unit_tests/test_root_handler.py
        ruff format --check \
            api/db.py \
            api/main.py \
            tests/unit_tests/test_db.py \
            tests/unit_tests/test_telemetry_handler.py \
            tests/unit_tests/test_root_handler.py
    ' sh "${pytest_args[@]}"
