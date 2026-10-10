from __future__ import annotations

import re
from typing import Any
from urllib.parse import urlparse

from app.services.fit_engine import run_fit_engine


THIRD_PARTY_DOMAINS = {
    "collegedunia.com",
    "careers360.com",
    "shiksha.com",
    "mbauniverse.com",
}

KNOWN_OFFICIAL_DOMAINS = {
    "Indira University": "indirauniversity.edu.in",
    "MIT-WPU": "mitwpu.edu.in",
    "IIM Bangalore": "iimb.ac.in",
    "Amrita Vishwa Vidyapeetham": "amrita.edu",
    "SCMHRD Pune": "scmhrd.edu",
    "JSPM University": "jspmuni.ac.in",
    "New Horizon College of Engineering": "newhorizoncollegeofengineering.in",
    "Dayananda Sagar Business School": "dsbs.edu.in",
    "Christ University": "christuniversity.in",
    "JAGSoM": "jagsom.edu.in",
    "BITS Pilani WILP": "bits-pilani-wilp.ac.in",
    "NMIMS": "nmims.edu",
}

ALIASES = {
    "Indira University": ["indira university", "indira school of business"],
    "MIT-WPU": ["mit-wpu", "mit wpu", "mit world peace university"],
    "IIM Bangalore": ["iim bangalore", "indian institute of management bangalore", "iimb"],
    "Amrita Vishwa Vidyapeetham": ["amrita vishwa vidyapeetham", "amrita school of business", "amrita"],
    "SCMHRD Pune": ["scmhrd", "symbiosis centre for management and human resource development"],
    "JSPM University": ["jspm university", "jspm"],
    "New Horizon College of Engineering": ["new horizon college of engineering", "nhce"],
    "Dayananda Sagar Business School": ["dayananda sagar business school", "dsbs", "dayananda sagar"],
    "Christ University": ["christ university", "christ (deemed to be university)", "christ deemed to be university"],
    "JAGSoM": ["jagsom", "jagdish sheth school of management"],
    "BITS Pilani WILP": ["bits pilani", "bits wilp", "work integrated learning programmes", "wilp"],
    "NMIMS": ["nmims", "narsee monjee institute of management studies", "svkm's narsee monjee"],
}

EXAMS = ["CAT", "XAT", "SNAP", "CMAT", "MAT", "GMAT", "NMAT", "MAH-CET", "MAH MBA CET", "ATMA", "GRE", "Indira CET", "CUET PG"]

COMPANIES = [
    "Accenture", "Amazon", "Deloitte", "EY", "KPMG", "PwC", "IBM", "TCS", "Infosys",
    "Wipro", "Cognizant", "Capgemini", "Microsoft", "Google", "Morgan Stanley", "ICICI Bank",
    "HDFC Bank", "Axis Bank", "Barclays", "Citi", "Mastercard", "Tech Mahindra", "Larsen & Toubro",
    "L&T", "Bajaj", "Reliance", "Asian Paints", "Hindustan Unilever", "HUL", "Oracle", "Philips",
    "Godrej", "Juspay", "SEBI", "NSE", "Volkswagen",
]


def clean(value: Any) -> str:
    return str(value or "").strip()


def norm(value: Any) -> str:
    text = clean(value).lower()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def domain(url: str) -> str:
    try:
        host = urlparse(clean(url)).netloc.lower()
        return host[4:] if host.startswith("www.") else host
    except Exception:
        return ""


def host_matches(host: str, allowed: str) -> bool:
    return host == allowed or host.endswith("." + allowed)


def text_blob(result: dict[str, Any]) -> str:
    return " ".join(
        x for x in [
            clean(result.get("title")),
            clean(result.get("content")),
        ] if x
    )


def program_specific(blob: str, program: str) -> bool:
    p = norm(program)
    b = norm(blob)
    if "business analytics" in p:
        return "business analytics" in b
    words = [w for w in p.split() if len(w) > 3]
    return sum(w in b for w in words) >= max(1, min(2, len(words)))


