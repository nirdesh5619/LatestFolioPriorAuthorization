"""Shared decision rules used by both the determination agent (to decide) and the
safety agent (to independently re-derive and cross-check that decision).

Keeping this logic in one place means the two agents can never silently drift
apart on what "not met" actually means for the purpose of denying a request.
"""


def blocking_not_met_criteria(criteria: list[dict]) -> list[dict]:
    """Returns the NOT_MET criteria that should actually block approval.

    Numeric BMI criteria in these policies are typically written as alternative
    qualifying bands (e.g. "BMI >= 40" OR "BMI 35-39.9 with a comorbidity"), not
    a checklist every band must pass. If the patient satisfies any BMI band,
    failing a *different* BMI band is not a real blocker - they simply qualify
    under a different pathway than the one that didn't match.
    """
    bmi_has_met = any("bmi" in c["criterion"].lower() and c["status"] == "MET" for c in criteria)

    blocking = []
    for c in criteria:
        if c["status"] != "NOT_MET":
            continue
        if bmi_has_met and "bmi" in c["criterion"].lower():
            continue
        blocking.append(c)
    return blocking


def expected_determination(criteria: list[dict]) -> str:
    not_met = blocking_not_met_criteria(criteria)
    unknown = [c for c in criteria if c["status"] == "UNKNOWN"]
    met = [c for c in criteria if c["status"] == "MET"]

    if not_met:
        return "denied"
    if unknown:
        return "pended"
    if met:
        return "approved"
    return "pended"
