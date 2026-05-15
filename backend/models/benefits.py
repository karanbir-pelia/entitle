"""
Pydantic models for the static benefits database (federal + state JSON).
Kept permissive (extra='allow') because each program file has slightly
different optional keys.
"""

from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


class MonthlyBenefitRange(BaseModel):
    model_config = ConfigDict(extra="allow")

    min_usd: Optional[float] = None
    max_usd: Optional[float] = None
    typical_usd: Optional[float] = None
    typical_family_4_usd: Optional[float] = None
    note: Optional[str] = None


class ApplicationInfo(BaseModel):
    model_config = ConfigDict(extra="allow")

    method: list[str] = Field(default_factory=list)
    where: Optional[str] = None
    processing_time_days: Optional[Any] = None


class BenefitProgram(BaseModel):
    """One federal or state benefit program."""

    model_config = ConfigDict(extra="allow")

    id: str
    name: str
    full_name: Optional[str] = None
    agency: Optional[str] = None
    category: Optional[str] = None
    description: str = ""
    monthly_benefit_range: Optional[MonthlyBenefitRange] = None
    eligibility_rules: dict[str, Any] = Field(default_factory=dict)
    application: Optional[ApplicationInfo] = None
    required_documents: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)


class FederalPrograms(BaseModel):
    model_config = ConfigDict(extra="allow")
    programs: list[BenefitProgram] = Field(default_factory=list)


class StateProgramsFile(BaseModel):
    """Shape of one backend/data/benefits/state_programs/<XX>.json file."""

    model_config = ConfigDict(extra="allow")

    state: str
    state_name: str
    medicaid_expansion: Optional[bool] = None
    note: Optional[str] = None
    programs: list[BenefitProgram] = Field(default_factory=list)


class StateMetadata(BaseModel):
    """One state's row inside state_metadata.json."""

    model_config = ConfigDict(extra="allow")

    name: str
    medicaid_expansion: Optional[bool] = None
    chip_income_limit_pct_fpl: Optional[float] = None
    tanf_max_monthly_family3: Optional[float] = None
    snap_portal: Optional[str] = None
    medicaid_portal: Optional[str] = None
    benefits_portal: Optional[str] = None


class StateMetadataFile(BaseModel):
    states: dict[str, StateMetadata] = Field(default_factory=dict)
