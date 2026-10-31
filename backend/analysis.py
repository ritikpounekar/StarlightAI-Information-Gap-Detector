from __future__ import annotations

import re
from datetime import datetime
from itertools import combinations


CRITERIA = [
    {
        "id": "eligibility",
        "title": "Eligibility criteria",
        "area": "Who can apply",
        "severity": "HIGH",
        "description": "Confirm every qualifying rule, including age, academic standing, residency, and income.",
        "terms": ("eligib", "qualif", "applicant", "who can apply", "age limit", "income limit", "GPA", "cgpa"),
    },
    {
        "id": "deadline",
        "title": "Current application deadline",
        "area": "Timing",
        "severity": "CRITICAL",
        "description": "Find a dated deadline for the active application cycle and confirm it on the official portal.",
        "terms": (
            "deadline",
            "due date",
            "last date",
            "apply by",
            "application closes",
            "applications close",
            "closing date",
            "submission date",
        ),
    },
    {
        "id": "documents",
        "title": "Required application documents",
        "area": "Application requirements",
        "severity": "HIGH",
        "description": "Verify the complete document list, accepted formats, and whether certified copies are required.",
        "terms": ("document", "certificate", "transcript", "proof", "paperwork", "upload", "income tax return", "form 16"),
    },
    {
        "id": "income_proof",
        "title": "Accepted income proof",
        "area": "Financial requirements",
        "severity": "HIGH",
        "description": "Confirm which income evidence is accepted; sources may use different or exclusive requirements.",
        "terms": ("income certificate", "income proof", "income tax return", "form 16", "tahsildar", "tax return"),
    },
    {
        "id": "renewal",
        "title": "Renewal and continuation rules",
        "area": "After receiving the award",
        "severity": "HIGH",
        "description": "Check year-to-year GPA, attendance, progress, and renewal submission requirements.",
        "terms": ("renew", "continuation", "maintain", "renewal", "subsequent year", "attendance", "retention"),
    },
    {
        "id": "process",
        "title": "Application and selection process",
        "area": "How to apply",
        "severity": "MEDIUM",
        "description": "Locate the official application steps, selection stages, and a help or contact channel.",
        "terms": ("apply", "application process", "selection", "submit", "portal", "contact", "helpdesk"),
    },
    {
        "id": "award",
        "title": "Award amount and disbursement",
        "area": "Funding",
        "severity": "MEDIUM",
        "description": "Verify the award value, payment schedule, and any conditions attached to disbursement.",
        "terms": ("award amount", "scholarship amount", "stipend", "grant", "disburse", "tuition", "funding"),
    },
]

DATE_RE = re.compile(
    r"\b(?:\d{1,2}[/-]\d{1,2}(?:[/-]\d{2,4})?|"
    r"(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|"
    r"Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|"
    r"Dec(?:ember)?)\s+\d{1,2}(?:,?\s+\d{4})?|"
    r"\d{1,2}\s+(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|"
    r"Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|"
    r"Dec(?:ember)?)\s+\d{4})\b",
    re.IGNORECASE,
)
NUMBER_RE = re.compile(r"\b\d+(?:,\d{3})*(?:\.\d+)?\s*(?:%|percent|years?|months?|days?|USD|INR|\$|₹)?\b", re.I)
YEAR_RE = re.compile(r"\b(?:19|20)\d{2}\b")
SENTENCE_RE = re.compile(r"(?<=[.!?])\s+|\n+")


def _sentences(text: str) -> list[str]:
    return [
        re.sub(r"^\s*[-*•\d.)]+\s*", "", sentence).strip()
        for sentence in SENTENCE_RE.split(text)
        if len(sentence.strip()) >= 24
    ]


def _matches_criterion(sentence: str, criterion: dict) -> bool:
    lowered = sentence.casefold()
    return any(term.casefold() in lowered for term in criterion["terms"])


