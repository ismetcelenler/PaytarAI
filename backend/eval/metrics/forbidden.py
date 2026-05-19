"""Yasakli kelime/ifade kontrolu — yanit must_not_contain listesinden hicbirini icermemeli."""


def must_not_contain(response: str, forbidden: list[str]) -> dict:
    """
    Yanitta yasakli ifade var mi kontrol eder.

    Returns:
        {
            "violations": ["mg/kg", ...],
            "passed": True/False,
        }
    """
    if not forbidden:
        return {"violations": [], "passed": True}

    response_lower = response.lower()
    violations = [term for term in forbidden if term.lower() in response_lower]
    return {"violations": violations, "passed": len(violations) == 0}
