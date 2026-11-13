"""Knowledge base package: rules, problem catalog, formulas, questions, thresholds."""
import json
from pathlib import Path

THRESHOLDS_PATH = Path(__file__).with_name("thresholds.json")


def load_threshold_table(path=THRESHOLDS_PATH) -> dict:
    """Full table: name -> {value, group, description} (used by the Admin page)."""
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def load_thresholds(path=THRESHOLDS_PATH) -> dict:
    """Flat dict: name -> numeric value (what the inference engine uses)."""
    return {name: entry["value"] for name, entry in load_threshold_table(path).items()}


# Threshold pairs that must stay in increasing order: (smaller, larger)
ORDER_RULES = [
    ("current_ratio_weak", "current_ratio_safe"),
    ("current_ratio_safe", "current_ratio_excess"),
    ("quick_ratio_critical", "quick_ratio_safe"),
    ("crisis_runway_days", "short_runway_days"),
    ("short_runway_days", "safe_runway_days"),
    ("slow_collection_days", "very_slow_collection_days"),
    ("slow_stock_days", "dead_stock_days"),
    ("dsr_moderate", "dsr_heavy"),
    ("crisis_score", "watch_score"),
    ("watch_score", "healthy_score"),
]


def validate_thresholds(values: dict, defaults: dict) -> list:
    """Check edited/uploaded thresholds before the engine uses them."""
    errors = []
    unknown, missing = set(values) - set(defaults), set(defaults) - set(values)
    if unknown:
        errors.append(f"Unknown thresholds: {', '.join(sorted(unknown))}")
    if missing:
        errors.append(f"Missing thresholds: {', '.join(sorted(missing))}")
    for name, value in values.items():
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            errors.append(f"{name} must be a number.")
        elif value < 0:
            errors.append(f"{name} cannot be negative.")
    if not errors:
        for low, high in ORDER_RULES:
            if values[low] >= values[high]:
                errors.append(f"{low} ({values[low]}) must be smaller than {high} ({values[high]}).")
        for name in ("crisis_score", "watch_score", "healthy_score"):
            if values[name] > 100:
                errors.append(f"{name} must be between 0 and 100.")
        if not 0 < values["cap_min_cf"] <= 1:
            errors.append("cap_min_cf must be between 0 and 1.")
        if not 0 < values["not_sure_cf"] < 1:
            errors.append("not_sure_cf must be between 0 and 1 (a 'Not sure' answer is weaker "
                          "than a 'Yes').")
    return errors