def _quote(sentence: str, source_name: str) -> str:
    excerpt = sentence[:320].strip()
    if len(sentence) > 320:
        excerpt = excerpt.rsplit(" ", 1)[0] + "…"
    return f'“{excerpt}” [Source: {source_name}]'


def _finding_categories(sentence: str) -> list[str]:
    return [criterion["id"] for criterion in CRITERIA if _matches_criterion(sentence, criterion)]


def _value_signature(category: str, sentence: str) -> set[str]:
    if category == "deadline":
        return {match.casefold().strip() for match in DATE_RE.findall(sentence)}
    return {match.casefold().replace(" ", "") for match in NUMBER_RE.findall(sentence)}


def _has_exclusive_language(sentence: str) -> bool:
    lowered = sentence.casefold()
    return any(term in lowered for term in ("only", "must", "required", "mandatory", "not accepted", "instead of"))


def _find_conflicts(sources: list[dict], sentences_by_source: list[list[str]]) -> list[dict]:
    conflicts = []
    seen = set()
    for (left_source, left_sentences), (right_source, right_sentences) in combinations(
        zip(sources, sentences_by_source), 2
    ):
        for left in left_sentences:
            left_categories = set(_finding_categories(left))
            for right in right_sentences:
                shared_categories = left_categories.intersection(_finding_categories(right))
                for category in shared_categories:
                    left_values = _value_signature(category, left)
                    right_values = _value_signature(category, right)
                    differs_by_value = bool(left_values and right_values and left_values.isdisjoint(right_values))
                    differs_by_exclusivity = (
                        category == "income_proof"
                        and _has_exclusive_language(left)
                        and _has_exclusive_language(right)
                        and left.casefold() != right.casefold()
                    )
                    if not (differs_by_value or differs_by_exclusivity):
                        continue
                    key = (category, left_source["name"], right_source["name"])
                    if key in seen:
                        continue
                    seen.add(key)
                    criterion = next(item for item in CRITERIA if item["id"] == category)
                    conflicts.append(
                        {
                            "id": f"conflict-{len(conflicts) + 1}",
                            "topic": criterion["title"],
                            "source_a": {"name": left_source["name"], "claim": _quote(left, left_source["name"])},
                            "source_b": {"name": right_source["name"], "claim": _quote(right, right_source["name"])},
                            "resolution_advice": "Treat this as unresolved. Check the latest official notice or contact the issuing organization before acting.",
                        }
                    )
    return conflicts[:8]


