# from __future__ import annotations

# from pathlib import Path
# from typing import Any
# from app.services.verification_service import verify_colleges

# from fastapi import FastAPI, HTTPException
# from fastapi.staticfiles import StaticFiles
# from pydantic import BaseModel, Field

# from app.database import (
#     DATABASE_PATH,
#     database_info,
#     get_connection,
# )
# from app.services.candidate_discovery import discover_candidates
# from app.services.evidence_service import (
#     get_institution_evidence,
#     save_research,
# )
# from app.services.fit_engine import run_fit_engine
# from app.services.pdf_reader import read_pdf_from_url
# from app.services.report_generator import generate_report


# # ============================================================
# # APP
# # ============================================================

# app = FastAPI(
#     title="EduCompass API",
#     description="Supporting API services for the EduCompass Agentic AI system",
#     version="1.0.0",
# )


# # ============================================================
# # REQUEST MODELS
# # ============================================================

# class CandidateDiscoveryRequest(BaseModel):
#     student_profile: dict[str, Any] = Field(default_factory=dict)
#     research_plan: dict[str, Any] = Field(default_factory=dict)
#     candidate_results: list[dict[str, Any]] = Field(default_factory=list)


# class PDFReadRequest(BaseModel):
#     url: str


# class FitBatchRequest(BaseModel):
#     student_profile: dict[str, Any] = Field(default_factory=dict)
#     verified_candidates: list[dict[str, Any]] = Field(default_factory=list)


# class ReportRequest(BaseModel):
#     report_text: str
#     student_profile: dict[str, Any] = Field(default_factory=dict)
#     shortlist: list[dict[str, Any]] = Field(default_factory=list)


# # ============================================================
# # ROOT
# # ============================================================

# @app.get("/")
# def root():
#     return {
#         "project": "EduCompass",
#         "status": "running",
#         "database": "SQLite",
#     }


# # ============================================================
# # HEALTH
# # ============================================================

# @app.get("/health")
# def health_check():

#     try:
#         with get_connection() as connection:
#             connection.execute("SELECT 1;").fetchone()

#         info = database_info()

#         return {
#             "status": "healthy",
#             "database": "SQLite",
#             "database_path": str(DATABASE_PATH),
#             "tables": info,
#         }

#     except Exception as exc:
#         raise HTTPException(
#             status_code=500,
#             detail=f"Database health check failed: {exc}",
#         )


# # ============================================================
# # CANDIDATE DISCOVERY
# # ============================================================

# @app.post("/candidates/discover")
# def candidate_discovery(request: CandidateDiscoveryRequest):

#     try:

#         result = discover_candidates(
#             student_profile=request.student_profile,
#             research_plan=request.research_plan,
#             candidate_results=request.candidate_results,
#             # web_results=request.candidate_results,
#         )

#         return result

#     except Exception as exc:

#         raise HTTPException(
#             status_code=500,
#             detail=f"Candidate discovery failed: {exc}",
#         )


# # ============================================================
# # PDF READER
# # ============================================================

# @app.post("/tools/read-pdf")
# def read_pdf(request: PDFReadRequest):

#     try:

#         return read_pdf_from_url(request.url)

#     except Exception as exc:

#         raise HTTPException(
#             status_code=500,
#             detail=f"PDF reading failed: {exc}",
#         )


# # ============================================================
# # EVIDENCE SAVE
# # ============================================================

# @app.post("/evidence/bulk")
# def save_evidence(payload: dict[str, Any]):

#     try:

#         result = save_research(payload)

#         return {
#             "research": payload,
#             "save_result": result,
#         }

#     except Exception as exc:

#         raise HTTPException(
#             status_code=500,
#             detail=f"Evidence save failed: {exc}",
#         )


# # ============================================================
# # EVIDENCE RETRIEVAL
# # ============================================================

# @app.get("/evidence/{institution_id}")
# def load_evidence(
#     institution_id: int,
#     program_id: int | None = None,
# ):

#     try:

#         return get_institution_evidence(
#             institution_id=institution_id,
#             program_id=program_id,
#         )

#     except Exception as exc:

#         raise HTTPException(
#             status_code=500,
#             detail=f"Evidence retrieval failed: {exc}",
#         )


