"""
consultation.py - Step-by-step consultation (wizard) logic. No UI code here.

* Which questions are shown is decided by each question's ask_if conditions,
  tested with the SAME evaluate_condition() the inference engine uses.
* A step whose questions are all skipped is skipped as a whole.
* validate_step() blocks "Next" until the step's required answers are given.
* resolve() turns the user's answers into the complete fact set for diagnose():
  skipped or blank optional questions get their default (0 / No). Shown
  Yes/No/Not sure questions have NO default - they must be answered.

Everything is recomputed from the answers every time, so going back and
changing an answer automatically re-decides which later questions are needed.
"""
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
    facts: dict = field(default_factory=dict)     # complete facts for the inference engine
    shown: set = field(default_factory=set)       # keys of questions that are asked
    skipped: list = field(default_factory=list)   # Question objects not needed


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


# ----------------------------------------------------------------------
# Steps
# ----------------------------------------------------------------------
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
    """
    Returns (field_errors {key: message}, step_error or None).
    Required answers must be given; messages are written in plain words.
    """
    res = resolve(answers, thresholds)
    errors = {}
    for q in questions_in_step(step):
        if q.key not in res.shown:
            continue
        value = answers.get(q.key)
        if q.kind == "text":
            if not str(value or "").strip():
                errors[q.key] = f"Please enter your {q.label.lower()}."
        elif q.kind == "yesno":                   # no default: an unanswered question is not a "No"
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


# ----------------------------------------------------------------------
# WHY are you asking?  (generated from the rule base)
# ----------------------------------------------------------------------
_PLAIN_CONDITION = {
    "accounts_receivable": "you told us customers owe you money",
    "accounts_payable": "you told us you owe suppliers money",
    "inventory_value": "you told us you hold stock",
    "short_term_loans": "you told us you have loans or running finance",
    "business_type": "of the type of business you run",
}


def ask_reason(question) -> str:
    """Plain reason first, then the rule-style condition (useful in the viva)."""
    if not question.ask_if:
        return "This question is always asked."
    plain = " and ".join(_PLAIN_CONDITION.get(c.fact, c.describe()) for c in question.ask_if)
    technical = " and ".join(c.describe() for c in question.ask_if)
    return f"I am asking because {plain} (condition: {technical})."


def because(skip_text: str) -> str:
    """'Skipped because you run a service business.' -> 'you run a service business.'"""
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
