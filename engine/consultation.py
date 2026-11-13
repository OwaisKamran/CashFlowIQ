"""Consultation wizard logic: which questions to ask, step navigation, validation, WHY."""
from dataclasses import dataclass, field

from engine.explanation import rules_using_fact
from engine.inference_engine import evaluate_condition
from engine.working_memory import WorkingMemory
from knowledge_base.questions import (
    LIABILITY_STEP, NO_ANSWER_ERROR, QUESTIONS, STEPS, questions_in_step,
)
from knowledge_base.rules import LIABILITY_FACTS

REVIEW_STEP = max(STEPS) + 1


@dataclass
class Resolution:
    facts: dict = field(default_factory=dict)     # facts for the inference engine
    shown: set = field(default_factory=set)       # keys of questions asked
    skipped: list = field(default_factory=list)   # questions not needed


def should_ask(question, facts: dict, thresholds: dict) -> bool:
    wm = WorkingMemory(facts)
    return all(evaluate_condition(c, wm, thresholds) for c in question.ask_if)


def resolve(answers: dict, thresholds: dict) -> Resolution:
    """Walk the questions in order; decide shown/skipped; fill defaults."""
    res = Resolution()
    for q in QUESTIONS:
        if should_ask(q, res.facts, thresholds):
            res.shown.add(q.key)
            value = answers.get(q.key)
            if value is None or value == "":
                value = None if q.required else q.default
            res.facts[q.key] = value
        else:
            res.facts[q.key] = q.default
            res.skipped.append(q)
    return res


# steps
def step_is_skipped(step: int, answers: dict, thresholds: dict) -> bool:
    shown = resolve(answers, thresholds).shown
    return not any(q.key in shown for q in questions_in_step(step))


def step_skip_reason(step: int) -> str:
    """Why a whole step is skipped = why its first question is skipped."""
    return questions_in_step(step)[0].skip_text


def next_step(step: int, answers: dict, thresholds: dict) -> tuple:
    """(next step number, [skipped step numbers passed over])."""
    passed = []
    s = step + 1
    while s in STEPS and step_is_skipped(s, answers, thresholds):
        passed.append(s)
        s += 1
    return (s if s in STEPS else REVIEW_STEP), passed


def previous_step(step: int, answers: dict, thresholds: dict) -> int:
    """Previous step that is not skipped (0 = welcome screen)."""
    s = min(step, REVIEW_STEP) - 1
    while s in STEPS and step_is_skipped(s, answers, thresholds):
        s -= 1
    return max(s, 0)


def validate_step(step: int, answers: dict, thresholds: dict) -> tuple:
    """Return (field errors by key, step error or None)."""
    res = resolve(answers, thresholds)
    errors = {}
    for q in questions_in_step(step):
        if q.key not in res.shown:
            continue
        value = answers.get(q.key)
        if q.kind == "text":
            if not str(value or "").strip():
                errors[q.key] = f"Please enter your {q.label.lower()}."
        elif q.kind == "yesno":                   # no default answer
            if value is None:
                errors[q.key] = NO_ANSWER_ERROR
        elif q.required and value is None:
            errors[q.key] = {
                "amount": "Please enter an amount. Enter 0 if you have none.",
                "days": "Please enter the number of days.",
                "percent": "Please enter your profit margin, for example 20.",
            }.get(q.kind, "Please answer this question.")
        elif q.key == "monthly_sales" and value is not None and value <= 0:
            errors[q.key] = "Monthly sales must be more than 0."
    step_error = None
    if (step == LIABILITY_STEP and not res.facts.get("owes_nothing")
            and not any(res.facts.get(k) for k in LIABILITY_FACTS)):
        step_error = ("Please enter at least one amount you owe: suppliers, bank loans or other "
                      "bills - or tick \"I don't owe anything right now\".")
    return errors, step_error


def first_invalid_step(answers: dict, thresholds: dict):
    for step in STEPS:
        errors, step_error = validate_step(step, answers, thresholds)
        if errors or step_error:
            return step
    return None


# "Why are you asking?" - generated from the rule base
_PLAIN_CONDITION = {
    "accounts_receivable": "you told us customers owe you money",
    "accounts_payable": "you told us you owe suppliers money",
    "inventory_value": "you told us you hold stock",
    "short_term_loans": "you told us you have loans or running finance",
    "business_type": "of the type of business you run",
}


def ask_reason(question) -> str:
    """Plain reason first, then the rule-style condition."""
    if not question.ask_if:
        return "This question is always asked."
    plain = " and ".join(_PLAIN_CONDITION.get(c.fact, c.describe()) for c in question.ask_if)
    technical = " and ".join(c.describe() for c in question.ask_if)
    return f"I am asking because {plain} (condition: {technical})."


def because(skip_text: str) -> str:
    """Text after 'because' in a skip reason."""
    return skip_text.split("because ", 1)[1] if "because " in skip_text else skip_text


def why_asking(question, rules) -> dict:
    """Rules that test this fact directly, and rules it feeds through derived facts."""
    by_id = {r.id: r for r in rules}
    direct, indirect = rules_using_fact(question.key, rules)
    return {
        "direct": [(rid, by_id[rid].group, by_id[rid].description) for rid in direct],
        "indirect": indirect,
        "ask_reason": ask_reason(question),
    }
