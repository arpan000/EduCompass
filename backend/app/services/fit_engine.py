from __future__ import annotations

import re
from typing import Any
from urllib.parse import urlparse


# ============================================================
# EDUCOMPASS — FINAL FIT ENGINE
#
# 20 criteria
# Missing evidence is NOT treated as zero.
# Available evidence is normalized over available weight.
# Discovery score is used only as a small prior.
# ============================================================


CRITERION_WEIGHTS = {
    1: 5,
    2: 4,
    3: 3,
    4: 12,
    5: 10,
    6: 5,
    7: 8,
    8: 7,
    9: 4,
    10: 4,
    11: 3,
    12: 4,
    13: 1,
    14: 6,
    15: 2,
    16: 2,
    17: 5,
    18: 1,
    19: 2,
    20: 12,
}


CRITERION_NAMES = {
    1: "College/University Reputation",
    2: "MBA Accreditation & Approvals",
    3: "NIRF Ranking",
    4: "Placement Record",
    5: "ROI",
    6: "Recruiting Companies",
    7: "Program/Branch Specialization",
    8: "Curriculum",
    9: "Faculty Quality",
    10: "Internship Opportunities",
    11: "Alumni Network",
    12: "Location",
    13: "Batch Size",
    14: "Admission Criteria",
    15: "Selection Process",
    16: "Infrastructure & Facilities",
    17: "Industry Exposure",
    18: "Student Reviews",
    19: "Placement Transparency",
    20: "Career Fit",
}


# ------------------------------------------------------------
# HELPERS
# ------------------------------------------------------------

def clean(value: Any) -> str:
    return str(value or "").strip()


def norm(value: Any) -> str:
    text = clean(value).lower()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def get_domain(url: str) -> str:
    try:
        host = urlparse(clean(url)).netloc.lower()
        if host.startswith("www."):
            host = host[4:]
        return host
    except Exception:
        return ""


def get_criterion(
    college: dict[str, Any],
    number: int,
) -> dict[str, Any]:

    criteria = college.get("criteria") or {}

    value = criteria.get(str(number))

    if value is None:
        value = criteria.get(number)

    if not isinstance(value, dict):
        return {
            "status": "NOT_VERIFIED",
            "confidence": "LOW",
            "value": None,
            "sources": [],
            "note": "",
        }

    return value


def status_score(
    criterion: dict[str, Any],
) -> float | None:

    status = clean(
        criterion.get("status")
    ).upper()

    confidence = clean(
        criterion.get("confidence")
    ).upper()

    # Missing evidence is excluded.
    if status == "NOT_VERIFIED":
        return None

    if status == "VERIFIED":
        if confidence == "HIGH":
            return 1.00

        if confidence == "MEDIUM":
            return 0.85

        return 0.70

    if status == "PARTIAL":
        if confidence == "HIGH":
            return 0.70

        if confidence == "MEDIUM":
            return 0.55

        return 0.40

    return None


def extract_lakh(
    value: Any,
) -> float | None:

    if isinstance(value, (int, float)):
        return float(value)

    text = clean(value).lower()

    match = re.search(
        r"(\d+(?:\.\d+)?)\s*(lakh|lakhs|crore|crores|lpa)",
        text,
    )

    if not match:
        return None

    number = float(
        match.group(1)
    )

    unit = match.group(2)

    if unit in {
        "crore",
        "crores",
    }:
        return number * 100

    return number


# ------------------------------------------------------------
# SPECIALIZED FIT VALUES
# ------------------------------------------------------------

def program_fit(
    student_profile: dict[str, Any],
    college: dict[str, Any],
) -> float | None:

    target = norm(
        student_profile.get(
            "mba_specialization"
        )
    )

    program = norm(
        college.get("program")
    )

    if not target or not program:
        return None

    if target in program:
        return 1.0

    return 0.0


def location_fit(
    student_profile: dict[str, Any],
    college: dict[str, Any],
) -> float | None:

    preferred = [
        norm(x)
        for x in (
            student_profile.get(
                "preferred_locations"
            )
            or []
        )
    ]

    location = norm(
        college.get("location")
    )

    if not preferred:
        return None

    if not location:
        return None

    for item in preferred:

        if (
            item in location
            or location in item
        ):
            return 1.0

    return 0.0


