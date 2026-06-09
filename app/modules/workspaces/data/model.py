# app/modules/workspaces/data/model.py
from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import Field

from app.core.model import BaseMongoModel, make_prefixed_id


class Product(str, Enum):
    """Closed set of products. See UGC/__documents__/workspace.md §2.3.

    Adding a value requires updating the business doc first.
    """
    CL = "CL"
    MMF = "MMF"
    FD = "FD"
    PL = "PL"
    FC = "FC"
    IN = "IN"
    STOCK = "Stock"
    TRANSFER = "Transfer"
    TELCO = "Telco"
    GLOBAL = "Global"
    OTA = "OTA"
    MOVIE = "Movie"


class ArticleStatus(str, Enum):
    NOT_SUBMITTED = "not_submitted"
    WAITING_FOR_REVIEW = "waiting_for_review"
    REVIEWING = "reviewing"
    APPROVED = "approved"
    REJECTED = "rejected"