def identity_match(blob: str, institution: str) -> bool:
    b = norm(blob)
    aliases = ALIASES.get(institution, [institution])
    for alias in aliases:
        a = norm(alias)
        if a and a in b:
            return True
    return False


def relevant_results(college: dict[str, Any], bucket_name: str, allow_generic_official: bool = True) -> list[tuple[dict[str, Any], str]]:
    institution = clean(college.get("institution"))
    program = clean(college.get("program"))
    official_domain = clean(college.get("official_domain")) or KNOWN_OFFICIAL_DOMAINS.get(institution, "")

    bucket = college.get(bucket_name) or []
    out: list[tuple[dict[str, Any], str]] = []

    for research in bucket:
        for result in research.get("results") or []:
            if not isinstance(result, dict):
                continue
            url = clean(result.get("url"))
            host = domain(url)
            blob = text_blob(result)
            src_type = clean(research.get("source_type"))

            if src_type == "official":
                if official_domain and not host_matches(host, official_domain):
                    continue
                # Official pages can be institution-wide when the field is institution-wide.
                out.append((result, "official"))

            elif src_type == "third_party":
                if not any(host_matches(host, d) for d in THIRD_PARTY_DOMAINS):
                    continue
                if not identity_match(blob, institution):
                    continue
                # For program-level numbers, require program mention when available.
                if program and "business analytics" in norm(program) and not program_specific(blob, program):
                    continue
                out.append((result, "third_party"))

    # Highest relevance first: program-specific, then source authority, then Tavily score.
    out.sort(
        key=lambda pair: (
            1 if program_specific(text_blob(pair[0]), program) else 0,
            1 if pair[1] == "official" else 0,
            float(pair[0].get("score") or 0),
        ),
        reverse=True,
    )
    return out


def first_excerpt(results: list[tuple[dict[str, Any], str]], keywords: list[str], max_len: int = 420) -> tuple[str, str, str] | None:
    for result, src_type in results:
        blob = text_blob(result)
        low = blob.lower()
        if any(k.lower() in low for k in keywords):
            return clean(blob)[:max_len], clean(result.get("url")), src_type
    return None


def source_urls(results: list[tuple[dict[str, Any], str]]) -> list[str]:
    seen = []
    for result, _ in results:
        url = clean(result.get("url"))
        if url and url not in seen:
            seen.append(url)
    return seen


def money_lakh_values(text: str) -> list[float]:
    out: list[float] = []
    for m in re.finditer(r"₹?\s*(\d+(?:\.\d+)?)\s*(lakh|lakhs|lac|lacs|crore|crores|LPA)\b", text, re.I):
        n = float(m.group(1))
        unit = m.group(2).lower()
        if unit.startswith("crore"):
            n *= 100
        out.append(n)
    return out


def parse_amount_to_lakh(number_text: str, unit: str | None = None) -> float:
    n = float(number_text.replace(",", ""))
    if unit:
        u = unit.lower()
        if u in {"lakh", "lakhs", "lac", "lacs"}:
            return n
        if u in {"crore", "crores"}:
            return n * 100
        if u == "lpa":
            return n
    if n > 1000:
        return n / 100000
    return n


def parse_amount_to_lakh(number_text: str, unit: str | None = None) -> float:
    n = float(number_text.replace(",", ""))
    if unit:
        u = unit.lower()
        if u in {"lakh", "lakhs", "lac", "lacs"}:
            return n
        if u in {"crore", "crores"}:
            return n * 100
        if u == "lpa":
            return n
    if n > 1000:
        return n / 100000
    return n


