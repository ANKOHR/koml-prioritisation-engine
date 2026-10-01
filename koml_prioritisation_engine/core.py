"""Pure scoring of hypothetical input estimates; no predictions or savings claims."""
from decimal import Decimal, InvalidOperation, localcontext, ROUND_HALF_EVEN

class SchemaError(ValueError):
    """An explicitly named input schema failure."""

FIELDS = {"id", "title", "expected_value", "urgency", "reversibility", "effort", "synthetic", "entered_by"}

def number(value, field, low, high):
    if isinstance(value, bool) or not isinstance(value, (str, int, float, Decimal)):
        raise SchemaError(f"field {field}: expected a finite decimal")
    try:
        result = Decimal(str(value))
    except InvalidOperation:
        raise SchemaError(f"field {field}: expected a finite decimal") from None
    if not result.is_finite() or not low <= result <= high:
        raise SchemaError(f"field {field}: must be between {low} and {high}")
    return result

def validate(task):
    if not isinstance(task, dict):
        raise SchemaError("field record: expected an object")
    unknown = set(task) - FIELDS
    missing = FIELDS - set(task) - {"entered_by"}
    if unknown or missing:
        raise SchemaError(f"fields: unknown={sorted(unknown)}, missing={sorted(missing)}")
    for field, maximum in (("id", 256), ("title", 10000)):
        if not isinstance(task[field], str) or not task[field].strip() or len(task[field]) > maximum:
            raise SchemaError(f"field {field}: nonempty text of at most {maximum} characters required")
        if "\u2014" in task[field]:
            raise SchemaError(f"field {field}: em dash is unsupported; use a hyphen")
    if type(task["synthetic"]) is not bool:
        raise SchemaError("field synthetic: expected boolean")
    if not task["synthetic"] and task.get("entered_by") != "Henry":
        raise SchemaError("field entered_by: real input requires Henry's explicit declaration")
    if "entered_by" in task and task["entered_by"] != "Henry":
        raise SchemaError("field entered_by: only Henry is supported")
    return {**task,
        "expected_value": number(task["expected_value"], "expected_value", Decimal(0), Decimal("1000000000")),
        "urgency": number(task["urgency"], "urgency", Decimal(0), Decimal(10)),
        "reversibility": number(task["reversibility"], "reversibility", Decimal(0), Decimal(1)),
        "effort": number(task["effort"], "effort", Decimal("0.01"), Decimal("1000000"))}

def decimal_text(value):
    return format(value, "f")

def score(task):
    """Hypothetical score, rounded to six decimal places using half-even."""
    task = validate(task)
    with localcontext() as ctx:
        ctx.prec = 50
        value = task["expected_value"] * (1 + task["urgency"]) * (1 + task["reversibility"]) / task["effort"]
        return value.quantize(Decimal("0.000001"), rounding=ROUND_HALF_EVEN)

def evaluate(tasks):
    rows, ids = [], set()
    for raw in tasks:
        task = validate(raw)
        if task["id"] in ids:
            raise SchemaError(f"field id: duplicate {task['id']!r}")
        ids.add(task["id"])
        row = {k: decimal_text(v) if isinstance(v, Decimal) else v for k, v in task.items()}
        row.update(score=decimal_text(score(raw)), score_label="hypothetical priority from supplied estimates")
        rows.append(row)
    rows.sort(key=lambda r: (-Decimal(r["score"]), r["id"]))
    with localcontext() as ctx:
        ctx.prec = 50
        total = sum((Decimal(r["expected_value"]) for r in rows), Decimal(0))
    return {"schema_version": 1, "score_label": "hypothetical priority from supplied estimates",
        "formula": "expected_value * (1 + urgency) * (1 + reversibility) / effort",
        "count": len(rows), "synthetic_count": sum(r["synthetic"] for r in rows),
        "real_count": sum(not r["synthetic"] for r in rows),
        "total_expected_value": decimal_text(total), "total_expected_value_label": "hypothetical supplied value units, not measured money or savings",
        "high_priority_ids": sorted(r["id"] for r in rows if Decimal(r["score"]) >= 100),
        "tasks": rows}
