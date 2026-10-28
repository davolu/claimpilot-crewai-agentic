"""Pydantic models — every agent returns one of these, so output is always structured."""

from typing import Literal, Optional

from pydantic import BaseModel, Field


class Procedure(BaseModel):
    code: str = Field(description="Billing/procedure code, e.g. a CDT code like D2740")
    description: str = Field(description="Plain-language name of the procedure")
    tooth_or_site: Optional[str] = Field(default=None, description="Tooth number or treatment site if applicable")
    fee: float = Field(description="Amount billed for this procedure")


class ExtractedVisit(BaseModel):
    """What the Extractor agent pulls out of the uploaded documents."""

    patient_name: str
    patient_dob: Optional[str] = None
    member_id: Optional[str] = Field(default=None, description="Insurance member/policy ID")
    insurer_name: Optional[str] = None
    provider_name: Optional[str] = None
    provider_license: Optional[str] = None
    visit_date: Optional[str] = None
    diagnosis: Optional[str] = None
    procedures: list[Procedure] = Field(default_factory=list)
    documents_present: list[str] = Field(
        default_factory=list,
        description="Document types found in the upload, e.g. 'itemized bill', 'clinical notes', 'x-ray report'",
    )
    total_billed: float = 0.0


class Issue(BaseModel):
    """One problem found by the Rule Checker."""

    severity: Literal["blocker", "warning", "info"] = Field(
        description="blocker = claim will be rejected; warning = likely delay; info = worth knowing"
    )
    field: str = Field(description="Which field or document the issue relates to")
    problem: str = Field(description="What is wrong, in one sentence")
    rule_reference: str = Field(description="Which insurer rule this violates")
    suggested_fix: str = Field(description="Concrete action to resolve it")


class RuleCheckResult(BaseModel):
    """Output of the Rule Checker agent."""

    insurer: str
    issues: list[Issue] = Field(default_factory=list)
    estimated_approval_chance: Literal["high", "medium", "low"] = Field(
        description="Chance the claim is approved as-is, before fixes"
    )


class FixAction(BaseModel):
    issue_field: str = Field(description="The field from the issue this fix addresses")
    action_taken: str = Field(description="What was corrected automatically")
    needs_human: bool = Field(description="True if staff must supply something the AI cannot (e.g. a missing x-ray)")
    note_to_staff: Optional[str] = Field(default=None, description="Instruction for billing staff if needs_human")


class FixResult(BaseModel):
    """Output of the Fixer agent."""

    fixes: list[FixAction] = Field(default_factory=list)
    remaining_blockers: list[str] = Field(
        default_factory=list,
        description="Blockers that could NOT be fixed automatically — claim must not be submitted until resolved",
    )


class FinalClaim(BaseModel):
    """The clean, submission-ready claim produced by the Claim Writer."""

    claim_type: Literal["standard", "prior_authorization"] = "standard"
    insurer: str
    patient_name: str
    member_id: str
    provider_name: str
    visit_date: str
    diagnosis: str
    procedures: list[Procedure]
    total_claimed: float
    attachments_required: list[str] = Field(
        default_factory=list, description="Documents that must accompany this claim"
    )
    cover_note: str = Field(description="Short justification narrative addressed to the insurer")
    ready_to_submit: bool = Field(description="False if any blocker remains unresolved")


class ClaimPipelineResult(BaseModel):
    """Everything the UI needs to render the review screen."""

    extracted: ExtractedVisit
    rule_check: RuleCheckResult
    fixes: FixResult
    claim: FinalClaim
