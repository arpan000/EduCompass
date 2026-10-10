from __future__ import annotations

import json
from typing import Any

from app.database import get_connection


# ============================================================
# CONSTANTS
# ============================================================

ALLOWED_STATUS = {
    "verified",
    "secondary",
    "conflict",
    "unverified",
    "not_found",
    "outdated",
    "partial",
}

ALLOWED_SCOPE = {
    "program_specific",
    "institution_wide",
    "general",
    "community_signal",
}


# ============================================================
# HELPERS
# ============================================================

def clamp_confidence(value: Any) -> float:
    try:
        value = float(value)
    except (TypeError, ValueError):
        return 0.0

    return max(0.0, min(1.0, value))


def json_string(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
    )


def normalize_status(value: Any) -> str:
    status = str(value or "unverified").strip().lower()

    if status not in ALLOWED_STATUS:
        return "unverified"

    return status


def normalize_scope(value: Any) -> str:
    scope = str(value or "program_specific").strip().lower()

    if scope not in ALLOWED_SCOPE:
        return "program_specific"

    return scope


# ============================================================
# SAVE RESEARCH
# ============================================================

def save_research(payload: dict[str, Any]) -> dict[str, Any]:
    """
    Save research evidence into the EduCompass SQLite database.

    Supports both payload styles:

    1. n8n style:
       {
           "institution": {
               "institution_id": 1
           },
           "program": {
               "program_id": 1
           },
           "facts": {...}
       }

    2. Direct API style:
       {
           "institution_id": 1,
           "program_id": 1,
           "facts": {...}
       }
    """

    if not isinstance(payload, dict):
        return {
            "status": "error",
            "error": "Request payload must be a JSON object.",
        }

    # --------------------------------------------------------
    # Resolve institution ID
    # --------------------------------------------------------

    institution = payload.get("institution")

    if not isinstance(institution, dict):
        institution = {}

    institution_id = (
        payload.get("institution_id")
        or institution.get("institution_id")
    )

    # --------------------------------------------------------
    # Resolve program ID
    # --------------------------------------------------------

    program = payload.get("program")

    if not isinstance(program, dict):
        program = {}

    program_id = (
        payload.get("program_id")
        or program.get("program_id")
    )

    if institution_id is None:
        return {
            "status": "error",
            "error": "institution_id is required",
        }

    try:
        institution_id = int(institution_id)
    except (TypeError, ValueError):
        return {
            "status": "error",
            "error": "institution_id must be an integer",
        }

    if program_id is not None:
        try:
            program_id = int(program_id)
        except (TypeError, ValueError):
            return {
                "status": "error",
                "error": "program_id must be an integer",
            }

    # --------------------------------------------------------
    # Resolve payload sections
    # --------------------------------------------------------

    facts = payload.get("facts") or {}
    sources = payload.get("sources") or []
    community_signals = payload.get("community_signals") or []

    if not isinstance(facts, dict):
        return {
            "status": "error",
            "error": "facts must be a JSON object",
        }

    if not isinstance(sources, list):
        return {
            "status": "error",
            "error": "sources must be a JSON array",
        }

    if not isinstance(community_signals, list):
        return {
            "status": "error",
            "error": "community_signals must be a JSON array",
        }

    connection = get_connection()

    sources_inserted = 0
    sources_reused = 0
    evidence_inserted = 0
    community_signals_inserted = 0
    facts_skipped = 0
    community_signals_skipped = 0

    try:
        # ====================================================
        # Validate institution
        # ====================================================

        institution_row = connection.execute(
            """
            SELECT institution_id
            FROM institutions
            WHERE institution_id = ?
            LIMIT 1;
            """,
            (institution_id,),
        ).fetchone()

        if institution_row is None:
            connection.rollback()

            return {
                "status": "error",
                "error": f"Institution {institution_id} does not exist.",
            }

        # ====================================================
        # Validate program if supplied
        # ====================================================

        if program_id is not None:

            program_row = connection.execute(
                """
                SELECT program_id
                FROM programs
                WHERE program_id = ?
                  AND institution_id = ?
                LIMIT 1;
                """,
                (
                    program_id,
                    institution_id,
                ),
            ).fetchone()

            if program_row is None:
                connection.rollback()

                return {
                    "status": "error",
                    "error": (
                        f"Program {program_id} does not belong "
                        f"to institution {institution_id}."
                    ),
                }

        # ====================================================
        # Save / reuse sources
        # ====================================================

        source_map: dict[str, int] = {}

        for source in sources:

            if not isinstance(source, dict):
                continue

            url = source.get("url")

            if not url:
                continue

            url = str(url).strip()

            if not url:
                continue

            existing = connection.execute(
                """
                SELECT source_id
                FROM sources
                WHERE url = ?
                LIMIT 1;
                """,
                (url,),
            ).fetchone()

            if existing:

                source_id = int(existing["source_id"])
                sources_reused += 1

            else:

                cursor = connection.execute(
                    """
                    INSERT INTO sources (
                        url,
                        title,
                        source_type,
                        publisher,
                        retrieved_at,
                        accessible
                    )
                    VALUES (
                        ?,
                        ?,
                        ?,
                        ?,
                        CURRENT_TIMESTAMP,
                        1
                    );
                    """,
                    (
                        url,
                        source.get("title"),
                        source.get("source_type"),
                        source.get("publisher"),
                    ),
                )

                source_id = int(cursor.lastrowid)
                sources_inserted += 1

            source_map[url] = source_id

        # ====================================================
        # Save evidence
        # ====================================================

        for fact_key, fact in facts.items():

            # ------------------------------------------------
            # Normalize fact
            # ------------------------------------------------

            if isinstance(fact, dict):
                fact_data = fact
            else:
                fact_data = {
                    "value": fact
                }

            # ------------------------------------------------
            # Ignore completely empty facts
            # ------------------------------------------------

            if not fact_data:
                facts_skipped += 1
                continue

            # ------------------------------------------------
            # Fact key
            # ------------------------------------------------

            fact_key = str(fact_key).strip()

            if not fact_key:
                facts_skipped += 1
                continue

            # ------------------------------------------------
            # Extract fields
            # ------------------------------------------------

            value = fact_data.get("value")

            evidence_text = fact_data.get("evidence_text")

            status = normalize_status(
                fact_data.get("status")
            )

            scope = normalize_scope(
                fact_data.get("scope")
            )

            confidence = clamp_confidence(
                fact_data.get("confidence")
            )

            verification_notes = fact_data.get(
                "verification_notes"
            )

            source_url = fact_data.get("source_url")

            source_id = None

            # ------------------------------------------------
            # Resolve source
            # ------------------------------------------------

            if source_url:

                source_url = str(source_url).strip()

                source_id = source_map.get(source_url)

                if source_id is None:

                    existing = connection.execute(
                        """
                        SELECT source_id
                        FROM sources
                        WHERE url = ?
                        LIMIT 1;
                        """,
                        (source_url,),
                    ).fetchone()

                    if existing:
                        source_id = int(
                            existing["source_id"]
                        )

            # ------------------------------------------------
            # Insert evidence
            # ------------------------------------------------

            connection.execute(
                """
                INSERT INTO evidence (
                    institution_id,
                    program_id,
                    fact_key,
                    value_json,
                    evidence_text,
                    source_id,
                    status,
                    confidence,
                    scope,
                    verification_notes
                )
                VALUES (
                    ?,
                    ?,
                    ?,
                    ?,
                    ?,
                    ?,
                    ?,
                    ?,
                    ?,
                    ?
                );
                """,
                (
                    institution_id,
                    program_id,
                    fact_key,
                    json_string(value),
                    evidence_text,
                    source_id,
                    status,
                    confidence,
                    scope,
                    verification_notes,
                ),
            )

            evidence_inserted += 1

        # ====================================================
        # Save community signals
        # ====================================================

        for signal in community_signals:

            if not isinstance(signal, dict):
                community_signals_skipped += 1
                continue

            # ------------------------------------------------
            # Accept both signal_text and summary
            # ------------------------------------------------

            signal_text = (
                signal.get("signal_text")
                or signal.get("summary")
            )

            if not signal_text:
                community_signals_skipped += 1
                continue

            connection.execute(
                """
                INSERT INTO community_signals (
                    institution_id,
                    program_id,
                    platform,
                    signal_type,
                    signal_text,
                    sentiment,
                    confidence,
                    source_url
                )
                VALUES (
                    ?,
                    ?,
                    ?,
                    ?,
                    ?,
                    ?,
                    ?,
                    ?
                );
                """,
                (
                    institution_id,
                    program_id,
                    signal.get("platform"),
                    signal.get("signal_type"),
                    signal_text,
                    signal.get("sentiment"),
                    clamp_confidence(
                        signal.get("confidence")
                    ),
                    signal.get("source_url"),
                ),
            )

            community_signals_inserted += 1

        # ====================================================
        # Commit
        # ====================================================

        connection.commit()

        return {
            "status": "success",
            "institution_id": institution_id,
            "program_id": program_id,
            "sources_inserted": sources_inserted,
            "sources_reused": sources_reused,
            "evidence_inserted": evidence_inserted,
            "community_signals_inserted": community_signals_inserted,
            "facts_skipped": facts_skipped,
            "community_signals_skipped": community_signals_skipped,
        }

    except Exception as exc:

        connection.rollback()

        return {
            "status": "error",
            "institution_id": institution_id,
            "program_id": program_id,
            "error": str(exc),
        }

    finally:

        connection.close()


