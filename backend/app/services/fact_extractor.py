from __future__ import annotations

import re
from typing import Any


# ------------------------------------------------------------
# Normalisation / identity helpers
# ------------------------------------------------------------

def clean(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def norm(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", " ", clean(value).lower()).strip()


ALIASES = {
    "MIT-WPU": ["mit world peace university", "mit wpu", "mit-wpu"],
    "IIM Bangalore": ["iim bangalore", "indian institute of management bangalore"],
    "Christ University": ["christ university", "christ university bangalore"],
    "JAGSoM": ["jagsom", "jagdish sheth school of management"],
    "BITS Pilani WILP": ["bits pilani wilp", "bits pilani"],
    "NMIMS": ["nmims", "narsee monjee institute of management studies"],
    "SCMHRD Pune": ["scmhrd", "symbiosis centre for management and human resource development"],
    "Amrita Vishwa Vidyapeetham": ["amrita vishwa vidyapeetham", "amrita university"],
    "New Horizon College of Engineering": ["new horizon college of engineering", "nhce"],
    "Dayananda Sagar Business School": ["dayananda sagar business school", "dsbs"],
    "JSPM University": ["jspm university", "jspm"],
    "Indira University": ["indira university", "indira school of business"],
}

FIELD_PATTERNS = {
    "College Brand Value / Reputation": [
        r"nirf[^.]{0,160}", r"ranked[^.]{0,160}", r"reputation[^.]{0,160}",
        r"legacy[^.]{0,120}", r"accredited[^.]{0,180}"
    ],
    "Entrance Exams Accepted": [
        r"entrance exams?[^.]{0,300}", r"accepted[^.]{0,300}(?:CAT|XAT|SNAP|CMAT|MAT|GMAT|NMAT|CET)[^.]{0,180}"
    ],
    "Total MBA Fees": [
        r"(?:total|program(?:me)?|tuition|academic) fees?[^.]{0,180}",
        r"fees?[^.]{0,100}(?:₹|INR)\s*[\d,.]+\s*(?:lakh|lakhs|crore)?"
    ],
    "Average Placement Package": [
        r"average (?:placement )?package[^.]{0,120}", r"average ctc[^.]{0,120}", r"average salary[^.]{0,120}"
    ],
    "Median Placement Package": [
        r"median (?:placement )?(?:package|salary|ctc)[^.]{0,120}"
    ],
    "Placement Percentage": [
        r"[0-9]{1,3}(?:\.[0-9]+)?\s*%[^.]{0,80}(?:placement|placed|students)",
        r"placement (?:rate|percentage)[^.]{0,120}"
    ],
    "Top Recruiting Companies": [
        r"top recruiters?[^.]{0,500}", r"companies (?:visited|recruiting|hiring)[^.]{0,500}", r"recruiters?[^.]{0,500}"
    ],
    "Specializations Offered": [
        r"speciali[sz]ations?[^.]{0,500}", r"MBA[^.]{0,300}(?:Marketing|Finance|HR|Analytics|Operations)[^.]{0,300}"
    ],
    "Curriculum / Course Quality": [
        r"curriculum[^.]{0,500}", r"syllabus[^.]{0,500}", r"key skills covered[^.]{0,500}", r"courses?[^.]{0,400}"
    ],
    "Eligibility & Admission Criteria": [
        r"eligibility[^.]{0,500}", r"selection process[^.]{0,500}", r"admission process[^.]{0,500}"
    ],
    "Reservation / Category Benefits": [
        r"reserved category[^.]{0,250}", r"reservation[^.]{0,250}", r"SC/ST/OBC/EWS[^.]{0,250}"
    ],
    "Career Fit": [
        r"business analyst[^.]{0,180}", r"data analyst[^.]{0,180}", r"analytics consultant[^.]{0,180}",
        r"strategy analyst[^.]{0,180}", r"career opportunities[^.]{0,300}"
    ],
}


def institution_match(target: str, source: dict[str, Any]) -> bool:
    target_aliases = [target] + ALIASES.get(target, [])
    blob = " ".join([
        clean(source.get("title")),
        clean(source.get("content")),
        clean(source.get("url")),
    ]).lower()
    if not blob.strip():
        return False
    return any(norm(alias) and norm(alias) in norm(blob) for alias in target_aliases)


def program_match(program: str, source: dict[str, Any]) -> bool:
    text = norm(" ".join([
        clean(source.get("title")),
        clean(source.get("content")),
    ]))
    p = norm(program)
    if not text:
        return False
    if "business analytics" in text or "business analytics" in p:
        return "analytics" in text or "business analytics" in text
    return any(tok in text for tok in p.split() if len(tok) > 4)


def source_type(research_source_type: str, url: str, official_domain: str = "") -> str:
    u = clean(url).lower()
    domain = clean(official_domain).lower().replace("https://", "").replace("http://", "").replace("www.", "")

    if any(x in u for x in [
        "nirfindia.org", "ugc.gov.in", "aicte.gov.in", "nbaind.org",
        "aacsb.edu", "associationofmbas.com", "efmdglobal.org"
    ]):
        return "regulator_accreditor"

    if any(x in u for x in [
        "reddit.com", "pagalguy.com", "youtube.com", "linkedin.com"
    ]):
        return "community"

    if any(x in u for x in [
        "collegedunia.com", "careers360.com", "shiksha.com",
        "mbauniverse.com", "kollegeapply.com", "findmycollege.com",
        "zollege.in", "boostmytalent.com"
    ]):
        return "secondary"

    # Only call a result official when its URL belongs to the
    # candidate's declared official domain.
    if domain and domain in u:
        return "official"

    if research_source_type == "official":
        return "other_official_domain"

    return "other"


def tier(st: str) -> int:
    return {"official": 1, "regulator_accreditor": 1, "secondary": 2, "community": 3}.get(st, 4)


def snippets(text: str, patterns: list[str], limit: int = 3) -> list[str]:
    out: list[str] = []
    raw = clean(text)
    for pattern in patterns:
        try:
            for m in re.finditer(pattern, raw, flags=re.I):
                s = raw[max(0, m.start() - 90): min(len(raw), m.end() + 90)]
                s = clean(s)
                if len(s) >= 25 and s not in out:
                    out.append(s)
                if len(out) >= limit:
                    return out
        except re.error:
            continue
    return out


def extract_cutoff_candidates(text: str, year: int) -> list[str]:
    raw = clean(text)
    hits = []
    year_pat = str(year)
    exams = r"(?:CAT|XAT|SNAP|CMAT|MAT|GMAT|NMAT|MAH[- ]?MBA[- ]?CET|CET|ATMA)"
    # Capture year + exam + percentile/percentile range in nearby text.
    pats = [
        rf"{year_pat}[^.{{0,140}}]{{0,20}}({exams})[^.{{0,140}}]{{0,90}}([0-9]{{2,3}}(?:\s*[-–]\s*[0-9]{{2,3}})?)\s*(?:percentile|%)",
        rf"({exams})[^.{{0,140}}]{{0,90}}{year_pat}[^.{{0,140}}]{{0,90}}([0-9]{{2,3}}(?:\s*[-–]\s*[0-9]{{2,3}})?)\s*(?:percentile|%)",
    ]
    for pat in pats:
        for m in re.finditer(pat, raw, flags=re.I):
            hits.append(clean(m.group(0)))
    return list(dict.fromkeys(hits))[:5]


def build_compact_candidate(college: dict[str, Any]) -> dict[str, Any]:
    institution = clean(college.get("institution"))
    program = clean(college.get("program"))

    sources = []
    for group_name in [
        "official_admission_research",
        "official_quality_research",
        "third_party_fallback_research",
    ]:
        for research in college.get(group_name, []) or []:
            st = research.get("source_type") or ("official" if "official" in group_name else "third_party")
            for result in research.get("results", []) or []:
                src = {
                    "url": clean(result.get("url")),
                    "title": clean(result.get("title")),
                    "content": clean(result.get("content")),
                    "source_type": source_type(st, result.get("url", ""), college.get("official_domain", "")),
                    "score": result.get("score"),
                    "research_type": research.get("query_type", ""),
                }
                if not institution_match(institution, src):
                    continue
                sources.append(src)

    # Prefer program-specific material for programme fields, but retain institution-wide placement separately.
    fields: dict[str, list[dict[str, Any]]] = {}

    def add(field: str, value: str, src: dict[str, Any], scope: str = "unknown"):
        if not value:
            return
        fields.setdefault(field, []).append({
            "value": clean(value),
            "evidence": clean(value),
            "source_url": src["url"],
            "source_title": src["title"],
            "source_type": src["source_type"],
            "scope": scope,
            "source_score": src.get("score"),
        })

    for src in sorted(sources, key=lambda s: (tier(s["source_type"]), -(float(s.get("score") or 0)))):
        text = f"{src['title']}. {src['content']}"
        scope = "program_specific" if program_match(program, src) else "institution_wide"

        for field, pats in FIELD_PATTERNS.items():
            for snip in snippets(text, pats, limit=3):
                add(field, snip, src, scope)

        for y in (2025, 2024):
            for hit in extract_cutoff_candidates(text, y):
                field = f"{y} Cutoff — Exam & Percentile"
                add(field, hit, src, scope)

    # Deterministically cap evidence to keep Agent 2 fast.
    for k in list(fields):
        dedup = []
        seen = set()
        for ev in fields[k]:
            key = (ev["value"], ev["source_url"])
            if key not in seen:
                seen.add(key)
                dedup.append(ev)
        fields[k] = dedup[:4]

    # Metadata-only fields.
    fields.setdefault("Location / City", []).append({
        "value": clean(college.get("location")),
        "evidence": clean(college.get("location")),
        "source_url": clean(college.get("official_url")),
        "source_title": "Candidate metadata",
        "source_type": "official",
        "scope": "general",
        "source_score": None,
    })

    return {
        "candidate_index": college.get("candidate_index"),
        "institution": institution,
        "program": program,
        "location": clean(college.get("location")),
        "official_url": clean(college.get("official_url")),
        "selection_score": college.get("selection_score"),
        "fields": fields,
        "source_count": len(sources),
        "source_urls": list(dict.fromkeys([s["url"] for s in sources if s["url"]]))[:12],
    }


def extract_facts(payload: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError("Payload must be a JSON object")

    profile = payload.get("student_profile") or {}
    colleges = payload.get("colleges") or []

    compact = [build_compact_candidate(c) for c in colleges if isinstance(c, dict)]

    return {
        "status": "success",
        "extraction_status": "ready_for_agent_2_audit",
        "student_profile": profile,
        "college_count": len(compact),
        "candidates": compact,
    }
