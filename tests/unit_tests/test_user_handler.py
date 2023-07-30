# SPDX-License-Identifier: LGPL-2.1-or-later
#
# Copyright (C) 2022, 2023 Collabora Limited
# Author: Jeny Sadadia <jeny.sadadia@collabora.com>

# pylint: disable=unused-argument

"""Unit test function for KernelCI API user handler"""

import json

from tests.unit_tests.conftest import (
    ADMIN_BEARER_TOKEN,
    BEARER_TOKEN,
)
from api.models import User, UserGroup, UserProfile


def test_create_regular_user(mock_init_sub_id, mock_get_current_admin_user,
                             mock_db_create, mock_publish_cloudevent,
                             test_client):
    """
    Test Case : Test KernelCI API /user endpoint to create regular user
    when requested with admin user's bearer token
    Expected Result :
        HTTP Response Code 200 OK
        JSON with 'id', 'username', 'hashed_password', and
        'active' keys
    """
    profile = UserProfile(username='test', hashed_password="$2b$12$Whi.dpTC.\
HR5UHMdMFQeOe1eD4oXaP08oW7ogYqyiNziZYNdUHs8i", email='test@kernelci.org')
    user = User(profile=profile, active=True)
    mock_db_create.return_value = user

    response = test_client.post(
        "user/test?email=test@kernelci.org",
        headers={
            "Accept": "application/json",
            "Authorization": ADMIN_BEARER_TOKEN
        },
        data=json.dumps({"password": "test"})
    )
    print(response.json())
    assert response.status_code == 200
    assert ('id', 'active', 'profile') == tuple(response.json().keys())
    assert ('username', 'hashed_password',
            'groups', 'email') == tuple(response.json()['profile'].keys())


def test_create_admin_user(  # pylint: disable=too-many-arguments
                           mock_init_sub_id,
                           mock_get_current_admin_user,
                           mock_db_create, mock_publish_cloudevent,
                           test_client, mock_db_find_one):
    """
    Test Case : Test KernelCI API /user endpoint to create admin user
    when requested with admin user's bearer token
    Expected Result :
        HTTP Response Code 200 OK
        JSON with 'id', 'username', 'hashed_password', and
        'active' keys
    """
    profile = UserProfile(
        username='test_admin',
        hashed_password="$2b$12$Whi.dpTC.HR5UHMdMFQeOe1eD4oXaP08o\
W7ogYqyiNziZYNdUHs8i",
        email='test-admin@kernelci.org',
        groups=[UserGroup(name='admin')])
    user = User(profile=profile, active=True)
    mock_db_create.return_value = user
    mock_db_find_one.return_value = UserGroup(name='admin')

    response = test_client.post(
        "user/test_admin?groups=admin&email=test-admin@kernelci.org",
        headers={
            "Accept": "application/json",
            "Authorization": ADMIN_BEARER_TOKEN
        },
        data=json.dumps({"password": "test"})
    )
    print(response.json())
    assert response.status_code == 200
    assert ('id', 'active', 'profile') == tuple(response.json().keys())
    assert ('username', 'hashed_password',
            'groups', 'email') == tuple(response.json()['profile'].keys())


def test_create_user_endpoint_negative(mock_init_sub_id, mock_get_current_user,
                                       mock_publish_cloudevent, test_client):
    """
    Test Case : Test KernelCI API /user endpoint when requested
    with regular user's bearer token
    Expected Result :
        HTTP Response Code 401 Unauthorized
        JSON with 'detail' key denoting 'Access denied' error
    """
    mock_get_current_user.return_value = None, "Access denied"

    response = test_client.post(
        "user/test",
        headers={
            "Accept": "application/json",
            "Authorization": BEARER_TOKEN
        },
        data=json.dumps({"password": "test"})
    )
    print(response.json())
    assert response.status_code == 401
    assert response.json() == {'detail': 'Access denied'}


def test_create_user_with_group(  # pylint: disable=too-many-arguments
                           mock_init_sub_id,
                           mock_get_current_admin_user,
                           mock_db_create, mock_publish_cloudevent,
                           test_client, mock_db_find_one):
    """
    Test Case : Test KernelCI API /user endpoint to create a user with a
    user group
    Expected Result :
        HTTP Response Code 200 OK
        JSON with 'id', 'username', 'hashed_password'
        'active', and 'groups' keys
    """
    profile = UserProfile(
        username='test_admin',
        hashed_password="$2b$12$Whi.dpTC.HR5UHMdMFQeOe1eD4oXaP08oW7\
ogYqyiNziZYNdUHs8i",
        email='test-admin@kernelci.org',
        groups=[UserGroup(name='kernelci')])
    user = User(profile=profile, active=True)
    mock_db_create.return_value = user
    mock_db_find_one.return_value = UserGroup(name='kernelci')

    response = test_client.post(
        "user/test_admin?groups=kernelci&email=test-admin@kernelci.org",
        headers={
            "Accept": "application/json",
            "Authorization": ADMIN_BEARER_TOKEN
        },
        data=json.dumps({"password": "test"})
    )
    print(response.json())
    assert response.status_code == 200
    assert ('id', 'active', 'profile') == tuple(response.json().keys())
    assert ('username', 'hashed_password',
            'groups', 'email') == tuple(response.json()['profile'].keys())


def test_get_user_by_id_endpoint(mock_get_current_admin_user, mock_db_find_by_id,
                                 mock_init_sub_id, test_client):
    """
    Test Case : Test KernelCI API GET /user/{user_id} endpoint with admin
    token
    Expected Result :
        HTTP Response Code 200 OK
        JSON with User object attributes
    """
    user_obj = User(
            id='61bda8f2eb1a63d2b7152418',
            profile=UserProfile(username='test', hashed_password="$2b$12$Whi.dpTC.\
HR5UHMdMFQeOe1eD4oXaP08oW7ogYqyiNziZYNdUHs8i", email='test@kernelci.org'),
            active=True
        )
    mock_db_find_by_id.return_value = user_obj

    response = test_client.get(
        "user/61bda8f2eb1a63d2b7152418",
        headers={
            "Accept": "application/json",
            "Authorization": ADMIN_BEARER_TOKEN
        })
    print("response.json()", response.json())
    assert response.status_code == 200
    assert response.json().keys() == {
        'id',
        'active',
        'profile'
    }
    assert ('username', 'groups',
            'email') == tuple(response.json()['profile'].keys())
