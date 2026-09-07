"""Sessions routes for Atlas OS API.

Note: Session endpoints are included in chat.py under /v1/chat/sessions.
This module exists for API structure consistency.
"""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter()

# Session endpoints are defined in chat.py to avoid circular imports
# and keep related functionality together.
# This module is kept for API structure consistency.