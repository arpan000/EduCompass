from __future__ import annotations

import re
from typing import Any
from urllib.parse import urlparse


DEEP_RESEARCH_LIMIT = 12


# ============================================================
# DOMAINS WE DO NOT TREAT AS OFFICIAL COLLEGE SOURCES
# ============================================================

BLOCKED_DOMAINS = {
    "shiksha.com",
    "careers360.com",
    "collegedunia.com",
    "collegedekho.com",
    "getmyuni.com",
    "targetadmission.com",
    "taxila.in",
    "collegesearch.in",
    "entrancezone.com",
    "reddit.com",
    "youtube.com",
    "quora.com",
    "linkedin.com",
    "facebook.com",
    "instagram.com",
    "x.com",
    "twitter.com",
    "mbauniverse.com",
    "catmock.com",
    "ismtindia.com",
    "gmac.com",
}


# ============================================================
# COMMON INSTITUTION ALIASES
# These are identity-normalization rules, NOT college facts.
# ============================================================

ALIASES = {
    "symbiosis institute of business management bengaluru":
        "SIBM Bengaluru",

    "symbiosis institute of business management bangalore":
        "SIBM Bengaluru",

    "sibm bengaluru":
        "SIBM Bengaluru",

    "sibm bangalore":
        "SIBM Bengaluru",

    "sibm-b":
        "SIBM Bengaluru",

    "symbiosis institute of business management pune":
        "SIBM Pune",

    "sibm pune":
        "SIBM Pune",

    "scmhrd":
        "SCMHRD Pune",

    "indira university":
        "Indira University",

    "mit-world peace university":
        "MIT-WPU",

    "mit wpu":
        "MIT-WPU",

    "mit-wpu":
        "MIT-WPU",

    "bits pilani wilp":
        "BITS Pilani WILP",

    "amrita school of business":
        "Amrita Vishwa Vidyapeetham",

    "amrita vishwa vidyapeetham":
        "Amrita Vishwa Vidyapeetham",

    "chandigarh university":
        "Chandigarh University",

    "christ university":
        "Christ University",

    "coep technological university":
        "COEP Technological University",

    "dayananda sagar business school":
        "Dayananda Sagar Business School",

    "new horizon college of engineering":
        "New Horizon College of Engineering",

    "izee business school":
        "IZee Business School",

    "one school of business":
        "One School Of Business",

    "jagdish sheth school of management":
        "JAGSoM",

    "jagsom":
        "JAGSoM",

    "great lakes institute of management":
        "Great Lakes Institute of Management",

    "great lakes chennai":
        "Great Lakes Institute of Management",

    "lal bahadur shastri institute of management":
        "LBSIM Delhi",

    "lbsim":
        "LBSIM Delhi",

    "welingkar institute":
        "Welingkar Institute of Management Development and Research",

    "jspm university":
        "JSPM University",

    "kirloskar institute of advanced management studies":
        "KIAMS",

    "spjimr":
        "SPJIMR",

    "sp jain":
        "SPJIMR",

    "nmims mumbai":
        "NMIMS Mumbai",

    "nmims":
        "NMIMS",
}


# ============================================================
# OFFICIAL DOMAINS KNOWN FROM DISCOVERY
# ============================================================

DIRECT_DOMAIN_MAP = {
    "indirauniversity.edu.in":
        "Indira University",

    "sibmbengaluru.edu.in":
        "SIBM Bengaluru",

    "mitwpu.edu.in":
        "MIT-WPU",

    "bits-pilani-wilp.ac.in":
        "BITS Pilani WILP",
}


# ============================================================
# KNOWN LOCATION MAP
# Used only as a deterministic location signal.
# ============================================================

