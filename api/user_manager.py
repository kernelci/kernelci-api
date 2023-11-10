# SPDX-License-Identifier: LGPL-2.1-or-later
#
# Copyright (C) 2023 Collabora Limited
# Author: Jeny Sadadia <jeny.sadadia@collabora.com>

"""User Manager"""

from typing import Optional, Any, Dict
from fastapi import Depends, Request
from fastapi.security import OAuth2PasswordRequestForm
from fastapi_users import BaseUserManager
from fastapi_users.db import (
    BaseUserDatabase,
    BeanieUserDatabase,
    ObjectIDIDMixin,
)
from fastapi_users.password import PasswordHelperProtocol
from beanie import PydanticObjectId
import jinja2
from .user_models import User
from .auth import Settings
from .email_sender import EmailSender


class UserManager(ObjectIDIDMixin, BaseUserManager[User, PydanticObjectId]):
    """User management logic"""
    settings = Settings()
    reset_password_token_secret = settings.secret_key
    verification_token_secret = settings.secret_key

    def __init__(self, user_db: BaseUserDatabase[User, PydanticObjectId],
                 password_helper: PasswordHelperProtocol | None = None):
        self._email_sender = EmailSender()
        self._template_env = jinja2.Environment(
                            loader=jinja2.FileSystemLoader(
                                "./templates/")
                        )
        super().__init__(user_db, password_helper)

    async def on_after_register(self, user: User,
                                request: Optional[Request] = None):
        """Handler to execute after successful user registration"""
        print(f"User {user.id} {user.username} has registered.")

    async def on_after_request_verify(self, user: User, token: str,
                                      request: Optional[Request] = None):
        """Handler to execute after successful verification request"""
        template = self._template_env.get_template("email-verification.jinja2")
        subject = "Email verification Token for KernelCI API account"
        content = template.render(
            username=user.username, token=token
        )
        self._email_sender.create_and_send_email(subject, content, user.email)

    async def on_after_verify(self, user: User,
                              request: Optional[Request] = None):
        """Handler to execute after successful user verification"""
        print(f"Verification successful for user {user.id} {user.username}")
        template = self._template_env.get_template(
            "email-verification-successful.jinja2")
        subject = "Email verification successful for KernelCI API account"
        content = template.render(
            username=user.username,
        )
        self._email_sender.create_and_send_email(subject, content, user.email)

    async def on_after_login(self, user: User,
                             request: Optional[Request] = None):
        """Handler to execute after successful user login"""
        print(f"User {user.id} {user.username} logged in.")

    async def on_after_forgot_password(self, user: User, token: str,
                                       request: Optional[Request] = None):
        """Handler to execute after successful forgot password request"""
        template = self._template_env.get_template("reset-password.jinja2")
        subject = "Reset Password Token for KernelCI API account"
        content = template.render(
            username=user.username, token=token
        )
        self._email_sender.create_and_send_email(subject, content, user.email)

    async def on_after_reset_password(self, user: User,
                                      request: Optional[Request] = None):
        """Handler to execute after successful password reset"""
        print(f"User {user.id} {user.username} has reset their password.")
        template = self._template_env.get_template(
            "reset-password-successful.jinja2")
        subject = "Password reset successful for KernelCI API account"
        content = template.render(
            username=user.username,
        )
        self._email_sender.create_and_send_email(subject, content, user.email)

    async def on_after_update(self, user: User, update_dict: Dict[str, Any],
                              request: Optional[Request] = None):
        """Handler to execute after successful user update"""
        print(f"User {user.id} {user.username} has been updated.")

    async def on_before_delete(self, user: User,
                               request: Optional[Request] = None):
        """Handler to execute before user delete."""
        print(f"User {user.id} {user.username} is going to be deleted.")

    async def on_after_delete(self, user: User,
                              request: Optional[Request] = None):
        """Handler to execute after user delete."""
        print(f"User {user.id} {user.username} was successfully deleted.")

    async def authenticate(
        self, credentials: OAuth2PasswordRequestForm
    ) -> User | None:
        """
        Overload user authentication method `BaseUserManager.authenticate`.
        This is to fix login endpoint to receive `username` instead of `email`.
        """
        user = await User.find_one(User.username == credentials.username)
        if user is None:
            self.password_helper.hash(credentials.password)
            return None

        verified, updated_password_hash = \
            self.password_helper.verify_and_update(
                credentials.password, user.hashed_password
            )
        if not verified:
            return None
        # Update password hash to a more robust one if needed
        if updated_password_hash is not None:
            await self.user_db.update(
                user, {"hashed_password": updated_password_hash}
            )

        return user


async def get_user_db():
    """Database adapter for fastapi-users"""
    yield BeanieUserDatabase(User)


async def get_user_manager(user_db: BeanieUserDatabase = Depends(get_user_db)):
    """Get user manager"""
    yield UserManager(user_db)