# ============================================================
# GET EVIDENCE
# ============================================================

def get_institution_evidence(
    institution_id: int,
    program_id: int | None = None,
) -> dict[str, Any]:

    connection = get_connection()

    try:

        # ====================================================
        # Institution
        # ====================================================

        institution_row = connection.execute(
            """
            SELECT
                institution_id,
                name,
                city,
                state,
                institution_type,
                official_domain,
                official_url
            FROM institutions
            WHERE institution_id = ?
            LIMIT 1;
            """,
            (institution_id,),
        ).fetchone()

        if institution_row is None:

            return {
                "status": "error",
                "error": (
                    f"Institution {institution_id} "
                    "does not exist."
                ),
            }

        institution = dict(institution_row)

        # ====================================================
        # Program
        # ====================================================

        program = None

        if program_id is not None:

            program_row = connection.execute(
                """
                SELECT
                    program_id,
                    institution_id,
                    degree_type,
                    program_name,
                    specialization,
                    duration_years,
                    mode,
                    official_url
                FROM programs
                WHERE program_id = ?
                  AND institution_id = ?
                LIMIT 1;
                """,
                (
                    program_id,
                    institution_id,
                ),
            ).fetchone()

            if program_row is not None:
                program = dict(program_row)

        # ====================================================
        # Evidence
        # ====================================================

        if program_id is None:

            evidence_rows = connection.execute(
                """
                SELECT
                    e.evidence_id,
                    e.institution_id,
                    e.program_id,
                    e.fact_key,
                    e.value_json,
                    e.evidence_text,
                    e.status,
                    e.confidence,
                    e.scope,
                    e.verification_notes,
                    e.created_at,
                    e.updated_at,

                    s.url AS source_url,
                    s.title AS source_title,
                    s.source_type,
                    s.publisher

                FROM evidence e

                LEFT JOIN sources s
                    ON s.source_id = e.source_id

                WHERE e.institution_id = ?

                ORDER BY
                    e.evidence_id ASC;
                """,
                (institution_id,),
            ).fetchall()

        else:

            evidence_rows = connection.execute(
                """
                SELECT
                    e.evidence_id,
                    e.institution_id,
                    e.program_id,
                    e.fact_key,
                    e.value_json,
                    e.evidence_text,
                    e.status,
                    e.confidence,
                    e.scope,
                    e.verification_notes,
                    e.created_at,
                    e.updated_at,

                    s.url AS source_url,
                    s.title AS source_title,
                    s.source_type,
                    s.publisher

                FROM evidence e

                LEFT JOIN sources s
                    ON s.source_id = e.source_id

                WHERE e.institution_id = ?
                  AND e.program_id = ?

                ORDER BY
                    e.evidence_id ASC;
                """,
                (
                    institution_id,
                    program_id,
                ),
            ).fetchall()

        evidence = []

        for row in evidence_rows:

            record = dict(row)

            raw_value = record.get("value_json")

            try:
                record["value"] = json.loads(
                    raw_value
                ) if raw_value is not None else None

            except (TypeError, json.JSONDecodeError):
                record["value"] = raw_value

            record.pop("value_json", None)

            evidence.append(record)

        # ====================================================
        # Community signals
        # ====================================================

        if program_id is None:

            signal_rows = connection.execute(
                """
                SELECT
                    signal_id,
                    institution_id,
                    program_id,
                    platform,
                    signal_type,
                    signal_text,
                    sentiment,
                    confidence,
                    source_url,
                    created_at
                FROM community_signals
                WHERE institution_id = ?
                ORDER BY signal_id ASC;
                """,
                (institution_id,),
            ).fetchall()

        else:

            signal_rows = connection.execute(
                """
                SELECT
                    signal_id,
                    institution_id,
                    program_id,
                    platform,
                    signal_type,
                    signal_text,
                    sentiment,
                    confidence,
                    source_url,
                    created_at
                FROM community_signals
                WHERE institution_id = ?
                  AND program_id = ?
                ORDER BY signal_id ASC;
                """,
                (
                    institution_id,
                    program_id,
                ),
            ).fetchall()

        community_signals = [
            dict(row)
            for row in signal_rows
        ]

        # ====================================================
        # Final response
        # ====================================================

        return {
            "status": "success",
            "institution": institution,
            "program": program,
            "evidence": evidence,
            "community_signals": community_signals,
            "evidence_count": len(evidence),
            "community_signal_count": len(
                community_signals
            ),
        }

    finally:

        connection.close()
