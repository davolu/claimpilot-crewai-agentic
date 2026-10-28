"""The ClaimPilot crew: Extractor → Rule Checker → Fixer → Claim Writer.

Each task forces structured output (output_pydantic), so the UI never has to
parse free text. A guardrail on the final task blocks claims that still have
unresolved blockers.
"""

import os
from pathlib import Path
from typing import Any, Tuple

from crewai import Agent, Crew, Process, Task
from crewai.tasks.task_output import TaskOutput

from .models import ExtractedVisit, FinalClaim, FixResult, RuleCheckResult

KNOWLEDGE_DIR = Path(__file__).parent / "knowledge"


def load_insurer_rules(insurer: str = "denticare") -> str:
    return (KNOWLEDGE_DIR / f"{insurer}_rules.md").read_text()


def pick_llm() -> str:
    """Pick a model string from whichever API key is available."""
    if os.getenv("ANTHROPIC_API_KEY"):
        return "anthropic/claude-sonnet-5"
    if os.getenv("OPENAI_API_KEY"):
        return "openai/gpt-4o"
    raise RuntimeError(
        "No API key found. Set ANTHROPIC_API_KEY or OPENAI_API_KEY, "
        "or use demo mode in the app."
    )


def claim_guardrail(output: TaskOutput) -> Tuple[bool, Any]:
    """Guardrail: never let a claim through with missing mandatory fields."""
    claim: FinalClaim = output.pydantic
    missing = [
        f for f in ("patient_name", "member_id", "provider_name", "visit_date")
        if not getattr(claim, f, "").strip()
    ]
    if missing:
        return False, f"Claim is missing mandatory fields: {', '.join(missing)}. Fill them or mark ready_to_submit=false with an explanation in cover_note."
    if not claim.procedures:
        return False, "Claim has no procedures. Re-read the extracted visit and include every billable line item."
    return True, claim


def build_crew(documents_text: str, insurer: str = "denticare") -> Crew:
    llm = pick_llm()
    rules = load_insurer_rules(insurer)

    extractor = Agent(
        role="Medical Document Extractor",
        goal="Pull every billing-relevant fact out of raw clinic documents with zero hallucination",
        backstory=(
            "You are a meticulous medical records specialist. You read bills, clinical "
            "notes, lab results and prescriptions, and extract structured data. You NEVER "
            "invent values — if something is absent from the documents, leave it empty."
        ),
        llm=llm,
        verbose=False,
    )

    rule_checker = Agent(
        role="Insurance Rules Auditor",
        goal="Find every reason this insurer could reject or delay the claim, before the insurer does",
        backstory=(
            "You spent ten years in an insurer's claims-rejection department, so you know "
            "exactly what gets claims bounced. You check extracted claim data against the "
            "insurer's written rules and cite the specific rule ID for every issue."
        ),
        llm=llm,
        verbose=False,
    )

    fixer = Agent(
        role="Claim Repair Specialist",
        goal="Fix every fixable issue automatically; route the rest to billing staff with clear instructions",
        backstory=(
            "You correct what can be corrected from the data at hand (reformatting IDs, "
            "removing non-covered line items, drafting justifications) and you are honest "
            "about what you cannot fix — a missing x-ray cannot be conjured, only requested."
        ),
        llm=llm,
        verbose=False,
    )

    claim_writer = Agent(
        role="Claim Writer",
        goal="Produce a clean, complete, submission-ready claim in the insurer's expected structure",
        backstory=(
            "You assemble the final claim from the extracted data and the applied fixes. "
            "You write a short, factual cover note justifying the treatment. If blockers "
            "remain, you still produce the claim but mark it not ready to submit."
        ),
        llm=llm,
        verbose=False,
    )

    extract_task = Task(
        description=(
            "Extract all billing-relevant data from these clinic documents:\n\n"
            "---DOCUMENTS START---\n{documents}\n---DOCUMENTS END---\n\n"
            "List which document types are present. Do not invent any value that is "
            "not explicitly in the text."
        ),
        expected_output="A structured ExtractedVisit object.",
        agent=extractor,
        output_pydantic=ExtractedVisit,
    )

    check_task = Task(
        description=(
            "Audit the extracted visit data against these insurer rules. Cite the rule ID "
            "(e.g. DC-R2) for every issue. Classify each as blocker, warning or info.\n\n"
            f"---INSURER RULES---\n{rules}\n---END RULES---"
        ),
        expected_output="A RuleCheckResult listing every issue found.",
        agent=rule_checker,
        context=[extract_task],
        output_pydantic=RuleCheckResult,
    )

    fix_task = Task(
        description=(
            "For every issue found, either fix it from the available data (reformat fields, "
            "drop non-covered items, draft missing justifications) or mark it needs_human "
            "with a concrete instruction for billing staff. List unfixable blockers in "
            "remaining_blockers."
        ),
        expected_output="A FixResult describing every action taken.",
        agent=fixer,
        context=[extract_task, check_task],
        output_pydantic=FixResult,
    )

    write_task = Task(
        description=(
            "Assemble the final claim for the insurer using the extracted data with all "
            "fixes applied. Exclude non-covered procedures. Choose claim_type "
            "'prior_authorization' if the rules require pre-approval. Set ready_to_submit "
            "to false if any blocker remains. Write a concise cover note."
        ),
        expected_output="A complete FinalClaim object.",
        agent=claim_writer,
        context=[extract_task, check_task, fix_task],
        output_pydantic=FinalClaim,
        guardrail=claim_guardrail,
    )

    return Crew(
        agents=[extractor, rule_checker, fixer, claim_writer],
        tasks=[extract_task, check_task, fix_task, write_task],
        process=Process.sequential,
        verbose=False,
    )


def run_pipeline(documents_text: str, insurer: str = "denticare"):
    """Run the full crew and return the four structured outputs."""
    from .models import ClaimPipelineResult

    crew = build_crew(documents_text, insurer)
    crew.kickoff(inputs={"documents": documents_text})
    extract_out, check_out, fix_out, write_out = (t.output.pydantic for t in crew.tasks)
    return ClaimPipelineResult(
        extracted=extract_out,
        rule_check=check_out,
        fixes=fix_out,
        claim=write_out,
    )