def analyze_research(query: str, sources: list[dict]) -> dict:
    sentences_by_source = [_sentences(source["text"]) for source in sources]
    all_sentences = [sentence for group in sentences_by_source for sentence in group]
    is_scholarship = any(term in query.casefold() for term in ("scholarship", "grant", "financial aid", "bursary"))
    criteria = CRITERIA if is_scholarship else [
        criterion for criterion in CRITERIA if criterion["id"] not in {"renewal", "income_proof"}
    ]

    evidence_matrix = []
    for source, sentences in zip(sources, sentences_by_source):
        relevant = [
            sentence
            for sentence in sentences
            if any(_matches_criterion(sentence, criterion) for criterion in criteria)
        ]
        if not relevant:
            relevant = sentences
        for sentence in relevant[:5]:
            evidence_matrix.append(
                {
                    "claim": _quote(sentence, source["name"]),
                    "source": source["name"],
                    "confidence": "Direct source excerpt",
                    "is_inferred": False,
                }
            )

    gaps = []
    covered = []
    for criterion in criteria:
        matching = [sentence for sentence in all_sentences if _matches_criterion(sentence, criterion)]
        if matching:
            covered.append(criterion["id"])
        else:
            gaps.append(
                {
                    "id": f"gap-{criterion['id']}",
                    "title": f"Missing: {criterion['title']}",
                    "severity": criterion["severity"],
                    "description": criterion["description"],
                    "affected_area": criterion["area"],
                    "ai_confidence": "Heuristic signal",
                    "evidence": "Not found in the supplied source text",
                }
            )

    conflicts = _find_conflicts(sources, sentences_by_source)
    if conflicts:
        evidence_matrix.extend(
            {
                "claim": claim,
                "source": source_name,
                "confidence": "Direct source excerpt — disputed",
                "is_inferred": False,
            }
            for conflict in conflicts
            for source_name, claim in (
                (conflict["source_a"]["name"], conflict["source_a"]["claim"]),
                (conflict["source_b"]["name"], conflict["source_b"]["claim"]),
            )
        )

    current_year = datetime.now().year
    freshness_warnings = []
    for source, sentences in zip(sources, sentences_by_source):
        years = [int(year) for year in YEAR_RE.findall(source["text"])]
        if not years:
            freshness_warnings.append(
                {
                    "source": source["name"],
                    "status": "UNDATED",
                    "detected_year": None,
                    "warning": "No publication or application-cycle year was detected. Confirm this source is current.",
                }
            )
        elif min(years) < current_year - 1:
            freshness_warnings.append(
                {
                    "source": source["name"],
                    "status": "POTENTIALLY OUTDATED",
                    "detected_year": min(years),
                    "warning": f"References {min(years)}; requirements may have changed since that cycle.",
                }
            )

    checklist = []
    for gap in gaps:
        checklist.append(
            {
                "id": f"verify-{gap['id']}",
                "task": gap["description"],
                "priority": gap["severity"],
                "done": False,
                "related_gap": gap["id"],
            }
        )
    for conflict in conflicts:
        checklist.append(
            {
                "id": f"verify-{conflict['id']}",
                "task": f"Resolve the conflicting {conflict['topic'].lower()} in {conflict['source_a']['name']} and {conflict['source_b']['name']}.",
                "priority": "CRITICAL",
                "done": False,
                "related_conflict": conflict["id"],
            }
        )
    for warning in freshness_warnings:
        checklist.append(
            {
                "id": f"verify-freshness-{len(checklist) + 1}",
                "task": f"Check whether “{warning['source']}” is current and find a dated official source.",
                "priority": "HIGH",
                "done": False,
            }
        )

    completeness = round(100 * len(covered) / max(len(criteria), 1))
    missing_critical = sum(gap["severity"] == "CRITICAL" for gap in gaps)
    missing_high = sum(gap["severity"] == "HIGH" for gap in gaps)
    summary = (
        f"Reviewed {len(sources)} source{'s' if len(sources) != 1 else ''}. "
        f"{len(covered)} of {len(criteria)} key information areas have source text; "
        f"{len(gaps)} potential gaps and {len(conflicts)} cross-source conflicts need review. "
        "Coverage indicates whether a topic appears, not whether its claims are correct."
    )
    inferred = []
    if is_scholarship:
        inferred.append(
            {
                "claim": "Ask whether this award has additional renewal, attendance, or course-load conditions not stated in the supplied text.",
                "source": "StarlightAI analysis suggestion",
                "confidence": "Rule-based inference — verification prompt only, not a source claim",
                "is_inferred": True,
            }
        )
    if is_scholarship:
        evidence_matrix.extend(inferred)

    return {
        "status": "success",
        "brand": "StarlightAI",
        "topic": query,
        "overall_completeness_score": completeness,
        "coverage_label": "Source coverage, not truth score",
        "summary": summary,
        "gap_severity_radar": {
            "critical": missing_critical,
            "high": missing_high,
            "medium": sum(gap["severity"] == "MEDIUM" for gap in gaps),
            "low": sum(gap["severity"] == "LOW" for gap in gaps),
        },
        "gaps": gaps,
        "conflicts": conflicts,
        "freshness_warnings": freshness_warnings,
        "verification_checklist": checklist,
        "evidence_matrix": evidence_matrix[:32],
        "sources_reviewed": [
            {"name": source["name"], "type": source["type"], "characters": len(source["text"])}
            for source in sources
        ],
        "analysis_note": "Findings use transparent keyword and pattern checks, not a trained or generative AI model. Validate every decision against the issuing organization.",
    }
