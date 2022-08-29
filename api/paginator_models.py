# SPDX-License-Identifier: LGPL-2.1-or-later
#
# Copyright (C) 2022 Collabora Limited
# Author: Jeny Sadadia <jeny.sadadia@collabora.com>

"""Model definitions for pagination"""

from typing import TypeVar
from fastapi import Query
from fastapi_pagination import LimitOffsetPage, LimitOffsetParams
from bson import ObjectId


class CustomLimitOffsetParams(LimitOffsetParams):
    """Model to set custom constraint on limit

    The model is required to redefine limit parameter to remove the number
    validation on maximum value"""

    limit: int = Query(50, ge=1, description="Page size limit")


class PageModel(LimitOffsetPage[TypeVar("T")]):
    """Model for pagination

    This model is required to serialize paginated model data response"""

    __params_type__ = CustomLimitOffsetParams

    class Config:
        """Configuration attributes for PageNode"""
        json_encoders = {
            ObjectId: str,
        }
