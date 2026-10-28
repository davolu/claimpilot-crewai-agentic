"""Demo mode — realistic canned pipeline output so the UI can be used end-to-end
without an API key. Mirrors exactly what the real crew returns for the bundled
sample documents."""

import time

from .models import (
    ClaimPipelineResult,
    ExtractedVisit,
    FinalClaim,
    FixAction,
    FixResult,
    Issue,
    Procedure,
    RuleCheckResult,
)


def run_demo_pipeline(documents_text: str, progress_callback=None) -> ClaimPipelineResult:
    """Return canned results, pausing briefly between stages so the UI shows progress."""

    def step(name: str):
        if progress_callback:
            progress_callback(name)
        time.sleep(1.2)

    step("Extractor reading documents…")
    extracted = ExtractedVisit(
        patient_name="Amara Okafor",
        patient_dob="1988-03-14",
        member_id="10293847",  # old format — missing DCP- prefix
        insurer_name="DentiCare Plus",
        provider_name="Dr. Lena Vasquez, DDS",
        provider_license="DDS-44721",
        visit_date="2026-10-21",
        diagnosis="Fractured crown on tooth 19 following trauma; secondary caries tooth 30.",
        procedures=[
            Procedure(code="D2740", description="Crown — porcelain/ceramic", tooth_or_site="19", fee=950.0),
            Procedure(code="D2391", description="Resin composite filling, one surface", tooth_or_site="30", fee=210.0),
            Procedure(code="D9972", description="External bleaching, per arch", tooth_or_site=None, fee=180.0),
        ],
        documents_present=["itemized bill", "clinical notes"],
        total_billed=1340.0,
    )

    step("Rule Checker auditing against DentiCare Plus rules…")
    rule_check = RuleCheckResult(
        insurer="DentiCare Plus",
        estimated_approval_chance="low",
        issues=[
            Issue(
                severity="blocker",
                field="member_id",
                problem="Member ID '10293847' is in the old digits-only format.",
                rule_reference="DC-R2",
                suggested_fix="Reformat to DCP-10293847.",
            ),
            Issue(
                severity="blocker",
                field="documents: x-ray",
                problem="Crown procedure D2740 requires a pre-treatment x-ray; none was uploaded.",
                rule_reference="DC-D3",
                suggested_fix="Attach the pre-treatment x-ray or x-ray report for tooth 19.",
            ),
            Issue(
                severity="blocker",
                field="procedures: D9972",
                problem="Teeth whitening (D9972) is cosmetic and not covered — it will reject the whole claim.",
                rule_reference="DC-C2",
                suggested_fix="Remove D9972 from the claim; bill the patient directly.",
            ),
            Issue(
                severity="warning",
                field="procedures: D2740",
                problem="Crown fee $950 exceeds the $800 prior-authorization threshold and treatment already happened.",
                rule_reference="DC-P1",
                suggested_fix="Submit as a prior-authorization exception request with a trauma justification narrative.",
            ),
            Issue(
                severity="info",
                field="procedures: D2740",
                problem="Crowns are reimbursed at 50% up to $600 per tooth — expect $475 reimbursement, not $950.",
                rule_reference="DC-C3",
                suggested_fix="Set patient expectation on out-of-pocket portion.",
            ),
        ],
    )

    step("Fixer repairing what it can…")
    fixes = FixResult(
        fixes=[
            FixAction(
                issue_field="member_id",
                action_taken="Reformatted member ID to DCP-10293847.",
                needs_human=False,
            ),
            FixAction(
                issue_field="procedures: D9972",
                action_taken="Removed non-covered whitening line ($180) from the claim; flagged for direct patient billing.",
                needs_human=False,
            ),
            FixAction(
                issue_field="procedures: D2740",
                action_taken="Drafted prior-authorization exception narrative citing dental trauma.",
                needs_human=False,
            ),
            FixAction(
                issue_field="documents: x-ray",
                action_taken="Cannot be fixed automatically.",
                needs_human=True,
                note_to_staff="Request the pre-treatment x-ray of tooth 19 from Dr. Vasquez's office and attach it before submitting.",
            ),
        ],
        remaining_blockers=["Pre-treatment x-ray for tooth 19 (DC-D3) still missing."],
    )

    step("Claim Writer assembling the final claim…")
    claim = FinalClaim(
        claim_type="prior_authorization",
        insurer="DentiCare Plus",
        patient_name="Amara Okafor",
        member_id="DCP-10293847",
        provider_name="Dr. Lena Vasquez, DDS (License DDS-44721)",
        visit_date="2026-10-21",
        diagnosis="Fractured crown on tooth 19 following trauma; secondary caries tooth 30.",
        procedures=[
            Procedure(code="D2740", description="Crown — porcelain/ceramic", tooth_or_site="19", fee=950.0),
            Procedure(code="D2391", description="Resin composite filling, one surface", tooth_or_site="30", fee=210.0),
        ],
        total_claimed=1160.0,
        attachments_required=["Itemized bill", "Clinical notes", "Pre-treatment x-ray, tooth 19 (PENDING)"],
        cover_note=(
            "Prior-authorization exception request: patient presented 2026-10-21 with a "
            "fractured crown on tooth 19 following acute trauma, requiring immediate "
            "restoration (D2740). Treatment could not await standard pre-approval. A "
            "single-surface composite restoration (D2391, tooth 30) addressed secondary "
            "caries found on examination. Cosmetic services have been excluded from this "
            "claim. Pre-treatment radiograph to follow as attachment."
        ),
        ready_to_submit=False,  # blocked until the x-ray is attached
    )

    return ClaimPipelineResult(extracted=extracted, rule_check=rule_check, fixes=fixes, claim=claim)