# # ============================================================
# # FIT ENGINE
# # ============================================================

# @app.post("/fit/batch")
# def fit_batch(request: FitBatchRequest):

#     try:

#         result = run_fit_engine(
#             student_profile=request.student_profile,
#             verified_candidates=request.verified_candidates,
#         )

#         return result

#     except Exception as exc:

#         raise HTTPException(
#             status_code=500,
#             detail=f"Fit engine failed: {exc}",
#         )


# # ============================================================
# # REPORT GENERATION
# # IMPORTANT:
# # This route MUST appear BEFORE the /reports static mount.
# # ============================================================

# @app.post("/reports/generate")
# def generate_report_endpoint(request: ReportRequest):

#     try:

#         result = generate_report(
#             report_text=request.report_text,
#             student_profile=request.student_profile,
#             shortlist=request.shortlist,
#         )

#         return result

#     except Exception as exc:

#         raise HTTPException(
#             status_code=500,
#             detail=f"Report generation failed: {exc}",
#         )


# # ============================================================
# # STATIC REPORT FILES
# #
# # IMPORTANT:
# # Keep this AFTER /reports/generate.
# #
# # Otherwise StaticFiles catches POST /reports/generate
# # and returns HTTP 405 Method Not Allowed.
# # ============================================================

# REPORT_DIR = (
#     Path(__file__).resolve().parents[1]
#     / "reports"
# )

# REPORT_DIR.mkdir(
#     parents=True,
#     exist_ok=True,
# )

# app.mount(
#     "/reports",
#     StaticFiles(directory=str(REPORT_DIR)),
#     name="reports",
# )


# # ============================================================
# # STARTUP
# # ============================================================

# @app.on_event("startup")
# def startup():

#     # Database initialization is already performed by
#     # app.database when imported.
#     print("EduCompass API started.")
#     print(f"SQLite database: {DATABASE_PATH}")
#     print(f"Reports directory: {REPORT_DIR}")

# # ============================================================
# # VERIFY & NORMALIZE RESEARCH EVIDENCE
# # ============================================================

# @app.post("/evidence/verify")
# def verify_evidence(payload: dict[str, Any]):

#     try:

#         return verify_colleges(
#             student_profile=
#                 payload.get(
#                     "student_profile",
#                     {},
#                 ),

#             colleges=
#                 payload.get(
#                     "colleges",
#                     [],
#                 ),
#         )

#     except Exception as exc:

#         raise HTTPException(
#             status_code=500,
#             detail=(
#                 "Evidence verification failed: "
#                 f"{exc}"
#             ),
#         )


from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from app.services.fact_extractor import extract_facts
from app.database import (
    DATABASE_PATH,
    database_info,
    get_connection,
)
from app.services.candidate_discovery import discover_candidates
from app.services.evidence_service import (
    get_institution_evidence,
    save_research,
)
from app.services.fit_engine import run_fit_engine
from app.services.verification_service import finalize_evidence
from app.services.pdf_reader import read_pdf_from_url
from app.services.report_generator import generate_report


# ============================================================
# APP
# ============================================================

app = FastAPI(
    title="EduCompass API",
    description="Supporting API services for the EduCompass Agentic AI system",
    version="1.0.0",
)


# ============================================================
# REQUEST MODELS
# ============================================================

class CandidateDiscoveryRequest(BaseModel):
    student_profile: dict[str, Any] = Field(default_factory=dict)
    research_plan: dict[str, Any] = Field(default_factory=dict)
    candidate_results: list[dict[str, Any]] = Field(default_factory=list)


class PDFReadRequest(BaseModel):
    url: str


class FitBatchRequest(BaseModel):
    student_profile: dict[str, Any] = Field(default_factory=dict)
    verified_candidates: list[dict[str, Any]] = Field(default_factory=list)


class FinalizeEvidenceRequest(BaseModel):
    student_profile: dict[str, Any] = Field(default_factory=dict)
    colleges: list[dict[str, Any]] = Field(default_factory=list)


class ReportRequest(BaseModel):
    report_text: str
    student_profile: dict[str, Any] = Field(default_factory=dict)
    shortlist: list[dict[str, Any]] = Field(default_factory=list)


# ============================================================
# ROOT
# ============================================================

