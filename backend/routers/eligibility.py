"""
Direct eligibility check endpoint — bypasses conversation, takes a structured profile.
Useful for testing and for the Kaggle notebook demo.
"""

import logging
from fastapi import APIRouter
from models.schemas import EligibilityRequest, EligibilityResponse
from services.eligibility_engine import run_eligibility_check

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/eligibility", response_model=EligibilityResponse)
async def check_eligibility(request: EligibilityRequest) -> EligibilityResponse:
    """
    Run a direct eligibility check with a structured user profile.
    Returns all qualifying programs sorted by estimated monthly value.
    """
    # Override state in profile if provided at top level
    profile = request.profile
    if request.state and not profile.state:
        profile.state = request.state

    logger.info(
        "Direct eligibility check: household=%s, income=$%s/mo, state=%s",
        profile.household_size,
        profile.monthly_income_usd,
        profile.state,
    )

    result = await run_eligibility_check(profile)
    return result