def budget_lakh(
    value: Any,
) -> float | None:

    if value is None:
        return None

    if isinstance(
        value,
        (int, float),
    ):
        # Supports raw rupees.
        if value > 1000:
            return float(value) / 100000
        return float(value)

    text = clean(value)

    match = re.search(
        r"(\d+(?:\.\d+)?)",
        text,
    )

    if not match:
        return None

    number = float(
        match.group(1)
    )

    if "crore" in text.lower():
        return number * 100

    if "lakh" in text.lower():
        return number

    # ₹14 lakh etc.
    if "₹" in text or "inr" in text.lower():
        if number > 100:
            return number / 100000

    return number


def budget_fit(
    student_profile: dict[str, Any],
    college: dict[str, Any],
) -> float | None:

    budget = budget_lakh(
        student_profile.get(
            "budget_max"
        )
    )

    criterion5 = get_criterion(
        college,
        5,
    )

    value = criterion5.get(
        "value"
    )

    if not isinstance(
        value,
        dict,
    ):
        return None

    fee = value.get(
        "program_fee_lakh"
    )

    fee = extract_lakh(
        fee
    )

    if budget is None or fee is None:
        return None

    if fee <= budget:
        return 1.0

    if fee <= budget * 1.10:
        return 0.50

    return 0.0


def admission_fit(
    student_profile: dict[str, Any],
    college: dict[str, Any],
) -> float | None:

    criterion14 = get_criterion(
        college,
        14,
    )

    value = criterion14.get(
        "value"
    )

    if not isinstance(
        value,
        dict,
    ):
        return None

    classification = clean(
        value.get(
            "competitiveness"
        )
    ).upper()

    mapping = {
        "STRONG": 1.00,
        "TARGET": 0.90,
        "REACH": 0.55,
        "CUTOFF NOT VERIFIED": 0.60,
        "SCORE NOT AVAILABLE": 0.60,
        "EXAM NOT ACCEPTED": 0.15,
        "": 0.60,
    }

    return mapping.get(
        classification,
        0.60,
    )


def roi_fit(
    college: dict[str, Any],
) -> float | None:

    criterion5 = get_criterion(
        college,
        5,
    )

    value = criterion5.get(
        "value"
    )

    if not isinstance(
        value,
        dict,
    ):
        return None

    fee = extract_lakh(
        value.get(
            "program_fee_lakh"
        )
    )

    salary = extract_lakh(
        value.get(
            "average_salary_lakh"
        )
    )

    if (
        fee is None
        or salary is None
        or fee <= 0
        or salary <= 0
    ):
        return None

    multiple = salary / fee

    if multiple >= 2.0:
        return 1.0

    if multiple >= 1.5:
        return 0.90

    if multiple >= 1.0:
        return 0.75

    if multiple >= 0.75:
        return 0.55

    return 0.35


# ------------------------------------------------------------
# PERSONALIZED WEIGHTS
# ------------------------------------------------------------

def personalized_weights(
    priorities: dict[str, Any],
) -> dict[int, float]:

    weights = {
        key: float(value)
        for key, value in
        CRITERION_WEIGHTS.items()
    }

    if not isinstance(
        priorities,
        dict,
    ):
        return weights

    placement = clean(
        priorities.get(
            "placement"
        )
    ).lower()

    roi = clean(
        priorities.get(
            "roi"
        )
    ).lower()

    location = clean(
        priorities.get(
            "location"
        )
    ).lower()

    career = clean(
        priorities.get(
            "career_fit"
        )
    ).lower()

    if placement == "high":
        weights[4] *= 1.35
        weights[6] *= 1.25
        weights[19] *= 1.25

    elif placement == "medium":
        weights[4] *= 1.15
        weights[6] *= 1.10

    if roi == "high":
        weights[5] *= 1.35
        weights[4] *= 1.15

    elif roi == "medium":
        weights[5] *= 1.15

    if location == "high":
        weights[12] *= 1.35

    elif location == "medium":
        weights[12] *= 1.15

    if career == "high":
        weights[20] *= 1.40
        weights[7] *= 1.20
        weights[8] *= 1.15
        weights[17] *= 1.15

    elif career == "medium":
        weights[20] *= 1.20

    return weights


