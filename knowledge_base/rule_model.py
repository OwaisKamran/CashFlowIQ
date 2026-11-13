"""
rule_model.py - The *shape* of knowledge (data classes only, no reasoning logic).

A rule is pure DATA:   IF <all conditions are true>  THEN <perform actions>

Keeping rules as data (instead of if/else code) is what makes this an expert
system: the inference engine can read, match, explain and display any rule
without knowing anything about cash flow.
"""
from dataclasses import dataclass
from typing import Any


# ---------------------------------------------------------------------------
# Value references used on the right-hand side of a condition
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class T:
    """Reference to a THRESHOLD in thresholds.json (looked up at match time)."""
    name: str

    def __str__(self):
        return self.name


@dataclass(frozen=True)
class F:
    """Reference to another FACT in working memory (fact-to-fact comparison)."""
    name: str

    def __str__(self):
        return self.name


# ---------------------------------------------------------------------------
# Condition  (the IF part)
# ---------------------------------------------------------------------------
# Supported operators:
#   <  <=  >  >=  ==  !=      compare fact with a constant, T(...) or F(...)
#   in / not in               fact value is (not) one of a tuple of values
#   known                     fact exists and is not None
#   unknown                   fact has NOT been asserted yet (e.g. "no status yet")
#   missing                   fact was not provided (absent or None)  - data checks
#   empty                     fact is missing OR equal to 0           - data checks
#   yes                       Yes/No/Not sure fact is Yes - or Not sure (uncertain evidence)
#   not_yes                   Yes/No fact is No or not given (Not sure is NOT a No)
#
# A "Not sure" answer is stored as the value NOT_SURE with CF = not_sure_cf
# (thresholds.json). A `yes` condition matches it, and the engine's usual
# MYCIN rule  conclusion CF = rule CF x min(premise CFs)  scales the conclusion.
NOT_SURE = "not_sure"


@dataclass(frozen=True)
class Condition:
    fact: str
    op: str
    value: Any = None

    def describe(self) -> str:
        """Plain-English-ish text used in the Knowledge Base table and trace."""
        if self.op == "known":
            return f"{self.fact} is known"
        if self.op == "unknown":
            return f"{self.fact} not yet decided"
        if self.op == "missing":
            return f"{self.fact} is missing"
        if self.op == "empty":
            return f"{self.fact} is missing or 0"
        if self.op == "not_yes":
            return f"{self.fact} is not Yes"
        if self.op == "yes":
            return f"{self.fact} = Yes"
        if self.fact.startswith("problem:"):
            return f"problem '{self.fact[8:]}' diagnosed"
        if self.op == "==" and self.value is True:
            return f"{self.fact} = Yes"
        if self.op in ("in", "not in"):
            options = ", ".join(str(v) for v in self.value)
            return f"{self.fact} {self.op} {{{options}}}"
        return f"{self.fact} {self.op} {self.value}"


# ---------------------------------------------------------------------------
# Actions  (the THEN part)
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Compute:
    """Derive a new fact using a named formula from formulas.py."""
    fact: str
    formula: str

    def describe(self):
        return f"COMPUTE {self.fact}"


@dataclass(frozen=True)
class Assert:
    """Assert a categorical fact, e.g. runway_band = 'critical'."""
    fact: str
    value: Any

    def describe(self):
        return f"{self.fact} = {self.value}"


@dataclass(frozen=True)
class RaiseProblem:
    """Diagnose a problem. Details (severity, decisions) come from problems.py."""
    key: str

    def describe(self):
        return f"PROBLEM: {self.key}"


@dataclass(frozen=True)
class AddStrength:
    """Record a positive finding (adds a small bonus to the health score)."""
    text: str

    def describe(self):
        return f"STRENGTH: {self.text}"


@dataclass(frozen=True)
class Recommend:
    """Recommend a decision directly (used by final-status rules)."""
    text: str
    reason: str
    severity: str = "Medium"

    def describe(self):
        return f"DECISION: {self.text}"


@dataclass(frozen=True)
class FlagMissing:
    """Data sufficiency: record that an essential fact is missing / unusable."""
    fact: str
    label: str

    def describe(self):
        return f"MISSING: {self.label}"


@dataclass(frozen=True)
class Warn:
    """Sanity check: warn the user that inputs look inconsistent."""
    text: str

    def describe(self):
        return f"WARNING: {self.text}"


@dataclass(frozen=True)
class Halt:
    """Stop the inference engine (no further rules fire)."""

    def describe(self):
        return "HALT inference"


# ---------------------------------------------------------------------------
# Rule
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Rule:
    id: str                 # unique ID, e.g. "R17"
    group: str              # knowledge group, e.g. "Cash Runway"
    description: str        # plain-English explanation of the rule
    conditions: tuple       # tuple[Condition]  - ALL must be true (AND)
    actions: tuple          # tuple[action]     - performed when the rule fires
    cf: float = 1.0         # certainty factor of the expert (0..1)
    priority: int = 50      # higher fires first during conflict resolution

    @property
    def specificity(self) -> int:
        """More conditions = more specific rule (2nd conflict-resolution key)."""
        return len(self.conditions)

    @property
    def kind(self) -> str:
        """Category of rule, used for counting on the Knowledge Base page."""
        if any(isinstance(a, (FlagMissing, Warn, Halt)) for a in self.actions) or \
                any(isinstance(a, Assert) and a.fact == "data_sufficient" for a in self.actions):
            return "DATA CHECK"
        if any(isinstance(a, Compute) for a in self.actions):
            return "COMPUTE"
        if any(isinstance(a, (RaiseProblem, Recommend)) for a in self.actions):
            return "DECISION"
        if any(isinstance(a, Assert) and a.fact == "status" for a in self.actions):
            return "STATUS"
        return "CLASSIFY"

    def if_text(self) -> str:
        return "  AND  ".join(c.describe() for c in self.conditions)

    def then_text(self) -> str:
        return "  ;  ".join(a.describe() for a in self.actions)


# ---------------------------------------------------------------------------
# Small helpers that make rules.py read like English
# ---------------------------------------------------------------------------
def known(fact: str) -> Condition:
    return Condition(fact, "known")


def yes(fact: str) -> Condition:
    """A symptom answered 'Yes' - also matches 'Not sure', at reduced certainty."""
    return Condition(fact, "yes", True)


def has_problem(key: str) -> Condition:
    """True when a problem with this catalog key has been diagnosed."""
    return Condition(f"problem:{key}", "==", True)
