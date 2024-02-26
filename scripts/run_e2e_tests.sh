#!/bin/sh
#
# SPDX-License-Identifier: LGPL-2.1-or-later
#
# Copyright (C) 2023-2024 Collabora Limited
# Author: Jeny Sadadia <jeny.sadadia@collabora.com>

# Script for running API end-to-end tests

docker-compose -f test-docker-compose.yaml build
docker-compose -f test-docker-compose.yaml up -d api db redis storage ssh test
docker-compose -f test-docker-compose.yaml exec -T test pytest -v tests/e2e_tests
docker-compose -f test-docker-compose.yaml down
