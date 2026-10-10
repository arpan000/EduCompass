from pathlib import Path
from uuid import uuid4

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
)


REPORT_DIR = (
    Path(__file__).resolve().parents[2]
    / "reports"
)

REPORT_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


def generate_report(
    report_text: str,
    student_profile: dict,
    shortlist: list[dict],
):

    filename = (
        f"educompass_{uuid4().hex[:10]}.pdf"
    )

    path = REPORT_DIR / filename

    styles = getSampleStyleSheet()

    document = SimpleDocTemplate(
        str(path),
        pagesize=A4,
        leftMargin=40,
        rightMargin=40,
        topMargin=40,
        bottomMargin=40,
    )

    story = []

    story.append(
        Paragraph(
            "EDUCOMPASS",
            styles["Title"],
        )
    )

    story.append(
        Paragraph(
            "Personalized College Research Report",
            styles["Heading2"],
        )
    )

    story.append(
        Spacer(1, 15)
    )

    story.append(
        Paragraph(
            "Final Decision Report",
            styles["Heading2"],
        )
    )

    for line in report_text.splitlines():

        line = line.strip()

        if not line:
            story.append(
                Spacer(1, 5)
            )
            continue

        story.append(
            Paragraph(
                line.replace("&", "&amp;"),
                styles["BodyText"],
            )
        )

        story.append(
            Spacer(1, 4)
        )

    document.build(story)

    return {
        "status": "success",
        "filename": filename,
        "url": f"/reports/{filename}",
        "path": str(path),
    }