def fee_value(text: str, program: str = "") -> float | None:
    p = norm(program)
    candidates: list[float] = []

    # Strongest pattern: explicit table/row tied to Business Analytics.
    if "business analytics" in p:
        row_patterns = [
            r"(?:\|\s*)MBA\s*\|\s*Business Analytics\s*\|[^\n]{0,100}?₹\s*(\d{1,3}(?:,\d{2,3})+|\d+)\s*(lakh|lakhs|lac|lacs)?",
            r"Business Analytics\s*\|[^\n]{0,100}?₹\s*(\d{1,3}(?:,\d{2,3})+|\d+)\s*(lakh|lakhs|lac|lacs)?",
        ]
        for pat in row_patterns:
            for m in re.finditer(pat, text, re.I):
                candidates.append(parse_amount_to_lakh(m.group(1), m.group(2)))

        # Explicit sentence tied to the requested program.
        for pat in [
            r"(?:MBA\s+in\s+Business Analytics|MBA\s+Business Analytics|Business Analytics)[^₹\n]{0,180}?₹\s*(\d{1,3}(?:,\d{2,3})+|\d+)\s*(lakh|lakhs|lac|lacs)?",
        ]:
            for m in re.finditer(pat, text, re.I):
                candidates.append(parse_amount_to_lakh(m.group(1), m.group(2)))

    # Generic total-fee statements only as fallback.
    for pat in [
        r"(?:total\s+(?:program|programme)\s+fees?|tuition\s+fees?|fee\s+structure|total\s+fees?)[^₹\n]{0,100}?₹?\s*(\d{1,3}(?:,\d{2,3})+|\d+(?:\.\d+)?)\s*(lakh|lakhs|lac|lacs)",
        r"₹\s*(\d{1,3}(?:,\d{2,3})+|\d+)\s*(lakh|lakhs|lac|lacs)\s*(?:total\s+(?:program|programme)\s+fees?|fees?)",
    ]:
        for m in re.finditer(pat, text, re.I):
            candidates.append(parse_amount_to_lakh(m.group(1), m.group(2)))

    if candidates:
        # Prefer an explicit program-linked value; when only generic values exist,
        # choose the first explicit total-fee value rather than a marketing range.
        return candidates[0]

    return None

def salary_value(text: str, label: str) -> float | None:
    pats = [
        rf"{re.escape(label)}\D{{0,80}}(?:₹\s*)?(\d+(?:\.\d+)?)\s*(LPA|lakh|lakhs)",
        rf"{re.escape(label)}\D{{0,80}}(?:₹\s*)?(\d+(?:\.\d+)?)\s*LPA",
    ]
    for pat in pats:
        m = re.search(pat, text, re.I)
        if m:
            return float(m.group(1))
    return None


def placement_metrics(results: list[tuple[dict[str, Any], str]]) -> dict[str, Any]:
    best: dict[str, Any] = {
        "average_salary_lakh": None,
        "median_salary_lakh": None,
        "highest_salary_lakh": None,
        "placement_percentage": None,
        "scope": None,
        "sources": [],
    }

    for result, src in results:
        blob = text_blob(result)
        prog = program_specific(blob, "MBA in Business Analytics")
        avg = salary_value(blob, "average") or salary_value(blob, "avg")
        median = salary_value(blob, "median")
        highest = salary_value(blob, "highest")
        if avg is None:
            m = re.search(r"(?:average|avg)\s*(?:CTC|package|salary)?\D{0,60}(\d+(?:\.\d+)?)\s*LPA", blob, re.I)
            if m:
                avg = float(m.group(1))
        if highest is None:
            m = re.search(r"highest\s*(?:CTC|package|salary)?\D{0,60}(\d+(?:\.\d+)?)\s*LPA", blob, re.I)
            if m:
                highest = float(m.group(1))
        if median is None:
            m = re.search(r"median\s*(?:CTC|package|salary)?\D{0,60}(\d+(?:\.\d+)?)\s*LPA", blob, re.I)
            if m:
                median = float(m.group(1))

        # Do not interpret "100% placement assistance" as placement percentage.
        pm = re.search(r"(?<!assistance)(?<!of)\b(\d{2,3})\s*%\s*(?:of\s+)?(?:students\s+)?(?:placed|placement)\b", blob, re.I)
        placement_pct = float(pm.group(1)) if pm else None

        if any(v is not None for v in [avg, median, highest, placement_pct]):
            best = {
                "average_salary_lakh": avg,
                "median_salary_lakh": median,
                "highest_salary_lakh": highest,
                "placement_percentage": placement_pct,
                "scope": "program" if prog else "institution",
                "sources": source_urls([(result, src)]),
            }
            # Prefer program-specific evidence; otherwise keep first good official result.
            if prog:
                return best
    return best


