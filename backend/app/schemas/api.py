"""Schemas for API metadata."""

from typing import Literal

from pydantic import BaseModel


class ApiInfoResponse(BaseModel):
    """Metadata returned by the versioned API root."""

    name: str
    version: Literal["v1"]