CITY_BY_NAME = {
    "SIBM Bengaluru": "Bangalore",
    "SIBM Pune": "Pune",
    "SCMHRD Pune": "Pune",
    "Indira University": "Pune",
    "MIT-WPU": "Pune",
    "KIAMS": "Pune",
    "JSPM University": "Pune",
    "COEP Technological University": "Pune",

    "IIM Bangalore": "Bangalore",
    "Amrita Vishwa Vidyapeetham": "Bangalore",
    "JAGSoM": "Bangalore",
    "Christ University": "Bangalore",
    "Dayananda Sagar Business School": "Bangalore",
    "New Horizon College of Engineering": "Bangalore",
    "IZee Business School": "Bangalore",

    "NMIMS Mumbai": "Mumbai",
    "NMIMS": "Mumbai",
    "SPJIMR": "Mumbai",
    "Welingkar Institute of Management Development and Research":
        "Mumbai",

    "Great Lakes Institute of Management": "Chennai",
    "LBSIM Delhi": "Delhi",

    "IIM Calcutta": "Kolkata",
    "IIM Ahmedabad": "Ahmedabad",
    "IIM Kashipur": "Kashipur",
    "IIM Ranchi": "Ranchi",
    "IIM Kozhikode": "Kozhikode",
    "IIM Indore": "Indore",
    "IIM Lucknow": "Lucknow",

    "Chandigarh University": "Chandigarh",
    "BITS Pilani WILP": "Pilani",
}


GENERIC_BAD_NAMES = {
    "business analytics",
    "business analytics college",
    "business analytics colleges",
    "mba college",
    "mba colleges",
    "top colleges",
    "best colleges",
    "management institute",
    "business school",
    "pune university",
    "symbiosis international university",
}


# ============================================================
# BASIC HELPERS
# ============================================================

def _text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _norm(value: Any) -> str:
    value = re.sub(
        r"[^a-z0-9]+",
        " ",
        _text(value).lower(),
    )
    return re.sub(r"\s+", " ", value).strip()


def _domain(url: str) -> str:
    try:
        host = urlparse(
            _text(url)
        ).netloc.lower().split(":")[0]

        if host.startswith("www."):
            host = host[4:]

        return host

    except Exception:
        return ""


def _is_blocked(url: str) -> bool:
    d = _domain(url)

    return any(
        d == blocked or d.endswith("." + blocked)
        for blocked in BLOCKED_DOMAINS
    )


def _parse_money(value: Any) -> float | None:

    if value is None:
        return None

    if isinstance(value, (int, float)):
        return float(value)

    value = (
        _text(value)
        .lower()
        .replace(",", "")
        .replace("₹", "")
    )

    match = re.search(
        r"(\d+(?:\.\d+)?)",
        value,
    )

    if not match:
        return None

    number = float(match.group(1))

    if "crore" in value or re.search(r"\bcr\b", value):
        number *= 10_000_000

    elif "lakh" in value or "lac" in value:
        number *= 100_000

    elif re.search(r"\bk\b", value):
        number *= 1_000

    return number


# ============================================================
# FLATTEN TAVILY
# ============================================================

def _flatten_results(
    raw_results: list[dict[str, Any]]
) -> list[dict[str, Any]]:

    flattened = []

    for item in raw_results:

        if not isinstance(item, dict):
            continue

        if item.get("url") or item.get("title"):
            flattened.append(item)

        if isinstance(item.get("results"), list):

            for result in item["results"]:

                if isinstance(result, dict):
                    flattened.append(result)

        if (
            isinstance(item.get("data"), dict)
            and
            isinstance(
                item["data"].get("results"),
                list
            )
        ):

            for result in item["data"]["results"]:

                if isinstance(result, dict):
                    flattened.append(result)

    return flattened


# ============================================================
# KNOWN NAME EXTRACTION
# ============================================================

def _extract_known_names(
    source_text: str
) -> list[str]:

    low = _norm(source_text)

    found = []

    # Longest aliases first.
    for key, canonical in sorted(
        ALIASES.items(),
        key=lambda pair: -len(pair[0])
    ):

        if _norm(key) in low:

            if canonical not in found:
                found.append(canonical)

    # Reliable IIM names.
    for match in re.finditer(
        r"\bIIM\s+"
        r"(Ahmedabad|Bangalore|Calcutta|Kashipur|"
        r"Ranchi|Kozhikode|Indore|Lucknow)\b",
        source_text,
        flags=re.IGNORECASE,
    ):

        name = (
            "IIM "
            + match.group(1).title()
        )

        if name not in found:
            found.append(name)

    return found


