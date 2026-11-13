"""
diagnosis.py - One-call facade used by the UI and the tests.

    result = diagnose(inputs, thresholds)

It wires the expert-system components together:
    inputs -> WorkingMemory -> InferenceEngine(RULES, thresholds) -> result
and packages problems, ranked decisions, strengths and the trace.
"""
from dataclasses import dataclass, field

from engine.inference_engine import InferenceEngine
from engine.working_memory import WorkingMemory
from knowledge_base import load_thresholds
from knowledge_base.problems import PROBLEMS, SEVERITY_RANK
from knowledge_base.rule_model import NOT_SURE
from knowledge_base.rules import RULES

# Facts shown as ratio cards on the Diagnose page
KEY_METRICS = [
    "current_ratio", "quick_ratio", "cash_ratio", "runway_days",
    "cash_conversion_cycle", "debt_service_ratio", "receivables_to_sales",
    "inventory_to_sales", "net_monthly_cash_flow", "working_capital",
]


@dataclass
class DiagnosisResult:
    inputs: dict
    status: str
    health_score: float | None   # None when data is insufficient
    problems: list            # sorted, most severe first
    decisions: list           # ranked
    strengths: list
    metrics: dict
    trace: list
    wm: WorkingMemory
    rules_fired: int
    cycles: int
    problem_by_key: dict = field(default_factory=dict)
    missing: list = field(default_factory=list)     # [{fact, label, rule_id}]
    warnings: list = field(default_factory=list)    # [{text, rule_id}]

    @property
    def sufficient(self) -> bool:
        return not self.missing


def diagnose(inputs: dict, thresholds: dict | None = None, rules=None) -> DiagnosisResult:
    thresholds = thresholds or load_thresholds()
    # Only pass facts to the engine (business_name is just a label)
    facts = {k: v for k, v in inputs.items() if k != "business_name"}
    wm = WorkingMemory(facts)
    # A "Not sure" answer is uncertain evidence: CF = not_sure_cf instead of 1.0
    for fact in wm.facts.values():
        if fact.value == NOT_SURE:
            fact.cf = thresholds["not_sure_cf"]
    engine = InferenceEngine(rules or RULES, thresholds)
    trace = engine.run(wm)

    # ---------------- problems (most severe, most certain first) ----------------
    problems = []
    for key, record in wm.problems.items():
        entry = PROBLEMS[key]
        problems.append({
            "key": key, "title": entry["title"], "severity": entry["severity"],
            "description": entry["description"], "cf": record.cf,
            "evidence": record.evidence, "decisions": entry["decisions"],
            "unsure": record.uncertain_only,     # raised only from "Not sure" answers
        })
    problems.sort(key=lambda p: (-SEVERITY_RANK[p["severity"]], -p["cf"]))

    # ---------------- decisions (deduplicated + ranked) ----------------
    by_text = {}
    for p in problems:
        for d in p["decisions"]:
            item = by_text.setdefault(d["text"], {
                "text": d["text"], "reason": d["reason"], "severity": p["severity"],
                "cf": p["cf"], "problems": [], "problem_keys": [],
                "rule_ids": [],
            })
            item["problems"].append(p["title"])
            item["problem_keys"].append(p["key"])
            item["rule_ids"] += [e[0] for e in p["evidence"] if e[0] not in item["rule_ids"]]
            # keep the strongest severity / CF that supports this decision
            if (SEVERITY_RANK[p["severity"]], p["cf"]) > (SEVERITY_RANK[item["severity"]], item["cf"]):
                item["severity"], item["cf"] = p["severity"], p["cf"]
    for d in wm.decisions:   # decisions recommended directly by status rules
        by_text[d["text"]] = {"text": d["text"], "reason": d["reason"], "severity": d["severity"],
                              "cf": d["cf"], "problems": [], "problem_keys": [],
                              "rule_ids": [d["rule_id"]]}
    decisions = sorted(by_text.values(), key=lambda d: (-SEVERITY_RANK[d["severity"]], -d["cf"]))
    for rank, d in enumerate(decisions, start=1):
        d["rank"] = rank

    return DiagnosisResult(
        inputs=inputs,
        status=wm.get("status") or "Unknown",
        health_score=wm.get("health_score"),
        problems=problems,
        decisions=decisions,
        strengths=[{"text": t, "rule_id": r} for t, r in wm.strengths.items()],
        metrics={m: wm.get(m) for m in KEY_METRICS},
        trace=trace,
        wm=wm,
        rules_fired=len(engine.fired),
        cycles=engine.cycles,
        problem_by_key={p["key"]: p for p in problems},
        missing=sorted(wm.missing, key=lambda m: int(m["rule_id"][1:])),
        warnings=list(wm.warnings),
    )