def cutoff_history(results: list[tuple[dict[str, Any], str]]) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    for result, src in results:
        blob = text_blob(result)
        if "cutoff" not in blob.lower():
            continue
        for year in (2025, 2024):
            # Search both directions around exam/year and require cutoff context.
            for exam in EXAMS:
                exam_pat = re.escape(exam)
                patterns = [
                    rf"{year}[^.\n]{{0,180}}?{exam_pat}[^.\n]{{0,120}}?(\d{{2,3}}(?:\.\d+)?)\s*(?:%|percentile)",
                    rf"{exam_pat}[^.\n]{{0,180}}?{year}[^.\n]{{0,120}}?(\d{{2,3}}(?:\.\d+)?)\s*(?:%|percentile)",
                    rf"(?:{exam_pat})\s*(?:cutoff|cut off)[^.\n]{{0,100}}?{year}[^.\n]{{0,100}}?(\d{{2,3}}(?:\.\d+)?)\s*(?:%|percentile)",
                    rf"{year}[^.\n]{{0,120}}?(?:cutoff|cut off)[^.\n]{{0,120}}?{exam_pat}[^.\n]{{0,80}}?(\d{{2,3}}(?:\.\d+)?)\s*(?:%|percentile)",
                ]
                value = None
                for pat in patterns:
                    m = re.search(pat, blob, re.I)
                    if m:
                        value = float(m.group(1))
                        break
                if value is not None:
                    rec = {"year": year, "exam": exam, "percentile": value, "source_type": src, "url": clean(result.get("url"))}
                    if rec not in found:
                        found.append(rec)

            # Raw-score cutoffs if no percentile match was found for the year/exam.
            for exam in EXAMS:
                patterns = [
                    rf"{year}[^.\n]{{0,160}}?{exam}[^.\n]{{0,100}}?(?:cutoff|cut off)[^0-9]{{0,40}}(\d{{2,4}})\b",
                    rf"{exam}[^.\n]{{0,140}}?(?:cutoff|cut off)[^0-9]{{0,60}}{year}[^0-9]{{0,40}}(\d{{2,4}})\b",
                ]
                for pat in patterns:
                    m = re.search(pat, blob, re.I)
                    if m:
                        value = float(m.group(1))
                        # Avoid accidental years and implausibly huge percentile values.
                        if 0 < value < 100 and not any(x["year"] == year and x["exam"] == exam for x in found):
                            found.append({"year": year, "exam": exam, "percentile": value, "source_type": src, "url": clean(result.get("url"))})
                        break
    # One value per year/exam: official first, then third-party, then page order.
    found.sort(key=lambda x: (x["year"], x["exam"], 0 if x["source_type"] == "official" else 1))
    unique = []
    seen = set()
    for x in found:
        key = (x["year"], x["exam"])
        if key not in seen:
            seen.add(key)
            unique.append(x)
    return unique


def accepted_exams(results: list[tuple[dict[str, Any], str]]) -> list[str]:
    counts: dict[str, int] = {}
    for result, _ in results:
        blob = text_blob(result)
        for exam in EXAMS:
            if re.search(rf"\b{re.escape(exam)}\b", blob, re.I):
                counts[exam] = counts.get(exam, 0) + 1
    # Require more than just the query concept to mention an exam; this data comes from retrieved content.
    return [x for x, _ in sorted(counts.items(), key=lambda kv: kv[1], reverse=True)]