# ============================================================
# DIRECT OFFICIAL INSTITUTION NAME
# ============================================================

def _official_name(
    url: str,
    title: str,
    body: str,
) -> str:

    d = _domain(url)

    # Known institutional domains.
    for official_domain, institution in DIRECT_DOMAIN_MAP.items():

        if (
            d == official_domain
            or d.endswith("." + official_domain)
        ):
            return institution

    # Other institutional-looking domains can be treated
    # as potentially official, but never secondary/listing sites.
    if _is_blocked(url):
        return ""

    institutional_domain = (
        ".edu.in",
        ".ac.in",
        ".edu",
        ".ac.uk",
    )

    if any(d.endswith(x) for x in institutional_domain):

        known_names = _extract_known_names(
            f"{title}\n{body}"
        )

        if known_names:
            return known_names[0]

    return ""

    d = _domain(url)

    for official_domain, institution in (
        DIRECT_DOMAIN_MAP.items()
    ):

        if (
            d == official_domain
            or d.endswith("." + official_domain)
        ):
            return institution

    # Don't try generic extraction from listing websites.
    if _is_blocked(url):
        return ""

    combined = (
        f"{title}\n{body}"
    )

    known_names = _extract_known_names(
        combined
    )

    if known_names:
        return known_names[0]

    # Generic extraction only for a
    # non-listing source.
    patterns = [

        r"\b[A-Z][A-Za-z&.'-]{2,}"
        r"(?:\s+[A-Z][A-Za-z&.'-]{2,}){0,5}"
        r"\s+University\b",

        r"\b[A-Z][A-Za-z&.'-]{2,}"
        r"(?:\s+[A-Z][A-Za-z&.'-]{2,}){0,5}"
        r"\s+Institute"
        r"(?:\s+of\s+[A-Za-z&.'-]+){0,4}\b",

        r"\b[A-Z][A-Za-z&.'-]{2,}"
        r"(?:\s+[A-Z][A-Za-z&.'-]{2,}){0,5}"
        r"\s+Business School\b",

        r"\b[A-Z][A-Za-z&.'-]{2,}"
        r"(?:\s+[A-Z][A-Za-z&.'-]{2,}){0,5}"
        r"\s+College\b",
    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            title,
        )

        if not match:
            continue

        value = re.sub(
            r"\s+",
            " ",
            match.group(0),
        ).strip()

        if _norm(value) not in {
            _norm(x)
            for x in GENERIC_BAD_NAMES
        }:

            return value

    return ""


# ============================================================
# FIND LOCAL EVIDENCE AROUND A SPECIFIC COLLEGE NAME
# ============================================================

def _mention_window(
    source_text: str,
    institution_name: str,
    radius: int = 220,
) -> str:

    low = source_text.lower()
    needle = institution_name.lower()

    chunks = []

    for match in re.finditer(
        re.escape(needle),
        low,
    ):

        start = max(
            0,
            match.start() - radius
        )

        end = min(
            len(source_text),
            match.end() + radius
        )

        chunks.append(
            source_text[start:end]
        )

    return "\n".join(chunks)


# ============================================================
# PROGRAM IDENTIFICATION
# ============================================================

def _infer_program(
    evidence: str,
    specialization: str,
) -> str:

    source = _norm(evidence)
    target = _norm(specialization)

    if (
        target
        and target in source
        and "mba" in source
    ):

        return (
            f"MBA in {specialization}"
        )

    if (
        "mba" in source
        and "analytics" in source
    ):

        return (
            "MBA / Business Analytics-related program"
        )

    if (
        "pgdm" in source
        and "analytics" in source
    ):

        return (
            "PGDM / Analytics-related program"
        )

    return ""


