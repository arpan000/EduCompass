from pathlib import Path
import sqlite3


# ============================================================
# EduCompass SQLite Database
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[1]

DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

DATABASE_PATH = DATA_DIR / "educompass.db"


# ============================================================
# Database Connection
# ============================================================

def get_connection():
    """
    Create and return a SQLite connection for EduCompass.
    """

    connection = sqlite3.connect(
        str(DATABASE_PATH),
        timeout=30,
    )

    connection.row_factory = sqlite3.Row

    # Enable foreign-key constraints.
    connection.execute("PRAGMA foreign_keys = ON;")

    return connection


# ============================================================
# Database Initialization
# ============================================================

def initialize_database():
    """
    Create all EduCompass SQLite tables and indexes.

    Safe to execute repeatedly.
    Existing data is preserved.
    """

    with get_connection() as connection:

        cursor = connection.cursor()

        # ====================================================
        # Institutions
        # ====================================================

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS institutions (
                institution_id INTEGER PRIMARY KEY AUTOINCREMENT,

                name TEXT NOT NULL,

                city TEXT,
                state TEXT,

                institution_type TEXT,

                official_domain TEXT,
                official_url TEXT,

                description TEXT,

                active INTEGER NOT NULL DEFAULT 1,

                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            """
        )

        # ====================================================
        # Programs
        # ====================================================

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS programs (
                program_id INTEGER PRIMARY KEY AUTOINCREMENT,

                institution_id INTEGER NOT NULL,

                degree_type TEXT NOT NULL,
                program_name TEXT NOT NULL,

                specialization TEXT,

                duration_years REAL,

                mode TEXT,

                official_url TEXT,

                description TEXT,

                active INTEGER NOT NULL DEFAULT 1,

                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,

                FOREIGN KEY (institution_id)
                    REFERENCES institutions(institution_id)
                    ON DELETE CASCADE
            );
            """
        )

        # ====================================================
        # Sources
        # ====================================================

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS sources (
                source_id INTEGER PRIMARY KEY AUTOINCREMENT,

                url TEXT NOT NULL UNIQUE,

                title TEXT,

                source_type TEXT,

                publisher TEXT,

                retrieved_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,

                accessible INTEGER NOT NULL DEFAULT 1,

                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            """
        )

        # ====================================================
        # Evidence
        # ====================================================

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS evidence (
                evidence_id INTEGER PRIMARY KEY AUTOINCREMENT,

                institution_id INTEGER NOT NULL,

                program_id INTEGER,

                fact_key TEXT NOT NULL,

                value_json TEXT,

                evidence_text TEXT,

                source_id INTEGER,

                status TEXT NOT NULL DEFAULT 'unverified',

                confidence REAL,

                scope TEXT NOT NULL DEFAULT 'program_specific',

                verification_notes TEXT,

                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,

                FOREIGN KEY (institution_id)
                    REFERENCES institutions(institution_id)
                    ON DELETE CASCADE,

                FOREIGN KEY (program_id)
                    REFERENCES programs(program_id)
                    ON DELETE CASCADE,

                FOREIGN KEY (source_id)
                    REFERENCES sources(source_id)
                    ON DELETE SET NULL
            );
            """
        )

        # ====================================================
        # Community Signals
        # ====================================================

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS community_signals (
                signal_id INTEGER PRIMARY KEY AUTOINCREMENT,

                institution_id INTEGER NOT NULL,

                program_id INTEGER,

                platform TEXT,

                signal_type TEXT,

                signal_text TEXT,

                sentiment TEXT,

                confidence REAL,

                source_url TEXT,

                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,

                FOREIGN KEY (institution_id)
                    REFERENCES institutions(institution_id)
                    ON DELETE CASCADE,

                FOREIGN KEY (program_id)
                    REFERENCES programs(program_id)
                    ON DELETE CASCADE
            );
            """
        )

        # ====================================================
        # Indexes
        # ====================================================

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_programs_institution
            ON programs(institution_id);
            """
        )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_programs_degree
            ON programs(degree_type);
            """
        )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_programs_specialization
            ON programs(specialization);
            """
        )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_evidence_institution
            ON evidence(institution_id);
            """
        )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_evidence_program
            ON evidence(program_id);
            """
        )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_evidence_source
            ON evidence(source_id);
            """
        )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_sources_url
            ON sources(url);
            """
        )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_community_institution
            ON community_signals(institution_id);
            """
        )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_community_program
            ON community_signals(program_id);
            """
        )

        connection.commit()


