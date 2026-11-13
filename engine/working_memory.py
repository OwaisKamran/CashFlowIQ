"""Working memory: the fact base (input facts, derived facts, problems, strengths)."""
from dataclasses import dataclass, field
from typing import Any

from engine.certainty import combine


@dataclass
class Fact:
    name: str
    value: Any
    cf: float = 1.0
    source: str = "user"          # "user" or the rule ID that derived it


@dataclass
class ProblemRecord:
    key: str
    cf: float
    evidence: list = field(default_factory=list)   # (rule_id, rule CF, combined CF)
    uncertain_only: bool = False                   # every rule rested on "Not sure"


class WorkingMemory:
    def __init__(self, inputs: dict | None = None):
        self.facts: dict[str, Fact] = {}
        self.problems: dict[str, ProblemRecord] = {}
        self.strengths: dict[str, str] = {}      # text -> rule ID
        self.decisions: list[dict] = []
        self.missing: list[dict] = []
        self.warnings: list[dict] = []
        self.halted = False
        for name, value in (inputs or {}).items():
            self.add_fact(name, value, 1.0, "user")

    # facts
    def add_fact(self, name, value, cf=1.0, source="user"):
        self.facts[name] = Fact(name, value, cf, source)

    def exists(self, name) -> bool:
        """Fact has been asserted (even if its value is None)."""
        return name in self.facts

    def get(self, name):
        """Value of a fact, or None if missing / not computable."""
        fact = self.facts.get(name)
        return None if fact is None else fact.value

    def get_cf(self, name) -> float:
        fact = self.facts.get(name)
        return 1.0 if fact is None else fact.cf

    # problems
    def add_problem(self, key, cf, rule_id, uncertain=False):
        """Record a problem, combining CFs if it already exists; returns (before, after)."""
        if key in self.problems:
            record = self.problems[key]
            before = record.cf
            record.cf = combine(before, cf)              # MYCIN CF combination
            record.uncertain_only = record.uncertain_only and uncertain
        else:
            before = 0.0
            record = self.problems[key] = ProblemRecord(key, cf, uncertain_only=uncertain)
        record.evidence.append((rule_id, cf, record.cf))
        self.add_fact(f"problem:{key}", True, record.cf, rule_id)   # for chained rules
        return before, record.cf

    # strengths and decisions
    def add_strength(self, text, rule_id):
        self.strengths[text] = rule_id

    def add_decision(self, text, reason, severity, cf, rule_id):
        self.decisions.append({"text": text, "reason": reason, "severity": severity,
                               "cf": cf, "rule_id": rule_id})

    # data sufficiency
    def add_missing(self, fact, label, rule_id):
        self.missing.append({"fact": fact, "label": label, "rule_id": rule_id})
        self.add_fact("missing_facts_count", len(self.missing), 1.0, rule_id)

    def add_warning(self, text, rule_id):
        self.warnings.append({"text": text, "rule_id": rule_id})

    def derived_facts(self):
        return [f for f in self.facts.values()
                if f.source != "user" and not f.name.startswith("problem:")]