# ============================================================
# LOCATION
# ============================================================

def _candidate_location(
    institution_name: str,
) -> str:

    return CITY_BY_NAME.get(
        institution_name,
        "",
    )


# ============================================================
# SOURCE TYPE
# ============================================================

def _source_type(url: str) -> str:

    if _is_blocked(url):
        return "secondary_or_community"

    d = _domain(url)

    if (
        ".edu.in" in d
        or ".ac.in" in d
        or ".edu." in d
        or ".ac." in d
    ):

        return "official_or_institutional"

    return "web_source"


# ============================================================
# SCORE CANDIDATE
# IMPORTANT:
# Exam acceptance is NOT awarded from generic listing-page
# text. It is verified later using college-specific research.
# ============================================================

def _score_candidate(
    candidate: dict[str, Any],
    profile: dict[str, Any],
) -> tuple[float, list[str]]:

    specialization = _norm(
        profile.get(
            "mba_specialization"
        )
    )

    locations = {
        _norm(x)
        for x in (
            profile.get(
                "preferred_locations"
            )
            or []
        )
        if _text(x)
    }

    career_goal = _norm(
        profile.get(
            "career_goal"
        )
    )

    budget = _parse_money(
        profile.get(
            "budget_max"
        )
    )

    priorities = (
        profile.get(
            "priorities"
        )
        or {}
    )

    placement_priority = _norm(
        priorities.get(
            "placement"
        )
    )

    evidence = _norm(
        candidate.get(
            "evidence_text"
        )
    )

    score = 0.0
    reasons = []

    # --------------------------------------------------------
    # 1. SPECIALIZATION — 30
    # --------------------------------------------------------

    if specialization:

        if specialization in evidence:

            score += 30

            reasons.append(
                "specialization match"
            )

        elif (
            "analytics"
            in specialization
            and
            "analytics"
            in evidence
        ):

            score += 18

            reasons.append(
                "analytics-related signal"
            )

        else:

            score += 3

    # --------------------------------------------------------
    # 2. LOCATION — 15
    # --------------------------------------------------------

    location = _norm(
        candidate.get(
            "location"
        )
    )

    if locations and location:

        if location in locations:

            score += 15

            reasons.append(
                "preferred location: "
                + candidate["location"]
            )

        else:

            score += 2

    else:

        # Unknown is not the same as wrong.
        score += 6

    # --------------------------------------------------------
    # 3. EXAM — 10 DISCOVERY SIGNAL ONLY
    # --------------------------------------------------------
    # We intentionally keep this conservative.
    # Detailed college research will verify actual acceptance
    # and historical cutoffs.

    exams = []

    for exam in (
        profile.get(
            "entrance_exams"
        )
        or []
    ):

        if (
            isinstance(exam, dict)
            and
            exam.get("exam")
        ):

            exams.append(
                _norm(exam["exam"])
            )

    direct_exam_signal = False

    if candidate.get(
        "official_url"
    ):

        for exam in exams:

            if (
    exam
    and
    re.search(
        rf"\b{re.escape(exam)}\b",
        evidence,
    )
):

                direct_exam_signal = True

                break

    if direct_exam_signal:

        score += 10

        reasons.append(
            "entrance exam signal from official source"
        )

    else:

        # Neutral when unverified.
        score += 5

    # --------------------------------------------------------
    # 4. CAREER FIT — 15
    # --------------------------------------------------------

    if career_goal:

        terms = [
            word
            for word in career_goal.split()
            if len(word) >= 4
        ]

        hits = sum(
            word in evidence
            for word in terms
        )

        if hits >= 2:

            score += 15

            reasons.append(
                "career relevance signal"
            )

        elif hits:

            score += 8

            reasons.append(
                "partial career relevance"
            )

        else:

            score += 4

    else:

        score += 5

    # --------------------------------------------------------
    # 5. BUDGET — 10
    # --------------------------------------------------------
    # Discovery-stage fees are only signals.
    # Final verified fees are handled later.

    fee = candidate.get(
        "candidate_fee"
    )

    if (
        budget is not None
        and
        isinstance(
            fee,
            (int, float)
        )
    ):

        if fee <= budget:

            score += 10

            reasons.append(
                "within budget signal"
            )

        elif fee <= budget * 1.15:

            score += 5

            reasons.append(
                "slightly above budget"
            )

        else:

            score -= 5

            reasons.append(
                "above budget signal"
            )

    else:

        score += 5

    # --------------------------------------------------------
    # 6. PLACEMENT PRIORITY — 5
    # --------------------------------------------------------

    placement_terms = [
        "placement",
        "placements",
        "average package",
        "median package",
        "highest package",
        "recruiter",
        "recruiters",
    ]

    placement_hits = sum(
        term in evidence
        for term in placement_terms
    )

    if placement_priority == "high":

        if placement_hits >= 2:

            score += 5

            reasons.append(
                "strong placement information signal"
            )

        elif placement_hits == 1:

            score += 3

            reasons.append(
                "placement information signal"
            )

        else:

            score += 1

    else:

        score += 2

    # --------------------------------------------------------
    # 7. SOURCE / IDENTITY CONFIDENCE — 15
    # --------------------------------------------------------

    source_count = len(
        candidate.get(
            "source_urls"
        )
        or []
    )

    official = bool(
        candidate.get(
            "official_url"
        )
    )

    if official:

        score += 15

        reasons.append(
            "official source found"
        )

    elif source_count >= 3:

        score += 10

        reasons.append(
            "multiple discovery sources"
        )

    elif source_count >= 2:

        score += 7

    else:

        score += 3

    score = max(
        0.0,
        min(
            100.0,
            score
        )
    )

    return (
        round(score, 2),
        reasons,
    )


