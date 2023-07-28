# SPDX-License-Identifier: LGPL-2.1-or-later
#
# Copyright (C) 2022 Jeny Sadadia
# Author: Jeny Sadadia <jeny.sadadia@gmail.com>
#
# Copyright (C) 2022, 2023 Collabora Limited
# Author: Jeny Sadadia <jeny.sadadia@collabora.com>

# pylint: disable=unused-argument

"""Unit test function for KernelCI API token handler"""

from api.models import User, UserGroup, UserProfile


def test_token_endpoint(mock_db_find_one_by_attributes,
                        mock_init_sub_id, test_client):
    """
    Test Case : Test KernelCI API token endpoint
    Expected Result :
        HTTP Response Code 200 OK
        JSON with 'access_token' and 'token_type' key
    """
    profile = UserProfile(
        username='bob',
        hashed_password='$2b$12$CpJZx5ooxM11bCFXT76/z.o6HWs2sPJy4iP8.'
                        'xCZGmM8jWXUXJZ4K',
        email='bob@kernelci.org',
        groups=[]
    )
    user = User(profile=profile, active=True)
    mock_db_find_one_by_attributes.return_value = user
    response = test_client.post(
        "token",
        headers={
            "Accept": "application/json",
            "Content-Type": "application/x-www-form-urlencoded"
        },
        data={'username': 'bob', 'password': 'hello'}
    )
    print("json", response.json())
    assert response.status_code == 200
    assert ('access_token', 'token_type') == tuple(response.json().keys())


def test_token_endpoint_incorrect_password(mock_db_find_one_by_attributes,
                                           mock_init_sub_id,
                                           test_client):
    """
    Test Case : Test KernelCI API token endpoint for negative path
    Incorrect password should be passed to the endpoint

    Expected Result :
        HTTP Response Code 401 Unauthorized
        JSON with 'detail' key
    """
    profile = UserProfile(
        username='bob',
        hashed_password='$2b$12$CpJZx5ooxM11bCFXT76/z.o6HWs2sPJy4iP8.'
                        'xCZGmM8jWXUXJZ4K',
        email='bob@kernelci.org',
        groups=[])
    user = User(profile=profile, active=True)
    mock_db_find_one_by_attributes.return_value = user

    # Pass incorrect password
    response = test_client.post(
        "token",
        headers={
            "Accept": "application/json",
            "Content-Type": "application/x-www-form-urlencoded"
        },
        data={'username': 'bob', 'password': 'hi'}
    )
    print("response json", response.json())
    assert response.status_code == 401
    assert response.json() == {'detail': 'Incorrect username or password'}


def test_token_endpoint_admin_user(mock_db_find_one_by_attributes,
                                   mock_init_sub_id,
                                   test_client):
    """
    Test Case : Test KernelCI API token endpoint for admin user
    Expected Result :
        HTTP Response Code 200 OK
        JSON with 'access_token' and 'token_type' key
    """
    profile = UserProfile(
        username='test_admin',
        hashed_password='$2b$12$CpJZx5ooxM11bCFXT76/z.o6HWs2sPJy4iP8.'
                        'xCZGmM8jWXUXJZ4K',
        email='test-admin@kernelci.org',
        groups=[UserGroup(name='admin')])
    user = User(profile=profile, active=True)
    mock_db_find_one_by_attributes.return_value = user
    response = test_client.post(
        "token",
        headers={
            "Accept": "application/json",
            "Content-Type": "application/x-www-form-urlencoded"
        },
        data={'username': 'test_admin', 'password': 'hello', 'scope': 'admin'}
    )
    print("json", response.json())
    assert response.status_code == 200
    assert ('access_token', 'token_type') == tuple(response.json().keys())