def reservation_text(results: list[tuple[dict[str, Any], str]]) -> str:
    for result, _ in results:
        blob = text_blob(result)
        matches = re.findall(r"[^.\n]{0,100}(?:reserved|reservation|reserved category|EWS|SC/ST|OBC|PWD|PwD)[^.\n]{0,180}", blob, re.I)
        if matches:
            # Prefer specific marks statements.
            for m in matches:
                if re.search(r"\d+%|relax|minimum|marks", m, re.I):
                    return clean(m)[:450]
            return clean(matches[0])[:450]
    return ""


def specialization_text(results: list[tuple[dict[str, Any], str]], program: str) -> str:
    for result, _ in results:
        blob = text_blob(result)
        m = re.search(r"(?:speciali[sz]ations?|specialisations?)\D{0,120}([^.\n]{20,280})", blob, re.I)
        if m:
            return clean(m.group(0))[:400]
    return program


def curriculum_text(results: list[tuple[dict[str, Any], str]]) -> str:
    patterns = [
        r"(?:curriculum|syllabus|key skills covered|skills covered)\D{0,40}([^.\n]{40,320})",
        r"(?:data mining|predictive analytics|business intelligence|data visualization|decision analytics)[^.\n]{0,250}",
    ]
    for result, _ in results:
        blob = text_blob(result)
        for p in patterns:
            m = re.search(p, blob, re.I)
            if m:
                return clean(m.group(0))[:450]
    return ""


def location_hub_text(results: list[tuple[dict[str, Any], str]], location: str) -> str:
    for result, _ in results:
        blob = text_blob(result)
        for pat in [
            r"([^.\n]{0,120}(?:IT|technology|tech|business|financial|SaaS|startup)[^.\n]{0,120}hub[^.\n]{0,80})",
            r"([^.\n]{0,120}(?:hub for IT|technology hub|tech hub|business hub)[^.\n]{0,120})",
        ]:
            m = re.search(pat, blob, re.I)
            if m:
                return clean(m.group(1))[:350]
    return ""


def batch_size_text(results: list[tuple[dict[str, Any], str]]) -> str:
    for result, _ in results:
        blob = text_blob(result)
        m = re.search(r"(?:batch size|class size|students per batch|batch of)\D{0,60}(\d{2,5})", blob, re.I)
        if m:
            return clean(m.group(0))[:250]
    return ""


def recruiter_text(results: list[tuple[dict[str, Any], str]]) -> str:
    found = []
    for result, _ in results:
        blob = text_blob(result)
        low = blob.lower()
        if "recruiter" not in low and "companies" not in low:
            continue
        for company in COMPANIES:
            if re.search(rf"\b{re.escape(company)}\b", blob, re.I) and company not in found:
                found.append(company)
    return ", ".join(found[:15])


def make_criterion(status: str, confidence: str, value: Any, urls: list[str], note: str = "") -> dict[str, Any]:
    return {
        "status": status,
        "confidence": confidence,
        "value": value,
        "sources": urls[:5],
        "note": note,
    }


