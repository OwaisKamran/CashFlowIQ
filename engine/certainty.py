"""
certainty.py - MYCIN-style certainty factor (CF) arithmetic.

CF ranges from -1 (definitely false) to +1 (definitely true).
Our rules only produce positive CFs, but the full formula is implemented.

1) CF of a rule's conclusion
       CF(conclusion) = CF(rule) x min(CF of the facts the rule matched)
   (a chain is only as strong as its weakest premise)

2) Two rules support the SAME conclusion  (parallel combination)
       both positive : CF = CF1 + CF2 x (1 - CF1)
       both negative : CF = CF1 + CF2 x (1 + CF1)
       mixed signs   : CF = (CF1 + CF2) / (1 - min(|CF1|, |CF2|))

   Example: R28 says "weak credit control" with 0.60, R59 says it with 0.50
            -> 0.60 + 0.50 x (1 - 0.60) = 0.80
   Evidence ADDS UP but can never exceed 1.0 (100%).
"""


def conclusion_cf(rule_cf: float, premise_cfs) -> float:
    premise_cfs = list(premise_cfs)
    weakest = min(premise_cfs) if premise_cfs else 1.0
    return round(rule_cf * weakest, 4)


def combine(cf1: float, cf2: float) -> float:
    if cf1 >= 0 and cf2 >= 0:
        result = cf1 + cf2 * (1 - cf1)
    elif cf1 < 0 and cf2 < 0:
        result = cf1 + cf2 * (1 + cf1)
    else:
        result = (cf1 + cf2) / (1 - min(abs(cf1), abs(cf2)))
    return round(result, 4)
