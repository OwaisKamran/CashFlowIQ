"""
inference_engine.py - FORWARD-CHAINING inference engine (data-driven reasoning).

The recognise-act cycle:

    repeat
        1. MATCH    : find every rule whose conditions are ALL true and that
                      has not fired yet                     -> the CONFLICT SET
        2. RESOLVE  : pick ONE rule from the conflict set:
                         a) highest priority
                         b) then highest specificity (more conditions)
                         c) then knowledge-base order (lower rule ID)
        3. FIRE     : execute its actions (compute / assert / raise problem ...)
                      and record it in the TRACE
    until the conflict set is empty (no rule can add anything new)
          or a rule executes HALT (e.g. R93: essential data is missing)

REFRACTION: each rule fires at most once, so with N rules the engine stops
after at most N cycles -> guaranteed termination (max_cycles is a safety net).

The engine is GENERIC: it knows nothing about cash flow. All domain knowledge
lives in knowledge_base/. That separation is the core idea of expert systems.
"""
import operator
from dataclasses import dataclass, field

from engine.certainty import conclusion_cf
from engine.working_memory import WorkingMemory
from knowledge_base.formulas import FORMULAS
from knowledge_base.problems import PROBLEMS
from knowledge_base.rule_model import (
    NOT_SURE, T, F, Compute, Assert, RaiseProblem, AddStrength, Recommend, FlagMissing, Warn, Halt,
)

OPERATORS = {
    "<": operator.lt, "<=": operator.le, ">": operator.gt, ">=": operator.ge,
    "==": operator.eq, "!=": operator.ne,
    "in": lambda a, b: a in b, "not in": lambda a, b: a not in b,
}


def resolve_value(value, wm, thresholds):
    """Turn T('x') into a threshold value and F('x') into a fact value."""
    if isinstance(value, T):
        return thresholds.get(value.name)
    if isinstance(value, F):
        return wm.get(value.name)
    return value


def evaluate_condition(condition, wm: WorkingMemory, thresholds: dict) -> bool:
    """
    Is one condition true in working memory?
    Shared by the inference engine AND the consultation's ask_if logic, so
    questions and rules use exactly the same condition language.
    """
    op, actual = condition.op, wm.get(condition.fact)
    if op == "unknown":
        return not wm.exists(condition.fact)
    if op == "known":
        return actual is not None
    if op == "missing":
        return actual is None
    if op == "empty":
        return actual is None or actual == 0
    if op == "yes":                             # Yes, or Not sure (its low CF scales the conclusion)
        return actual is True or actual == NOT_SURE
    if op == "not_yes":                         # No or not given - "Not sure" is not a No
        return actual is not True and actual != NOT_SURE
    expected = resolve_value(condition.value, wm, thresholds)
    if actual is None or expected is None:      # None = not computable -> skip
        return False
    return OPERATORS[op](actual, expected)


@dataclass
class TraceStep:
    """One fired rule, as shown in the HOW explanation."""
    cycle: int
    rule_id: str
    group: str
    description: str
    matched: list            # [(condition text, actual value, compared-with value)]
    conclusions: list        # human-readable conclusions
    cf: float                # CF of this rule's conclusion
    conflict_set: list = field(default_factory=list)   # rule IDs that were eligible
    unsure: list = field(default_factory=list)         # premises resting on a "Not sure" answer