# ============================================================
# MAIN FUNCTION
# ============================================================

def discover_candidates(
    student_profile: dict[str, Any],
    research_plan: dict[str, Any] | None = None,
    candidate_results: list[dict[str, Any]] | None = None,
    web_results: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:

    profile = (
        student_profile
        or {}
    )

    raw_results = (
        candidate_results
        if candidate_results is not None
        else (
            web_results
            or []
        )
    )

    flattened = _flatten_results(
        raw_results
    )

    # --------------------------------------------------------
    # Deduplicate identical URLs
    # --------------------------------------------------------

    unique_sources = {}

    for result in flattened:

        url = _text(
            result.get(
                "url"
            )
        )

        if not url:
            continue

        key = (
            url
            .rstrip("/")
            .lower()
        )

        if key not in unique_sources:
            unique_sources[key] = result

    # --------------------------------------------------------
    # Institution registry
    # --------------------------------------------------------

    registry: dict[
        str,
        dict[str, Any]
    ] = {}

    specialization = (
        _text(
            profile.get(
                "mba_specialization"
            )
        )
        or "MBA"
    )

    for result in unique_sources.values():

        url = _text(
            result.get(
                "url"
            )
        )

        title = _text(
            result.get(
                "title"
            )
        )

        body = _text(
            result.get(
                "snippet"
            )
            or
            result.get(
                "content"
            )
            or
            result.get(
                "raw_content"
            )
        )

        source_text = (
            f"{title}\n{body}"
        )

        # ----------------------------------------------------
        # Direct official source
        # ----------------------------------------------------

        direct_name = _official_name(
            url,
            title,
            body,
        )

        if direct_name:

            names = [
                direct_name
            ]

        else:

            # ------------------------------------------------
            # Listing/search source
            # Extract explicit institution names contained
            # in the result text.
            # ------------------------------------------------

            names = _extract_known_names(
                source_text
            )

        for institution_name in names:

            institution_name = (
                institution_name.strip()
            )

            if not institution_name:
                continue

            if (
                _norm(
                    institution_name
                )
                in {
                    _norm(x)
                    for x in GENERIC_BAD_NAMES
                }
            ):
                continue

            # -----------------------------------------------
            # Candidate-specific local evidence
            # -----------------------------------------------

            local_evidence = _mention_window(
                source_text,
                institution_name,
            )

            local_normalized = _norm(
                local_evidence
            )

            # Do not treat a random navigation/menu occurrence
            # as a real MBA candidate.
            relevant = (
                "business analytics"
                in local_normalized
                or
                "mba"
                in local_normalized
                or
                "pgdm"
                in local_normalized
                or
                "analytics"
                in local_normalized
            )

            if not relevant:
                continue

            key = _norm(
                institution_name
            )

            entry = registry.setdefault(
                key,
                {
                    "institution":
                        institution_name,

                    "program":
                        "",

                    "location":
                        _candidate_location(
                            institution_name
                        ),

                    "official_url":
                        "",

                    "official_domain":
                        "",

                    "source_urls":
                        [],

                    "source_types":
                        [],

                    "evidence_texts":
                        [],

                    "best_search_score":
                        0.0,

                    "candidate_fee":
                        None,
                },
            )

            # -----------------------------------------------
            # Program signal
            # -----------------------------------------------

            program = _infer_program(
                local_evidence,
                specialization,
            )

            if (
                program
                and
                not entry["program"]
            ):

                entry["program"] = (
                    program
                )

            # -----------------------------------------------
            # Source tracking
            # -----------------------------------------------

            if (
                url
                not in entry["source_urls"]
            ):

                entry["source_urls"].append(
                    url
                )

            stype = _source_type(
                url
            )

            if (
                stype
                not in entry["source_types"]
            ):

                entry["source_types"].append(
                    stype
                )

            entry[
                "evidence_texts"
            ].append(
                local_evidence
            )

            raw_score = (
                result.get(
                    "search_score"
                )
            )

            if not isinstance(
                raw_score,
                (int, float),
            ):

                raw_score = (
                    result.get(
                        "score"
                    )
                )

            if isinstance(
                raw_score,
                (int, float),
            ):

                entry[
                    "best_search_score"
                ] = max(
                    entry[
                        "best_search_score"
                    ],
                    float(
                        raw_score
                    ),
                )

            # -----------------------------------------------
            # Official source
            # -----------------------------------------------

            if (
                direct_name
                and
                not entry[
                    "official_url"
                ]
            ):

                entry[
                    "official_url"
                ] = url

                entry[
                    "official_domain"
                ] = _domain(
                    url
                )

    # --------------------------------------------------------
    # Final scoring
    # --------------------------------------------------------

    scored = []

    for entry in registry.values():

        entry[
            "evidence_text"
        ] = " ".join(
            entry.pop(
                "evidence_texts",
                [],
            )
        )

        selection_score, reasons = (
            _score_candidate(
                entry,
                profile,
            )
        )

        entry[
            "selection_score"
        ] = selection_score

        entry[
            "selection_reasons"
        ] = reasons

        entry[
            "needs_detailed_research"
        ] = True

        # Stable names for n8n downstream use.
        entry[
            "institution_name"
        ] = entry[
            "institution"
        ]

        entry[
            "program_name"
        ] = entry[
            "program"
        ]

        scored.append(
            entry
        )

    # --------------------------------------------------------
    # Rank candidates
    # --------------------------------------------------------

    scored.sort(
        key=lambda item: (
            float(
                item.get(
                    "selection_score",
                    0
                )
            ),

            bool(
                item.get(
                    "official_url"
                )
            ),

            len(
                item.get(
                    "source_urls",
                    []
                )
            ),

            float(
                item.get(
                    "best_search_score",
                    0
                )
            ),
        ),
        reverse=True,
    )

    selected = scored[
        :DEEP_RESEARCH_LIMIT
    ]

    return {
        "status":
            "success",

        "student_profile":
            profile,

        "candidate_count":
            len(scored),

        "selected_count":
            len(selected),

        "deep_research_limit":
            DEEP_RESEARCH_LIMIT,

        "selection_method":
            "profile-aware deterministic discovery",

        "candidates":
            selected,

        "all_scored_candidates":
            scored,
    }