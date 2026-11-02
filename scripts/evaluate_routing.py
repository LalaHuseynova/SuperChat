"""Reproducible, offline routing evaluation. No model calls or credentials."""

import json
from collections import Counter
from pathlib import Path
from superchat.nlu import route
from superchat.store import initial_state

root = Path(__file__).resolve().parents[1]
cases = json.loads((root / "tests/routing_cases.json").read_text())
results = []
for c in cases:
    state = initial_state()
    state["active_domains"] = c.get("active", [])
    actual = route(c["text"], state)["category"]
    results.append({**c, "actual": actual, "correct": actual == c["expected"]})
passed = sum(r["correct"] for r in results)
lines = [
    "# Routing test log",
    "",
    f"Date: 2 November 2026. Offline rule router; reference date 2026-11-02.",
    "",
    f"**{passed}/{len(results)} correct ({100 * passed / len(results):.1f}%).**",
    "",
    "Author-written regression set, including the brief, translated equivalents, context-dependent follow-ups, mixed-language requests and four harder paraphrases. This is not an independent benchmark or a general accuracy guarantee. No OpenRouter key was supplied, so hosted-model accuracy is not measured.",
    "",
    "| Language | Correct | Total | Accuracy |",
    "|---|---:|---:|---:|",
]
for lang in ["en", "az", "ru", "mixed"]:
    subset = [r for r in results if r["lang"] == lang]
    n = sum(r["correct"] for r in subset)
    lines.append(f"| {lang} | {n} | {len(subset)} | {100 * n / len(subset):.1f}% |")
lines += ["", "## Error analysis", ""]
failures = [r for r in results if not r["correct"]]
for r in failures:
    lines.append(f"- `{r['text']}`: expected {r['expected']}, got {r['actual']}.")
lines += [
    "",
    "Rules recognize catalogue terms and explicit follow-ups. Unseen slang and indirect descriptions can become clarifications rather than domain matches. Optional OpenRouter parsing targets those cases; it is not counted in these results. No routing error permits invented catalogue records.",
    "",
    "## Complete results",
    "",
    "| # | Language | Expected | Actual | Pass | Input |",
    "|---:|---|---|---|---|---|",
]
for i, r in enumerate(results, 1):
    lines.append(
        f"| {i} | {r['lang']} | {r['expected']} | {r['actual']} | {'yes' if r['correct'] else 'no'} | {r['text']} |"
    )
(root / "docs/TEST_LOG.md").write_text("\n".join(lines) + "\n")
(root / "docs/routing-results.json").write_text(
    json.dumps(
        {
            "total": len(results),
            "correct": passed,
            "accuracy": passed / len(results),
            "results": results,
        },
        ensure_ascii=False,
        indent=2,
    )
    + "\n"
)
print(
    f"{passed}/{len(results)} routing cases correct ({100 * passed / len(results):.1f}%)"
)
for r in failures:
    print("MISS", r["text"], r["expected"], "->", r["actual"])