# ------------------------------------------------------------
# DISCOVERY PRIOR
# ------------------------------------------------------------

def discovery_prior(
    college: dict[str, Any],
) -> float:

    value = college.get(
        "selection_score"
    )

    if not isinstance(
        value,
        (int, float),
    ):
        return 0.50

    # Current discovery score is around 0–100.
    return max(
        0.0,
        min(
            1.0,
            float(value) / 100,
        ),
    )


# ------------------------------------------------------------
# MAIN CANDIDATE SCORE
# ------------------------------------------------------------

def score_candidate(
    student_profile: dict[str, Any],
    college: dict[str, Any],
) -> dict[str, Any]:

    criteria = {
        number:
            get_criterion(
                college,
                number,
            )
        for number in range(
            1,
            21,
        )
    }

    weights = personalized_weights(
        student_profile.get(
            "priorities"
        )
        or {}
    )

    values: dict[int, float | None] = {}

    # Base evidence score.
    for number in range(
        1,
        21,
    ):

        values[number] = status_score(
            criteria[number]
        )

    # Personalized replacements.
    values[5] = roi_fit(
        college
    )

    values[7] = program_fit(
        student_profile,
        college,
    )

    values[12] = location_fit(
        student_profile,
        college,
    )

    values[14] = admission_fit(
        student_profile,
        college,
    )

    # --------------------------------------------------------
    # Evidence-normalized weighted score
    # --------------------------------------------------------

    available_weight = 0.0
    weighted_score = 0.0

    for number, value in values.items():

        if value is None:
            continue

        weight = weights[
            number
        ]

        available_weight += weight

        weighted_score += (
            value * weight
        )

    # --------------------------------------------------------
    # Coverage
    # --------------------------------------------------------

    verified = sum(
        1
        for number in range(
            1,
            21,
        )
        if criteria[number].get(
            "status"
        ) == "VERIFIED"
    )

    partial = sum(
        1
        for number in range(
            1,
            21,
        )
        if criteria[number].get(
            "status"
        ) == "PARTIAL"
    )

    not_verified = (
        20
        - verified
        - partial
    )

    coverage = (
        (
            verified
            + partial
        )
        / 20
        * 100
    )

    if available_weight > 0:

        evidence_score = (
            weighted_score
            / available_weight
            * 100
        )

    else:

        evidence_score = 0.0

    # Prevent sparse evidence from producing an
    # unrealistically high final score.
    coverage_factor = (
        0.55
        + (coverage / 100.0) * 0.45
    )
    # Discovery prior
    #
    # Only 10% influence.
    # --------------------------------------------------------

    prior = (
        discovery_prior(
            college
        )
        * 100
    )

    final_score = (
        evidence_score
        * 0.90
        * coverage_factor
        + prior
        * 0.10
    )

    # --------------------------------------------------------
    # Admission penalty
    #
    # A college not accepting the student's taken exam
    # is not automatically removed because flexibility may
    # allow another exam, but it is strongly penalized.
    # --------------------------------------------------------

    raw_admission_value = criteria[14].get("value")

    if isinstance(raw_admission_value, dict):
        admission_value = raw_admission_value

        admission_status = clean(
            admission_value.get(
                "competitiveness"
            )
        ).upper()

    else:
        admission_text = clean(
            raw_admission_value
        ).lower()

        admission_value = {}

        if "exam not accepted" in admission_text:
            admission_status = "EXAM NOT ACCEPTED"

        elif "strong" in admission_text:
            admission_status = "STRONG"

        elif "target" in admission_text:
            admission_status = "TARGET"

        elif "reach" in admission_text:
            admission_status = "REACH"

        elif (
            "accepted/mentioned exams"
            in admission_text
            or
            "accepted exams"
            in admission_text
        ):
            admission_status = "CUTOFF NOT VERIFIED"

        else:
            admission_status = "UNKNOWN"

    if admission_status == "EXAM NOT ACCEPTED":

        final_score *= 0.80

    # --------------------------------------------------------
    # Location penalty
    #
    # Preferred location is meaningful but not always a hard
    # filter.
    # --------------------------------------------------------

    loc = location_fit(
        student_profile,
        college,
    )

    if loc == 0.0:
        final_score *= 0.92

    # --------------------------------------------------------
    # Strengths / tradeoffs
    # --------------------------------------------------------

    strengths = []
    tradeoffs = []

    if values[7] == 1.0:
        strengths.append(
            "Requested MBA specialization matches."
        )

    if values[12] == 1.0:
        strengths.append(
            "Program is in a preferred location."
        )

    if values[5] == 1.0:
        strengths.append(
            "Available fee and salary evidence indicates strong ROI."
        )

    if values[4] is not None:
        strengths.append(
            "Placement evidence is available."
        )

    if admission_status == "STRONG":
        strengths.append(
            "Student percentile is above the available historical cutoff."
        )

    if admission_status == "TARGET":
        strengths.append(
            "Student percentile is around the available historical cutoff."
        )

    if admission_status == "REACH":
        tradeoffs.append(
            "Student percentile is below the available historical cutoff."
        )

    if admission_status == "EXAM NOT ACCEPTED":
        tradeoffs.append(
            "The student's taken exam is not accepted for this program; an alternate exam may be required."
        )

    if loc == 0.0:
        tradeoffs.append(
            "Program is outside the stated preferred locations."
        )

    if values[5] is None:
        tradeoffs.append(
            "Insufficient fee and salary evidence for ROI calculation."
        )

    if coverage < 40:
        tradeoffs.append(
            "Research coverage is limited; several criteria are not publicly verified."
        )

    missing = [
        CRITERION_NAMES[number]
        for number in range(
            1,
            21,
        )
        if values[number] is None
    ]

    return {
        "candidate_index":
            college.get(
                "candidate_index"
            ),

        "institution":
            college.get(
                "institution"
            ),

        "program":
            college.get(
                "program"
            ),

        "location":
            college.get(
                "location"
            ),

        "official_url":
            college.get(
                "official_url"
            ),

        "official_domain":
            college.get(
                "official_domain"
            ),

        "discovery_selection_score":
            college.get(
                "selection_score"
            ),

        "fit_score":
            round(
                final_score,
                2,
            ),

        "evidence_score":
            round(
                evidence_score,
                2,
            ),

        "evidence_coverage":
            round(
                coverage,
                2,
            ),

        "verified_count":
            verified,

        "partial_count":
            partial,

        "not_verified_count":
            not_verified,

        "cutoff_competitiveness":
            admission_status
            or "UNKNOWN",

        "criterion_scores":
            {
                str(number):
                    values[number]
                for number in range(
                    1,
                    21,
                )
            },

        "criteria":
            criteria,

        "weights":
            weights,

        "strengths":
            strengths,

        "tradeoffs":
            tradeoffs,

        "missing_criteria":
            missing,

        "evidence":
            college.get(
                "evidence"
            )
            or [],
    }


# ------------------------------------------------------------
# FINAL RANKING
# ------------------------------------------------------------

def run_fit_engine(
    student_profile: dict[str, Any],
    verified_candidates: list[dict[str, Any]],
) -> dict[str, Any]:

    ranked = []

    for college in (
        verified_candidates
        or []
    ):

        if not isinstance(
            college,
            dict,
        ):
            continue

        ranked.append(
            score_candidate(
                student_profile,
                college,
            )
        )

    ranked.sort(
        key=lambda item: (
            item["fit_score"],
            item["evidence_coverage"],
            item["evidence_score"],
        ),
        reverse=True,
    )

    for rank, item in enumerate(
        ranked,
        start=1,
    ):
        item["final_rank"] = rank

    return {
        "status":
            "success",

        "student_profile":
            student_profile,

        "candidate_count":
            len(ranked),

        "top_10_count":
            min(
                10,
                len(ranked),
            ),

        "top_10":
            ranked[:10],

        "all_ranked_candidates":
            ranked,

        "criterion_weights":
            CRITERION_WEIGHTS,

        "criterion_names":
            CRITERION_NAMES,
    }
