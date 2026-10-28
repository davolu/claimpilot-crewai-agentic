# DentiCare Plus — Claim Submission Rules (v2026.1)

These are the rules every claim submitted to DentiCare Plus must satisfy.
Rule IDs are referenced by the Rule Checker agent.

## Required fields (DC-R1 .. DC-R6)

- **DC-R1** Patient full name AND date of birth must both be present and match the member record.
- **DC-R2** Member ID is mandatory, format `DCP-` followed by 8 digits (e.g. DCP-10293847).
- **DC-R3** Treating provider name AND license number are mandatory.
- **DC-R4** Visit date is mandatory and must not be in the future.
- **DC-R5** Every line item must carry a valid CDT procedure code (format `D` + 4 digits).
- **DC-R6** A diagnosis or clinical justification statement is mandatory for any claim over $200.

## Required documents (DC-D1 .. DC-D3)

- **DC-D1** Itemized bill is required for every claim.
- **DC-D2** Clinical notes are required for every claim over $200.
- **DC-D3** A pre-treatment x-ray (or x-ray report) is required for: crowns (D27xx),
  root canals (D33xx), extractions of impacted teeth (D7220–D7241).

## Prior authorization (DC-P1 .. DC-P2)

- **DC-P1** Any single procedure over $800 requires prior authorization BEFORE treatment.
  If treatment already happened without it, the claim must be submitted as a
  prior-authorization exception request with a justification narrative.
- **DC-P2** Orthodontic treatment (D8xxx) always requires prior authorization.

## Coverage limits (DC-C1 .. DC-C4)

- **DC-C1** Routine cleaning (D1110) is covered at most twice per calendar year.
- **DC-C2** Teeth whitening and purely cosmetic procedures (D9972–D9975) are NOT covered. Remove them from the claim or the whole claim is rejected.
- **DC-C3** Crowns (D27xx) are covered at 50% up to a maximum of $600 per tooth.
- **DC-C4** Annual maximum benefit is $2,000 per member.

## Common rejection reasons (from past claims — memory)

1. Missing x-ray on crown claims — the single most frequent rejection.
2. Member ID written in the old format (digits only, no `DCP-` prefix).
3. Cosmetic whitening bundled into a restorative claim (rejects the whole claim).
4. Clinical notes missing on claims just over the $200 threshold.