# ============================================================
# Seed Database
# ============================================================

def seed_database():
    """
    Add initial EduCompass registry data.

    The seed operation is idempotent.
    It will not duplicate existing institutions or programs.
    """

    with get_connection() as connection:

        cursor = connection.cursor()

        # ----------------------------------------------------
        # Check whether the institution already exists
        # ----------------------------------------------------

        institution = cursor.execute(
            """
            SELECT institution_id
            FROM institutions
            WHERE name = ?;
            """,
            (
                "Symbiosis International University",
            ),
        ).fetchone()

        # ----------------------------------------------------
        # Create institution if necessary
        # ----------------------------------------------------

        if institution is None:

            cursor.execute(
                """
                INSERT INTO institutions (
                    name,
                    city,
                    state,
                    institution_type,
                    official_domain,
                    official_url,
                    description
                )
                VALUES (?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    "Symbiosis International University",
                    "Pune",
                    "Maharashtra",
                    "Private University",
                    "https://www.siu.edu.in",
                    "https://www.siu.edu.in",
                    "Deemed university based in Pune, Maharashtra.",
                ),
            )

            institution_id = cursor.execute(
                """
                SELECT institution_id
                FROM institutions
                WHERE name = ?;
                """,
                (
                    "Symbiosis International University",
                ),
            ).fetchone()["institution_id"]

        else:

            institution_id = institution["institution_id"]

        # ----------------------------------------------------
        # Check whether the program already exists
        # ----------------------------------------------------

        program = cursor.execute(
            """
            SELECT program_id
            FROM programs
            WHERE institution_id = ?
              AND program_name = ?;
            """,
            (
                institution_id,
                "MBA - Data Science and Data Analytics",
            ),
        ).fetchone()

        # ----------------------------------------------------
        # Create program if necessary
        # ----------------------------------------------------

        if program is None:

            cursor.execute(
                """
                INSERT INTO programs (
                    institution_id,
                    degree_type,
                    program_name,
                    specialization,
                    duration_years,
                    mode,
                    official_url,
                    description
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    institution_id,
                    "MBA",
                    "MBA - Data Science and Data Analytics",
                    "Data Science and Data Analytics",
                    2.0,
                    "Full-time",
                    "https://www.siu.edu.in",
                    "Postgraduate management program with a focus on data science and analytics.",
                ),
            )

        connection.commit()


# ============================================================
# Database Reset
# ============================================================

def reset_database():
    """
    Completely delete and recreate the EduCompass database.

    WARNING:
    This deletes all stored EduCompass research data.
    """

    if DATABASE_PATH.exists():
        DATABASE_PATH.unlink()

    initialize_database()
    seed_database()


# ============================================================
# Database Information
# ============================================================

def database_info():
    """
    Return database path, tables, and record counts.
    """

    with get_connection() as connection:

        tables = connection.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
              AND name NOT LIKE 'sqlite_%'
            ORDER BY name;
            """
        ).fetchall()

        result = {
            "database": str(DATABASE_PATH),
            "tables": [],
        }

        for row in tables:

            table_name = row["name"]

            result["tables"].append(table_name)

            count = connection.execute(
                f'SELECT COUNT(*) FROM "{table_name}";'
            ).fetchone()[0]

            result[f"{table_name}_count"] = count

        return result


# ============================================================
# Automatic Initialization
# ============================================================

initialize_database()
seed_database()


# ============================================================
# Command-Line Test
# ============================================================

if __name__ == "__main__":

    print()
    print("=" * 60)
    print("EduCompass SQLite Database")
    print("=" * 60)
    print()

    print(f"Database: {DATABASE_PATH}")
    print()

    info = database_info()

    print("Tables:")

    for table in info["tables"]:

        print(
            f"  {table}: "
            f"{info.get(table + '_count', 0)} records"
        )

    print()
    print("Database initialization complete.")
    print("=" * 60)