def build_candidate(college: dict[str, Any], student_profile: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    institution = clean(college.get("institution"))
    program = clean(college.get("program"))
    location = clean(college.get("location"))

    adm = relevant_results(college, "official_admission_research")
    quality = relevant_results(college, "official_quality_research")
    third = relevant_results(college, "third_party_fallback_research")
    all_results = adm + quality + third

    official_urls = source_urls(adm + quality)
    third_urls = source_urls(third)
    all_urls = source_urls(all_results)

    # Admission / cutoff / fees
    exams = accepted_exams(adm)
    cutoff = cutoff_history(third + adm)
    fee = None
    fee_source = ""

    # First pass: program-specific evidence.
    for result, src in adm + third:
        blob = text_blob(result)
        if not program_specific(blob, program):
            continue
        v = fee_value(blob, program)
        if v is not None:
            fee = v
            fee_source = clean(result.get("url"))
            if src == "official":
                break

    # Second pass: official/general fee evidence only if no program-specific value exists.
    if fee is None:
        for result, src in adm + third:
            v = fee_value(text_blob(result), program)
            if v is not None:
                fee = v
                fee_source = clean(result.get("url"))
                if src == "official":
                    break

    reservation = reservation_text(adm)
    eligibility = first_excerpt(adm, ["eligibility", "minimum 50%", "graduation with", "bachelor's degree"])
    selection = first_excerpt(adm, ["selection process", "personal interaction", "group discussion", "GD", "PI", "WAT", "written ability"])
    specializations = specialization_text(adm, program)

    # Quality / placements
    placements = placement_metrics(quality + third)
    recruiters = recruiter_text(quality)
    curriculum = curriculum_text(quality + adm)
    hub = location_hub_text(adm + quality, location)
    batch_size = batch_size_text(quality + adm)
    reputation = first_excerpt(quality, ["ranked", "ranking", "reputation", "legacy", "accredited", "top business school"])
    accreditation = first_excerpt(quality, ["NAAC", "NBA", "AACSB", "AMBA", "EQUIS", "AICTE", "UGC"])
    nirf = first_excerpt(quality, ["NIRF"])
    faculty = first_excerpt(quality, ["faculty", "professor", "professors"])
    internship = first_excerpt(quality, ["internship", "internships"])
    alumni = first_excerpt(quality, ["alumni", "alumnae"])
    infrastructure = first_excerpt(quality, ["infrastructure", "campus", "labs", "library", "facilities"])
    industry = first_excerpt(quality, ["industry exposure", "industry interaction", "industry tie", "live projects", "industrial visit"])
    reviews = None

    # Career fit: deterministic relevance, not a web fact.
    career_goal = norm(student_profile.get("career_goal"))
    career_keywords = [
        w for w in re.findall(r"[a-z]+", career_goal)
        if w in {"business", "analyst", "analytics", "consulting", "data", "strategy", "technology"}
    ]
    career_blob = norm(" ".join([program, clean(curriculum), clean(quality[0][0].get("content") if quality else "")]))
    career_matches = sum(1 for w in career_keywords if w in career_blob)
    career_score_text = (
        f"Strong alignment with stated career goal ({clean(student_profile.get('career_goal'))})."
        if career_matches >= 2 else
        f"Moderate alignment with stated career goal ({clean(student_profile.get('career_goal'))})."
        if career_matches == 1 else
        "Career fit could not be established from the retrieved program evidence."
    )

    # Criteria dictionary for the deterministic fit engine.
    criteria: dict[str, Any] = {}

    criteria["1"] = make_criterion(
        "VERIFIED" if reputation else "NOT_VERIFIED",
        "HIGH" if reputation and reputation[2] == "official" else "MEDIUM",
        reputation[0] if reputation else None,
        [reputation[1]] if reputation else [],
    )
    criteria["2"] = make_criterion(
        "VERIFIED" if accreditation else "NOT_VERIFIED",
        "HIGH" if accreditation and accreditation[2] == "official" else "MEDIUM",
        accreditation[0] if accreditation else None,
        [accreditation[1]] if accreditation else [],
    )
    criteria["3"] = make_criterion(
        "VERIFIED" if nirf else "NOT_VERIFIED",
        "HIGH" if nirf and nirf[2] == "official" else "MEDIUM",
        nirf[0] if nirf else None,
        [nirf[1]] if nirf else [],
    )
    criteria["4"] = make_criterion(
        "VERIFIED" if any(v is not None for v in [placements["average_salary_lakh"], placements["median_salary_lakh"], placements["highest_salary_lakh"], placements["placement_percentage"]]) else "NOT_VERIFIED",
        "HIGH" if placements["sources"] and any(host_matches(domain(placements["sources"][0]), clean(college.get("official_domain")) or KNOWN_OFFICIAL_DOMAINS.get(institution, "")) for _ in [0]) else "MEDIUM",
        placements,
        placements["sources"],
    )

    criteria["5"] = make_criterion(
        "VERIFIED" if fee is not None and placements["average_salary_lakh"] is not None else "PARTIAL" if fee is not None or placements["average_salary_lakh"] is not None else "NOT_VERIFIED",
        "HIGH" if fee is not None and fee_source in official_urls else "MEDIUM",
        {
            "program_fee_lakh": fee,
            "average_salary_lakh": placements["average_salary_lakh"],
            "median_salary_lakh": placements["median_salary_lakh"],
            "highest_salary_lakh": placements["highest_salary_lakh"],
            "placement_scope": placements["scope"],
        },
        [x for x in [fee_source] + placements["sources"] if x],
        "ROI is calculated only when fee and average salary are both available.",
    )
    criteria["6"] = make_criterion(
        "VERIFIED" if recruiters else "NOT_VERIFIED",
        "HIGH" if recruiters and official_urls else "MEDIUM",
        recruiters if recruiters else None,
        official_urls,
    )
    criteria["7"] = make_criterion("VERIFIED" if program else "NOT_VERIFIED", "HIGH", program or None, official_urls)
    criteria["8"] = make_criterion("VERIFIED" if curriculum else "NOT_VERIFIED", "HIGH" if curriculum else "LOW", curriculum[0] if curriculum else None, [curriculum[1]] if curriculum else [])
    criteria["9"] = make_criterion("VERIFIED" if faculty else "NOT_VERIFIED", "HIGH" if faculty and faculty[2] == "official" else "MEDIUM", faculty[0] if faculty else None, [faculty[1]] if faculty else [])
    criteria["10"] = make_criterion("VERIFIED" if internship else "NOT_VERIFIED", "HIGH" if internship and internship[2] == "official" else "MEDIUM", internship[0] if internship else None, [internship[1]] if internship else [])
    criteria["11"] = make_criterion("VERIFIED" if alumni else "NOT_VERIFIED", "HIGH" if alumni and alumni[2] == "official" else "MEDIUM", alumni[0] if alumni else None, [alumni[1]] if alumni else [])
    criteria["12"] = make_criterion("VERIFIED" if location else "NOT_VERIFIED", "HIGH", location or None, [])
    criteria["13"] = make_criterion("VERIFIED" if batch_size else "NOT_VERIFIED", "MEDIUM", batch_size or None, [])

    competitiveness = "UNKNOWN"
    student_exams = student_profile.get("entrance_exams") or []
    taken_scores = {
        norm(x.get("exam")): x.get("percentile")
        for x in student_exams
        if isinstance(x, dict) and x.get("percentile") is not None
    }
    for row in cutoff:
        if norm(row["exam"]) in taken_scores and taken_scores[norm(row["exam"])] is not None:
            pct = float(taken_scores[norm(row["exam"])])
            cut = float(row["percentile"])
            competitiveness = "STRONG" if pct >= cut + 3 else "TARGET" if pct >= cut - 1 else "REACH"
            break

    criteria["14"] = make_criterion(
        "VERIFIED" if exams or cutoff else "NOT_VERIFIED",
        "HIGH" if exams and official_urls else "MEDIUM",
        {
            "accepted_exams": exams,
            "cutoff_history": cutoff,
            "competitiveness": competitiveness,
            "eligibility": eligibility[0] if eligibility else None,
        },
        [x["url"] for x in cutoff if x.get("url")] + official_urls,
    )
    criteria["15"] = make_criterion("VERIFIED" if selection else "NOT_VERIFIED", "HIGH" if selection and selection[2] == "official" else "MEDIUM", selection[0] if selection else None, [selection[1]] if selection else [])
    criteria["16"] = make_criterion("VERIFIED" if infrastructure else "NOT_VERIFIED", "HIGH" if infrastructure and infrastructure[2] == "official" else "MEDIUM", infrastructure[0] if infrastructure else None, [infrastructure[1]] if infrastructure else [])
    criteria["17"] = make_criterion("VERIFIED" if industry else "NOT_VERIFIED", "HIGH" if industry and industry[2] == "official" else "MEDIUM", industry[0] if industry else None, [industry[1]] if industry else [])
    criteria["18"] = make_criterion("VERIFIED" if reviews else "NOT_VERIFIED", "MEDIUM", None, [])
    placement_transparency = None
    if placements["sources"] and any(v is not None for v in [placements["average_salary_lakh"], placements["median_salary_lakh"], placements["highest_salary_lakh"]]):
        placement_transparency = "Placement figures are reported with separate salary metrics where available."
    criteria["19"] = make_criterion("VERIFIED" if placement_transparency else "NOT_VERIFIED", "HIGH" if placements["scope"] == "program" else "MEDIUM", placement_transparency, placements["sources"])
    criteria["20"] = make_criterion("VERIFIED" if career_matches >= 2 else "PARTIAL" if career_matches == 1 else "NOT_VERIFIED", "HIGH" if career_matches else "LOW", career_score_text, all_urls[:3])

    user_fields = {
        "College Brand Value / Reputation": criteria["1"]["value"],
        "Entrance Exams Accepted": exams,
        "2025 Cutoff — Exam & Percentile": "; ".join(f"{x['exam']}: {x['percentile']:.0f}%" for x in cutoff if x["year"] == 2025),
        "2024 Cutoff — Exam & Percentile": "; ".join(f"{x['exam']}: {x['percentile']:.0f}%" for x in cutoff if x["year"] == 2024),
        "Total MBA Fees": fee,
        "Average Placement Package": placements["average_salary_lakh"],
        "Median Placement Package": placements["median_salary_lakh"],
        "Placement Percentage": placements["placement_percentage"],
        "Top Recruiting Companies": recruiters,
        "Specializations Offered": specializations,
        "Curriculum / Course Quality": curriculum[0] if curriculum else "",
        "Location / City": location,
        "Nearby IT / Business / Tech Hub": hub,
        "Eligibility & Admission Criteria": eligibility[0] if eligibility else "",
        "Reservation / Category Benefits": reservation,
        "ROI": None,
        "Career Fit": career_score_text,
        "Data Confidence": "High" if len(all_results) >= 4 else "Medium" if len(all_results) >= 2 else "Limited",
        "Source URLs": all_urls,
    }
    if fee is not None and placements["average_salary_lakh"] is not None and fee > 0:
        user_fields["ROI"] = round(placements["average_salary_lakh"] / fee, 2)

    candidate = {
        "candidate_index": college.get("candidate_index"),
        "institution": institution,
        "program": program,
        "location": location,
        "official_url": clean(college.get("official_url")),
        "official_domain": clean(college.get("official_domain")) or KNOWN_OFFICIAL_DOMAINS.get(institution, ""),
        "selection_score": college.get("selection_score"),
        "criteria": criteria,
        "evidence": all_results,
        "user_fields": user_fields,
    }

    return candidate, user_fields


def finalize_evidence(
    student_profile: dict[str, Any],
    colleges: list[dict[str, Any]],
) -> dict[str, Any]:

    prepared = []
    for college in colleges or []:
        candidate, _ = build_candidate(college, student_profile)
        prepared.append(candidate)

    result = run_fit_engine(
        student_profile=student_profile,
        verified_candidates=prepared,
    )

    # Attach the user-facing extracted fields to ranked records.
    by_index = {
        c.get("candidate_index"): c.get("user_fields", {})
        for c in prepared
    }

    for item in result.get("top_10", []):
        item["user_fields"] = by_index.get(item.get("candidate_index"), {})

    for item in result.get("all_ranked_candidates", []):
        item["user_fields"] = by_index.get(item.get("candidate_index"), {})

    result["status"] = "success"
    result["verification_status"] = "finalized"
    result["college_count"] = len(prepared)
    result["top_10_count"] = min(10, len(prepared))
    result["verified_candidates"] = prepared

    return result
