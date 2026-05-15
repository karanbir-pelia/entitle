"""
Pydantic request/response models for the Entitle API.
"""

from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


class Language(str, Enum):
    en = "en"
    es = "es"
    zh = "zh"
    vi = "vi"
    ar = "ar"
    fr = "fr"
    pt = "pt"
    ko = "ko"
    ru = "ru"


class CitizenshipStatus(str, Enum):
    citizen = "citizen"
    permanent_resident = "permanent_resident"
    other = "other"
    unknown = "unknown"


class EmploymentStatus(str, Enum):
    employed = "employed"
    unemployed = "unemployed"
    part_time = "part_time"
    self_employed = "self_employed"
    retired = "retired"
    unknown = "unknown"


class HousingStatus(str, Enum):
    renter = "renter"
    owner = "owner"
    homeless = "homeless"
    other = "other"
    unknown = "unknown"


class UserProfile(BaseModel):
    """Structured household profile extracted from the user's conversation."""

    model_config = ConfigDict(extra="ignore")

    household_size: Optional[int] = None
    adults: Optional[int] = None
    children: Optional[int] = None

    monthly_income_usd: Optional[float] = None
    annual_income_usd: Optional[float] = None

    state: Optional[str] = None
    zip_code: Optional[str] = None

    has_elderly: Optional[bool] = None
    has_disabled: Optional[bool] = None
    has_pregnant: Optional[bool] = None
    has_infant: Optional[bool] = None
    has_children_under_5: Optional[bool] = None

    citizenship_status: Optional[str] = None
    employment_status: Optional[str] = None
    has_health_insurance: Optional[bool] = None
    housing_status: Optional[str] = None
    utility_bills: Optional[bool] = None
    is_student: Optional[bool] = None
    veteran: Optional[bool] = None

    currently_on_snap: Optional[bool] = None
    currently_on_medicaid: Optional[bool] = None

    profile_complete: bool = False


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    message: str
    history: list[ChatMessage] = Field(default_factory=list)
    language: Language = Language.en
    session_id: Optional[str] = None
    profile: Optional[dict[str, Any]] = None


class ChatResponse(BaseModel):
    reply: str
    benefits_found: Optional[list[dict[str, Any]]] = None
    next_action: str = "ask_more"
    profile: Optional[dict[str, Any]] = None


class EligibilityRequest(BaseModel):
    profile: UserProfile
    state: Optional[str] = None


class EligibilityResult(BaseModel):
    """One qualifying program in the eligibility response."""

    model_config = ConfigDict(extra="ignore")

    program_id: str
    program_name: str
    likely_eligible: bool = True
    confidence: str = "medium"
    estimated_monthly_value_usd: Optional[float] = None
    value_period: str = "monthly"
    reason: str = ""
    next_steps: list[str] = Field(default_factory=list)
    required_documents: list[str] = Field(default_factory=list)
    apply_url: Optional[str] = None
    category: Optional[str] = None


class EligibilityResponse(BaseModel):
    results: list[EligibilityResult] = Field(default_factory=list)
    total_estimated_monthly_usd: float = 0.0
    disclaimer: str = (
        "Entitle provides estimates and preparation help only. "
        "Official eligibility decisions are made by the relevant agencies."
    )


class DocumentResponse(BaseModel):
    """Plain-language explanation of an uploaded government document."""

    model_config = ConfigDict(extra="ignore")

    document_type: str
    plain_language_summary: str
    action_required: Optional[str] = None
    deadline: Optional[str] = None
    appeal_possible: Optional[bool] = None
    next_steps: list[str] = Field(default_factory=list)
