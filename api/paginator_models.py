# SPDX-License-Identifier: LGPL-2.1-or-later
#
# Copyright (C) 2022 Collabora Limited
# Author: Jeny Sadadia <jeny.sadadia@collabora.com>

"""Model definitions for pagination"""

from typing import TypeVar
from fastapi_pagination import LimitOffsetPage
from bson import ObjectId


class PageModel(LimitOffsetPage[TypeVar("T")]):
    """Model for pagination

    This model is required to serialize paginated model data response"""

    class Config:
        """Configuration attributes for PageNode"""
        json_encoders = {
            ObjectId: str,
        }
