"""MYCIN-style certainty factor (CF) arithmetic."""


def conclusion_cf(rule_cf: float, premise_cfs) -> float:
    """Rule CF x weakest premise CF."""
    premise_cfs = list(premise_cfs)
    weakest = min(premise_cfs) if premise_cfs else 1.0
    return round(rule_cf * weakest, 4)


def combine(cf1: float, cf2: float) -> float:
    """MYCIN CF combination for two rules with the same conclusion."""
    if cf1 >= 0 and cf2 >= 0:
        result = cf1 + cf2 * (1 - cf1)
    elif cf1 < 0 and cf2 < 0:
        result = cf1 + cf2 * (1 + cf1)
    else:
        result = (cf1 + cf2) / (1 - min(abs(cf1), abs(cf2)))
    return round(result, 4)