@app.get("/")
def root():
    return {
        "project": "EduCompass",
        "status": "running",
        "database": "SQLite",
    }


# ============================================================
# HEALTH
# ============================================================

@app.get("/health")
def health_check():

    try:
        with get_connection() as connection:
            connection.execute("SELECT 1;").fetchone()

        info = database_info()

        return {
            "status": "healthy",
            "database": "SQLite",
            "database_path": str(DATABASE_PATH),
            "tables": info,
        }

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Database health check failed: {exc}",
        )


# ============================================================
# CANDIDATE DISCOVERY
# ============================================================

@app.post("/candidates/discover")
def candidate_discovery(request: CandidateDiscoveryRequest):

    try:

        result = discover_candidates(
            student_profile=request.student_profile,
            research_plan=request.research_plan,
            candidate_results=request.candidate_results,
        )

        return result

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=f"Candidate discovery failed: {exc}",
        )


# ============================================================
# PDF READER
# ============================================================

@app.post("/tools/read-pdf")
def read_pdf(request: PDFReadRequest):

    try:

        return read_pdf_from_url(request.url)

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=f"PDF reading failed: {exc}",
        )


# ============================================================
# EVIDENCE SAVE
# ============================================================

@app.post("/evidence/bulk")
def save_evidence(payload: dict[str, Any]):

    try:

        result = save_research(payload)

        return {
            "research": payload,
            "save_result": result,
        }

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=f"Evidence save failed: {exc}",
        )


# ============================================================
# EVIDENCE RETRIEVAL
# ============================================================

@app.get("/evidence/{institution_id}")
def load_evidence(
    institution_id: int,
    program_id: int | None = None,
):

    try:

        return get_institution_evidence(
            institution_id=institution_id,
            program_id=program_id,
        )

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=f"Evidence retrieval failed: {exc}",
        )


# ============================================================
# FINAL EVIDENCE EXTRACTION + RANKING
# ============================================================

@app.post("/evidence/verify")
def verify_and_rank(request: FinalizeEvidenceRequest):

    try:

        result = finalize_evidence(
            student_profile=request.student_profile,
            colleges=request.colleges,
        )

        return result

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=f"Final evidence verification failed: {exc}",
        )


# ============================================================
# FIT ENGINE (legacy/direct endpoint)
# ============================================================

@app.post("/fit/batch")
def fit_batch(request: FitBatchRequest):

    try:

        result = run_fit_engine(
            student_profile=request.student_profile,
            verified_candidates=request.verified_candidates,
        )

        return result

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=f"Fit engine failed: {exc}",
        )


# ============================================================
# REPORT GENERATION
# IMPORTANT:
# This route MUST appear BEFORE the /reports static mount.
# ============================================================

@app.post("/reports/generate")
def generate_report_endpoint(request: ReportRequest):

    try:

        result = generate_report(
            report_text=request.report_text,
            student_profile=request.student_profile,
            shortlist=request.shortlist,
        )

        return result

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=f"Report generation failed: {exc}",
        )


# ============================================================
# STATIC REPORT FILES
#
# IMPORTANT:
# Keep this AFTER /reports/generate.
#
# Otherwise StaticFiles catches POST /reports/generate
# and returns HTTP 405 Method Not Allowed.
# ============================================================

REPORT_DIR = (
    Path(__file__).resolve().parents[1]
    / "reports"
)

REPORT_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

app.mount(
    "/reports",
    StaticFiles(directory=str(REPORT_DIR)),
    name="reports",
)


# ============================================================
# STARTUP
# ============================================================

@app.on_event("startup")
def startup():

    # Database initialization is already performed by
    # app.database when imported.
    print("EduCompass API started.")
    print(f"SQLite database: {DATABASE_PATH}")
    print(f"Reports directory: {REPORT_DIR}")

class ExtractFactsRequest(BaseModel):
    student_profile: dict[str, Any] = Field(default_factory=dict)
    colleges: list[dict[str, Any]] = Field(default_factory=list)

@app.post("/evidence/extract")
def extract_evidence_facts(request: ExtractFactsRequest):

    try:

        result = extract_facts({
            "student_profile": request.student_profile,
            "colleges": request.colleges,
        })

        return result

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=f"Evidence extraction failed: {exc}",
        )