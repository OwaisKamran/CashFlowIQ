"""Explanation facility: HOW (rule trace), WHY (questions, decisions) and plain summaries."""
from knowledge_base.formulas import FORMULAS
from knowledge_base.problems import PROBLEMS
from knowledge_base.rule_model import NOT_SURE, Compute


def _fmt(value):
    if value is None:
        return "N/A"
    if isinstance(value, bool):
        return "Yes" if value else "No"
    if isinstance(value, float):
        return f"{value:,.2f}"
    if isinstance(value, int):
        return f"{value:,}"
    if value == NOT_SURE:
        return "Not sure"
    return str(value)


# HOW
def how_table(trace) -> list:
    """One row per fired rule."""
    return [{
        "Step": step.cycle,
        "Rule": step.rule_id,
        "Group": step.group,
        "Because (matched facts)": "; ".join(
            f"{text} [{_fmt(actual)}" + (f" vs {_fmt(cmp)}]" if cmp is not None and cmp is not True else "]")
            for text, actual, cmp in step.matched),
        "Concluded": " | ".join(step.conclusions),
        "CF": round(step.cf, 2),
        "Eligible rules": len(step.conflict_set),
    } for step in trace]


def how_text(trace) -> str:
    """Plain-text trace for download."""
    lines = []
    for step in trace:
        lines.append(f"Step {step.cycle}: {step.rule_id} fired - {step.description}")
        for text, actual, cmp in step.matched:
            lines.append(f"     IF {text}   (value: {_fmt(actual)}"
                         + (f", compared with {_fmt(cmp)})" if cmp not in (None, True) else ")"))
        for c in step.conclusions:
            lines.append(f"     THEN {c}")
        lines.append(f"     conflict set had {len(step.conflict_set)} rule(s): "
                     f"{', '.join(step.conflict_set)}")
    return "\n".join(lines)


# WHY a question is asked
def rules_using_fact(fact: str, rules) -> tuple:
    """(direct, indirect) IDs of rules using a fact, indirect = via computed facts."""
    direct = [r.id for r in rules if any(c.fact == fact for c in r.conditions)]
    seen_facts, frontier, indirect = {fact}, [fact], []
    while frontier:
        current = frontier.pop()
        for rule in rules:
            if any(c.fact == current for c in rule.conditions):
                if current != fact and rule.id not in direct and rule.id not in indirect:
                    indirect.append(rule.id)
                for action in rule.actions:
                    if isinstance(action, Compute) and action.fact not in seen_facts:
                        seen_facts.add(action.fact)
                        frontier.append(action.fact)
    return direct, sorted(indirect, key=lambda x: int(x[1:]))


# WHY a decision / problem
def why_problem(problem: dict, trace) -> str:
    steps = {s.rule_id: s for s in trace}
    lines = [f"**{problem['title']}** ({problem['severity']}, confidence {problem['cf']:.0%})",
             f"_{problem['description']}_", ""]
    lines.append("Supported by:")
    for rule_id, rule_cf, combined in problem["evidence"]:
        step = steps.get(rule_id)
        because = "; ".join(t if a is True and cmp is True else f"{t} (= {_fmt(a)})"
                            for t, a, cmp in step.matched) if step else ""
        lines.append(f"- **{rule_id}** (CF {rule_cf:.2f}) because {because}")
        if step and step.unsure:
            lines.append("  - You answered *Not sure*, so this rule's CF was reduced "
                         "(rule CF x min(CF of matched facts)).")
    if len(problem["evidence"]) > 1:
        cfs = [e[1] for e in problem["evidence"]]
        lines.append("")
        lines.append(f"Several rules agree, so their certainty factors were combined "
                     f"(MYCIN: CF1 + CF2 x (1 - CF1)): {' & '.join(f'{c:.2f}' for c in cfs)} "
                     f"-> **{problem['cf']:.2f}**")
    return "\n".join(lines)


def why_decision(decision: dict, result) -> str:
    lines = [f"**Action:** {decision['text']}", "", f"**Reason:** {decision['reason']}", ""]
    if decision.get("problem_keys"):
        for key in decision["problem_keys"]:
            lines.append(why_problem(result.problem_by_key[key], result.trace))
            lines.append("")
    else:
        lines.append(f"Recommended directly by rule **{decision['rule_ids'][0]}** "
                     f"because the final status is **{result.status}**.")
    return "\n".join(lines)


# plain-English summary
STATUS_SENTENCE = {
    "Healthy": "{name} is HEALTHY: no serious cash-flow problems were found.",
    "Watch": "{name} is on WATCH: there is no emergency, but some issues need attention.",
    "Risky": "{name} is RISKY: there are serious cash problems that need action soon.",
    "Crisis": "{name} is in CRISIS: cash could run out very soon without urgent action.",
}


# already covered by the "your cash covers N days" sentence
CASH_PROBLEMS = {"cash_runs_out_within_month", "short_cash_runway", "imminent_cash_crisis",
                 "monthly_cash_burn", "thin_cash_buffer"}


class _SafeFacts(dict):
    def __missing__(self, key):
        return "?"


def _rs(value):
    return f"Rs {abs(value):,.0f}"