class InferenceEngine:
    def __init__(self, rules, thresholds, max_cycles=1000):
        self.rules = list(rules)
        self.thresholds = thresholds
        self.max_cycles = max_cycles
        self._order = {rule.id: i for i, rule in enumerate(self.rules)}
        self.trace: list[TraceStep] = []
        self.fired: set[str] = set()
        self.cycles = 0

    # ------------------------------------------------------------------
    # 1. MATCH
    # ------------------------------------------------------------------
    def _resolve_value(self, value, wm):
        return resolve_value(value, wm, self.thresholds)

    def evaluate(self, condition, wm: WorkingMemory) -> bool:
        return evaluate_condition(condition, wm, self.thresholds)

    def match(self, wm: WorkingMemory) -> list:
        """Return the conflict set: unfired rules whose conditions are all true."""
        return [rule for rule in self.rules
                if rule.id not in self.fired
                and all(self.evaluate(c, wm) for c in rule.conditions)]

    # ------------------------------------------------------------------
    # 2. CONFLICT RESOLUTION
    # ------------------------------------------------------------------
    def resolve(self, conflict_set: list):
        """Priority first, then specificity, then knowledge-base order."""
        return min(conflict_set,
                   key=lambda r: (-r.priority, -r.specificity, self._order[r.id]))

    # ------------------------------------------------------------------
    # 3. FIRE
    # ------------------------------------------------------------------
    def fire(self, rule, wm: WorkingMemory, conflict_set: list):
        # Snapshot of the facts that made this rule match (for explanations).
        # A "Not sure" answer is shown with its reduced CF.
        matched = [(c.describe(),
                    f"Not sure (CF {wm.get_cf(c.fact):.2f})" if wm.get(c.fact) == NOT_SURE
                    else wm.get(c.fact),
                    self._resolve_value(c.value, wm))
                   for c in rule.conditions]
        # Premises that rest only on uncertain answers: a "Not sure" fact, or a
        # problem that was itself raised only from "Not sure" answers (chaining).
        unsure = [c.fact for c in rule.conditions
                  if wm.get(c.fact) == NOT_SURE
                  or (c.fact.startswith("problem:") and c.fact[8:] in wm.problems
                      and wm.problems[c.fact[8:]].uncertain_only)]
        # CF of conclusion = rule CF x weakest premise CF
        premise_cfs = [wm.get_cf(c.fact) for c in rule.conditions
                       if c.op not in ("unknown", "missing", "empty")]
        cf = conclusion_cf(rule.cf, premise_cfs)
        # Classifications/computations are as certain as their premises;
        # the rule's CF expresses confidence in the DIAGNOSIS it makes.
        premise_cf = conclusion_cf(1.0, premise_cfs)
        conclusions = []

        for action in rule.actions:
            if isinstance(action, Compute):
                func, formula_text = FORMULAS[action.formula]
                value = func(wm, self.thresholds)
                wm.add_fact(action.fact, value, premise_cf, rule.id)
                shown = "N/A (not computable)" if value is None else _fmt(value)
                conclusions.append(f"{action.fact} = {shown}   [{formula_text}]")

            elif isinstance(action, Assert):
                wm.add_fact(action.fact, action.value, premise_cf, rule.id)
                conclusions.append(f"{action.fact} = {action.value}")

            elif isinstance(action, RaiseProblem):
                before, after = wm.add_problem(action.key, cf, rule.id, uncertain=bool(unsure))
                title = PROBLEMS[action.key]["title"]
                if before:
                    conclusions.append(f"PROBLEM '{title}' CF {before:.2f} combined with "
                                       f"{cf:.2f} -> {after:.2f}")
                else:
                    conclusions.append(f"PROBLEM '{title}' (CF {cf:.2f})")

            elif isinstance(action, AddStrength):
                wm.add_strength(action.text, rule.id)
                conclusions.append(f"STRENGTH '{action.text}'")

            elif isinstance(action, Recommend):
                wm.add_decision(action.text, action.reason, action.severity, cf, rule.id)
                conclusions.append(f"DECISION '{action.text}'")

            elif isinstance(action, FlagMissing):
                wm.add_missing(action.fact, action.label, rule.id)
                conclusions.append(f"MISSING '{action.label}'")

            elif isinstance(action, Warn):
                wm.add_warning(action.text, rule.id)
                conclusions.append(f"WARNING '{action.text}'")

            elif isinstance(action, Halt):
                wm.halted = True
                conclusions.append("HALT - no further rules will fire")

        self.fired.add(rule.id)
        self.trace.append(TraceStep(
            cycle=self.cycles, rule_id=rule.id, group=rule.group,
            description=rule.description, matched=matched, conclusions=conclusions,
            cf=cf, conflict_set=[r.id for r in conflict_set], unsure=unsure))

    # ------------------------------------------------------------------
    # The recognise-act loop
    # ------------------------------------------------------------------
    def run(self, wm: WorkingMemory) -> list:
        while self.cycles < self.max_cycles:
            conflict_set = self.match(wm)
            if not conflict_set:            # nothing new can be inferred -> stop
                break
            self.cycles += 1
            rule = self.resolve(conflict_set)
            self.fire(rule, wm, conflict_set)
            if wm.halted:                   # a rule executed HALT (e.g. insufficient data)
                break
        else:
            raise RuntimeError("Inference engine exceeded max_cycles (possible loop)")
        return self.trace


def _fmt(value):
    if isinstance(value, float):
        return f"{value:,.2f}"
    if isinstance(value, int):
        return f"{value:,}"
    return str(value)
