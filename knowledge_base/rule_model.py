"""Rule data classes: IF all conditions are true THEN perform the actions."""
from dataclasses import dataclass
from typing import Any


# values on the right-hand side of a condition
@dataclass(frozen=True)
class T:
    """Reference to a threshold in thresholds.json."""
    name: str

    def __str__(self):
        return self.name


@dataclass(frozen=True)
class F:
    """Reference to another fact in working memory."""
    name: str

    def __str__(self):
        return self.name


# operators: < <= > >= == != in, not in, known, unknown, missing, empty, yes, not_yes
NOT_SURE = "not_sure"      # stored value of a "Not sure" answer (CF = not_sure_cf)


@dataclass(frozen=True)
class Condition:
    fact: str
    op: str
    value: Any = None

    def describe(self) -> str:
        """Readable text for the Knowledge Base table and trace."""
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


# actions (the THEN part)
@dataclass(frozen=True)
class Compute:
    """Derive a fact with a named formula."""
    fact: str
    formula: str

    def describe(self):
        return f"COMPUTE {self.fact}"


@dataclass(frozen=True)
class Assert:
    """Assert a fact, e.g. runway_band = 'critical'."""
    fact: str
    value: Any

    def describe(self):
        return f"{self.fact} = {self.value}"


@dataclass(frozen=True)
class RaiseProblem:
    """Diagnose a problem from the catalog."""
    key: str

    def describe(self):
        return f"PROBLEM: {self.key}"


@dataclass(frozen=True)
class AddStrength:
    """Record a positive finding."""
    text: str

    def describe(self):
        return f"STRENGTH: {self.text}"


@dataclass(frozen=True)
class Recommend:
    """Recommend a decision directly."""
    text: str
    reason: str
    severity: str = "Medium"

    def describe(self):
        return f"DECISION: {self.text}"


@dataclass(frozen=True)
class FlagMissing:
    """Record that an essential fact is missing."""
    fact: str
    label: str

    def describe(self):
        return f"MISSING: {self.label}"


@dataclass(frozen=True)
class Warn:
    """Warn that inputs look inconsistent."""
    text: str

    def describe(self):
        return f"WARNING: {self.text}"


@dataclass(frozen=True)
class Halt:
    """Stop the inference engine."""

    def describe(self):
        return "HALT inference"


@dataclass(frozen=True)
class Rule:
    id: str                 # unique ID, e.g. "R17"
    group: str
    description: str
    conditions: tuple       # all must be true (AND)
    actions: tuple
    cf: float = 1.0         # certainty factor (0..1)
    priority: int = 50      # higher fires first

    @property
    def specificity(self) -> int:
        """Number of conditions (second conflict-resolution key)."""
        return len(self.conditions)

    @property
    def kind(self) -> str:
        """Rule category for the Knowledge Base counts."""
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


# helpers for rules.py
def known(fact: str) -> Condition:
    return Condition(fact, "known")


def yes(fact: str) -> Condition:
    """Symptom answered Yes (also matches Not sure, at lower CF)."""
    return Condition(fact, "yes", True)


def has_problem(key: str) -> Condition:
    """True when this problem has been diagnosed."""
    return Condition(f"problem:{key}", "==", True)