def summary_facts(wm) -> dict:
    """Facts formatted for the CONCERNS templates."""
    g = wm.get
    out = _SafeFacts()
    for key, fmt in (("collection_days", "{:.0f}"), ("payment_days", "{:.0f}"),
                     ("stock_days", "{:.0f}"), ("runway_days", "{:.0f}"),
                     ("cash_conversion_cycle", "{:.0f}"), ("receivables_to_sales", "{:.1f}"),
                     ("inventory_to_sales", "{:.1f}")):
        if g(key) is not None:
            out[key] = fmt.format(g(key))
    out["ccc"] = out.get("cash_conversion_cycle", "?")
    out["rec_months"] = out.get("receivables_to_sales", "?")
    out["inv_months"] = out.get("inventory_to_sales", "?")
    if g("cash_ratio") is not None:
        out["cash_ratio_pct"] = f"{g('cash_ratio'):.0%}"
    if g("debt_service_ratio") is not None:
        out["dsr_pct"] = f"{g('debt_service_ratio'):.0%}"
    if g("net_monthly_cash_flow") is not None:
        out["net_cf_abs"] = _rs(g("net_monthly_cash_flow"))
    if g("gross_margin_pct") is not None:
        out["margin"] = f"{g('gross_margin_pct'):g}%"
    return out


def concern(problem_key: str, facts: dict) -> str:
    from knowledge_base.problems import CONCERNS
    template = CONCERNS.get(problem_key, PROBLEMS[problem_key]["description"])
    return template.format_map(facts)


def plain_summary(result) -> list:
    """2-3 plain sentences: status, how long the cash lasts, the main concern."""
    name = result.inputs.get("business_name") or "Your business"
    if not result.sufficient:
        labels = ", ".join(m["label"].lower() for m in result.missing)
        return [f"We could not diagnose {name} because some essential information is missing: "
                f"{labels}.", "Please add it and run the diagnosis again."]

    sentences = [STATUS_SENTENCE.get(result.status, "{name}: " + result.status).format(name=name)]
    wm = result.wm
    runway, net = wm.get("runway_days"), wm.get("net_monthly_cash_flow")
    if runway is not None:
        cash = f"Your cash covers about {runway:,.0f} days of fixed costs and loan payments"
        if net is not None:
            cash += (f", and you are losing about {_rs(net)} a month" if net < 0 else
                     f", and you keep about {_rs(net)} a month after these costs")
        sentences.append(cash + ".")
    elif net is not None:
        sentences.append(f"Each month you {'lose' if net < 0 else 'keep'} about {_rs(net)} "
                         "after fixed costs and loan payments.")

    facts = summary_facts(wm)
    # "Not sure"-only problems are not stated as facts
    certain = [p for p in result.problems if not p.get("unsure")]
    unsure = [p for p in result.problems if p.get("unsure")]
    if certain:
        # skip cash-runway problems already covered by the cash sentence
        covered = CASH_PROBLEMS if len(sentences) > 1 else set()
        others = [p for p in certain if p["key"] not in covered]
        phrases = list(dict.fromkeys(concern(p["key"], facts) for p in (others or certain)))
        lead = ("Besides the cash shortage, the main concern is that"
                if others and len(others) < len(certain)
                and any(p["key"] in covered for p in certain[:1])
                else "One thing to improve is that" if result.status == "Healthy"
                else "The main concern is that")
        text = f"{lead} {phrases[0]}"
        if len(phrases) > 1:
            text += f"; also, {phrases[1]}"
        sentences.append(text + ".")
    elif not unsure:
        sentences.append("Keep monitoring your cash every month to stay healthy.")
    if unsure:
        sentences.append(f"You weren't sure whether {concern(unsure[0]['key'], facts)} "
                         "- worth checking.")
    return sentences


def figure_meaning(metric: str, value, th: dict) -> str:
    """One plain-language line explaining what a key figure means for this business."""
    if value is None:
        return "Could not be calculated from your answers."
    if metric == "current_ratio":
        if value < th["current_ratio_weak"]:
            return "You owe more in the short term than you have in short-term assets."
        if value < th["current_ratio_safe"]:
            return "Your short-term assets only just cover what you owe soon."
        return "You have comfortably more short-term assets than short-term debts."
    if metric == "quick_ratio":
        if value < th["quick_ratio_critical"]:
            return "Without selling stock you could pay less than half of what you owe soon."
        if value < th["quick_ratio_safe"]:
            return "Without selling stock you could not pay all your short-term debts."
        return "You could pay your short-term debts even without selling stock."
    if metric == "cash_ratio":
        return f"Cash alone covers {value:.0%} of what you owe in the short term."
    if metric == "runway_days":
        return f"Your cash would last about {value:,.0f} days of fixed costs and installments."
    if metric == "net_monthly_cash_flow":
        return (f"You lose about {_rs(value)} each month after fixed costs and loan payments."
                if value < 0 else
                f"You keep about {_rs(value)} each month after fixed costs and loan payments.")
    if metric == "working_capital":
        return (f"Short-term debts are larger than short-term assets by {_rs(value)}."
                if value < 0 else f"Short-term assets exceed short-term debts by {_rs(value)}.")
    if metric == "cash_conversion_cycle":
        if value <= 0:
            return "You collect cash before you have to pay suppliers - suppliers fund your stock."
        return f"Money spent on stock takes about {value:,.0f} days to come back as cash."
    if metric == "debt_service_ratio":
        if value == 0:
            return "You have no loan installments to pay."
        return f"Loan installments take {value:.0%} of your gross profit."
    if metric == "receivables_to_sales":
        if value == 0:
            return "No customers owe you money - you are paid straight away."
        return f"Customers owe you about {value:.1f} months of sales."
    if metric == "inventory_to_sales":
        if value == 0:
            return "You hold no stock."
        return f"You hold about {value:.1f} months of sales as stock."
    return ""


def formula_text(name: str) -> str:
    return FORMULAS[name][1] if name in FORMULAS else ""


def problem_catalog_rows() -> list:
    return [{"Key": k, "Problem": v["title"], "Severity": v["severity"],
             "Decisions": " | ".join(d["text"] for d in v["decisions"])}
            for k, v in PROBLEMS.items()]
