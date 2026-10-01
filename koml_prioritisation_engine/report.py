"""Deterministic reports with explicit provenance and hypothetical figure labels."""
import json

def banner(result):
    return (f"Data provenance: {result['synthetic_count']} synthetic fixtures; "
            f"{result['real_count']} real tasks declared entered by Henry. "
            "Scores and expected values are hypothetical supplied estimates. No measured savings.")

def render(result, fmt):
    if fmt == "json":
        return json.dumps({"provenance_banner": banner(result), **result}, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    lines = ["# KOML Prioritisation Engine", "", banner(result), "",
        f"Task count: {result['count']}",
        f"Total hypothetical expected value (supplied value units): {result['total_expected_value']}",
        f"High priority count (hypothetical score >= 100): {len(result['high_priority_ids'])}",
        "", f"Formula: `{result['formula']}`", "",
        "| ID | Title | Hypothetical score |", "| --- | --- | --- |"]
    def escape(text):
        return text.replace("&", "&amp;").replace("<", "&lt;").replace("|", "&#124;").replace("\r", " ").replace("\n", " ")
    lines.extend(f"| {escape(r['id'])} | {escape(r['title'])} | {r['score']} |" for r in result["tasks"])
    return "\n".join(lines) + "\n"
