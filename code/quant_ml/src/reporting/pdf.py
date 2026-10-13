import re
from datetime import datetime
from io import BytesIO
from typing import Any, Callable, Dict, List, Optional
from xml.sax.saxutils import escape

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    Image,
    ListFlowable,
    ListItem,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

BOLD = re.compile(r"\*\*(.+?)\*\*")
ITALIC = re.compile(r"(?<!\*)\*(?!\s)(.+?)(?<!\s)\*(?!\*)")
HEADING = re.compile(r"^(#{1,3})\s+(.*)$")
BULLET = re.compile(r"^\s*[-*]\s+(.*)$")
MAX_TABLE_ROWS = 2000
MAX_CELL_CHARS = 200


def inline(text: str) -> str:
    safe = escape(text)
    safe = BOLD.sub(r"<b>\1</b>", safe)
    return ITALIC.sub(r"<i>\1</i>", safe)


def text_flowables(content: str, styles: Dict[str, ParagraphStyle]) -> List[Any]:
    flowables: List[Any] = []
    bullets: List[str] = []
    paragraph: List[str] = []

    def flush_paragraph() -> None:
        if paragraph:
            flowables.append(Paragraph(inline(" ".join(paragraph)), styles["body"]))
            paragraph.clear()

    def flush_bullets() -> None:
        if bullets:
            items = [
                ListItem(Paragraph(inline(item), styles["body"])) for item in bullets
            ]
            flowables.append(ListFlowable(items, bulletType="bullet", start="\u2022"))
            bullets.clear()

    for raw in content.splitlines():
        line = raw.rstrip()
        heading = HEADING.match(line)
        bullet = BULLET.match(line)
        if not line.strip():
            flush_paragraph()
            flush_bullets()
        elif heading:
            flush_paragraph()
            flush_bullets()
            level = min(len(heading.group(1)) + 1, 3)
            flowables.append(Paragraph(inline(heading.group(2)), styles[f"h{level}"]))
        elif bullet:
            flush_paragraph()
            bullets.append(bullet.group(1))
        else:
            flush_bullets()
            paragraph.append(line.strip())
    flush_paragraph()
    flush_bullets()
    return flowables


def table_flowable(
    frame: pd.DataFrame,
    show_index: bool,
    width: float,
    styles: Dict[str, ParagraphStyle],
) -> Any:
    frame = frame.head(MAX_TABLE_ROWS)
    if show_index:
        frame = frame.reset_index()

    def cell(value: Any, style: ParagraphStyle) -> Paragraph:
        if isinstance(value, float):
            text = f"{value:.6g}"
        else:
            text = str(value)
        return Paragraph(escape(text[:MAX_CELL_CHARS]), style)

    rows = [[cell(column, styles["header"]) for column in frame.columns]]
    rows.extend(
        [cell(value, styles["cell"]) for value in record]
        for record in frame.itertuples(index=False)
    )
    table = Table(
        rows,
        colWidths=[width / max(len(frame.columns), 1)] * len(frame.columns),
        repeatRows=1,
    )
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f2f2f2")),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cccccc")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )
    return table


def build_styles() -> Dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "ReportTitle", parent=base["Title"], fontSize=22, spaceAfter=6
        ),
        "meta": ParagraphStyle(
            "ReportMeta",
            parent=base["Normal"],
            textColor=colors.HexColor("#555555"),
            fontSize=9,
        ),
        "h1": ParagraphStyle(
            "H1", parent=base["Heading1"], spaceBefore=14, spaceAfter=6
        ),
        "h2": ParagraphStyle(
            "H2", parent=base["Heading2"], spaceBefore=10, spaceAfter=4
        ),
        "h3": ParagraphStyle(
            "H3", parent=base["Heading3"], spaceBefore=8, spaceAfter=3
        ),
        "body": ParagraphStyle(
            "Body", parent=base["BodyText"], leading=14, spaceAfter=6
        ),
        "header": ParagraphStyle(
            "TableHeader",
            parent=base["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=8,
            leading=10,
        ),
        "cell": ParagraphStyle(
            "TableCell", parent=base["BodyText"], fontSize=8, leading=10
        ),
    }


def build_pdf(
    output_path: str,
    title: str,
    description: str,
    author: str,
    version: str,
    sections: List[Dict[str, Any]],
    render_section: Callable[[Dict[str, Any], float], List[Any]],
) -> None:
    styles = build_styles()
    document = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
        title=title,
        author=author or "",
    )
    width = A4[0] - 4 * cm
    story: List[Any] = [Paragraph(escape(title), styles["title"])]
    if description:
        story.append(Paragraph(escape(description), styles["body"]))
    meta = f"{'Author: ' + escape(author) + ' | ' if author else ''}Version: {escape(version)} | Date: {datetime.now():%Y-%m-%d}"
    story.extend([Paragraph(meta, styles["meta"]), Spacer(1, 12)])
    for section in sections:
        if section.get("title"):
            story.append(Paragraph(escape(str(section["title"])), styles["h1"]))
        story.extend(render_section(section, width))

    def footer(canvas: Any, doc: Any) -> None:
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.HexColor("#777777"))
        canvas.drawRightString(A4[0] - 2 * cm, 1.2 * cm, f"Page {doc.page}")
        canvas.restoreState()

    document.build(story, onFirstPage=footer, onLaterPages=footer)


def image_flowable(png: bytes, width: float) -> Image:
    image = Image(BytesIO(png))
    ratio = image.imageHeight / float(image.imageWidth)
    image.drawWidth = width
    image.drawHeight = width * ratio
    return image


def paragraph_flowable(
    text: str, styles: Optional[Dict[str, ParagraphStyle]] = None
) -> Paragraph:
    return Paragraph(escape(text), (styles or build_styles())["body"])
