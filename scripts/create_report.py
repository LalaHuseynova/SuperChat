"""Render the four-page technical report from its readable Markdown source."""

from pathlib import Path
from xml.sax.saxutils import escape
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    PageBreak,
    KeepTogether,
)

root = Path(__file__).resolve().parents[1]
source = (root / "docs/TECHNICAL_REPORT.md").read_text()
output = root / "docs/TECHNICAL_REPORT.pdf"
green = colors.HexColor("#244f3f")
grey = colors.HexColor("#6e7f70")
body = ParagraphStyle(
    "Body",
    fontName="Helvetica",
    fontSize=10,
    leading=15,
    textColor=colors.HexColor("#33443b"),
    spaceAfter=11,
)
heading = ParagraphStyle(
    "Heading",
    fontName="Helvetica-Bold",
    fontSize=15,
    leading=20,
    textColor=green,
    spaceBefore=8,
    spaceAfter=16,
)
title = ParagraphStyle(
    "Title",
    fontName="Helvetica",
    fontSize=31,
    leading=35,
    textColor=green,
    spaceAfter=14,
)
kicker = ParagraphStyle(
    "Kicker",
    fontName="Helvetica-Bold",
    fontSize=8,
    leading=12,
    textColor=grey,
    spaceAfter=13,
)
small = ParagraphStyle(
    "Small", fontName="Helvetica", fontSize=8, leading=12, textColor=grey, spaceAfter=6
)


def clean(s):
    return (
        s.replace("—", "-")
        .replace("–", "-")
        .replace("→", ">")
        .replace("≥", ">=")
        .replace("“", '"')
        .replace("”", '"')
        .replace("’", "'")
    )


story = []
for block in source.split("\n\n"):
    block = clean(block.strip())
    if not block:
        continue
    if block.startswith("# "):
        story.extend(
            [
                Paragraph("COMPETITION BUILD / 02 NOVEMBER 2026", kicker),
                Paragraph("SuperChat", title),
                Paragraph("Phase 1 technical report", heading),
                Spacer(1, 10),
            ]
        )
    elif block.startswith("## "):
        section = block[3:]
        if section.startswith(("3.", "5.", "6.")):
            story.append(PageBreak())
        story.append(Paragraph(escape(section), heading))
    else:
        story.append(Paragraph(escape(block.replace("\n", " ")), body))

links = [
    (
        "Router pattern",
        "https://github.com/langchain-ai/docs/blob/main/src/oss/langchain/multi-agent/router-knowledge-base.mdx",
    ),
    (
        "RAG research template",
        "https://github.com/langchain-ai/rag-research-agent-template",
    ),
    ("LangGraph Supervisor", "https://github.com/langchain-ai/langgraph-supervisor-py"),
    (
        "OpenRouter structured outputs",
        "https://openrouter.ai/docs/guides/features/structured-outputs",
    ),
    (
        "CLIP model and model card",
        "https://huggingface.co/openai/clip-vit-base-patch32",
    ),
    (
        "Web Speech API",
        "https://developer.mozilla.org/en-US/docs/Web/API/Web_Speech_API",
    ),
]
story.append(Spacer(1, 8))
for label, url in links:
    story.append(
        Paragraph(f'<link href="{url}" color="#244f3f">{escape(label)}</link>', small)
    )


def decorate(canvas, doc):
    w, h = A4
    canvas.saveState()
    canvas.setStrokeColor(colors.HexColor("#dce4d7"))
    canvas.line(44, h - 35, w - 44, h - 35)
    canvas.line(44, 37, w - 44, 37)
    canvas.setFillColor(grey)
    canvas.setFont("Helvetica", 8)
    canvas.drawString(44, h - 27, "SUPERCHAT / TECHNICAL REPORT")
    canvas.drawRightString(w - 44, 24, f"{doc.page} / 4")
    canvas.drawString(44, 24, "Mock data. Local durable sessions. No real payments.")
    canvas.restoreState()


doc = SimpleDocTemplate(
    str(output),
    pagesize=A4,
    rightMargin=44,
    leftMargin=44,
    topMargin=54,
    bottomMargin=53,
    title="SuperChat - Phase 1 technical report",
    author="SuperChat Project",
)
doc.build(story, onFirstPage=decorate, onLaterPages=decorate)
import pymupdf

pdf = pymupdf.open(output)
assert len(pdf) == 4, f"Expected 4 pages, got {len(pdf)}"
preview = root / "tmp/pdfs"
preview.mkdir(parents=True, exist_ok=True)
for i, page in enumerate(pdf):
    page.get_pixmap(matrix=pymupdf.Matrix(1.5, 1.5)).save(
        preview / f"report-{i + 1}.png"
    )
print(f"Wrote {output} ({len(pdf)} pages)")
