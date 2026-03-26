"""
pdf_generator.py
Generates professional CV PDFs in multiple formats:
- classic_1page: Traditional 1-page, single column
- modern_2page: 2-page modern layout  
- sidebar_left: Left sidebar colored layout (popular)
- sidebar_right: Right sidebar layout
- minimal_clean: Ultra minimal ATS-friendly
"""

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm, mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, KeepTogether, PageBreak
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT, TA_JUSTIFY
from reportlab.platypus.flowables import Flowable
from io import BytesIO
import os


# ── Color Palettes ─────────────────────────────────────────────────────────────
PALETTES = {
    "navy":   {"primary": colors.HexColor("#1B2A4A"), "accent": colors.HexColor("#2E86AB"), "light": colors.HexColor("#EBF5FB")},
    "forest": {"primary": colors.HexColor("#1B4332"), "accent": colors.HexColor("#40916C"), "light": colors.HexColor("#D8F3DC")},
    "slate":  {"primary": colors.HexColor("#2D3748"), "accent": colors.HexColor("#718096"), "light": colors.HexColor("#F7FAFC")},
    "maroon": {"primary": colors.HexColor("#6B2737"), "accent": colors.HexColor("#C9485B"), "light": colors.HexColor("#FEE8ED")},
}

W, H = A4  # 595.27 x 841.89 pts


def _safe(val, fallback=""):
    return val if val else fallback


def _styles(palette_name="navy"):
    p = PALETTES[palette_name]
    base = getSampleStyleSheet()
    s = {}

    s["name"] = ParagraphStyle("name", fontName="Helvetica-Bold", fontSize=22,
                                textColor=p["primary"], spaceAfter=2, leading=26)
    s["tagline"] = ParagraphStyle("tagline", fontName="Helvetica-Oblique", fontSize=10,
                                   textColor=p["accent"], spaceAfter=6)
    s["contact"] = ParagraphStyle("contact", fontName="Helvetica", fontSize=8.5,
                                   textColor=colors.HexColor("#555555"), spaceAfter=2)
    s["section_title"] = ParagraphStyle("section_title", fontName="Helvetica-Bold", fontSize=11,
                                         textColor=p["primary"], spaceBefore=10, spaceAfter=4)
    s["job_title"] = ParagraphStyle("job_title", fontName="Helvetica-Bold", fontSize=10,
                                     textColor=colors.black, spaceAfter=1)
    s["company"] = ParagraphStyle("company", fontName="Helvetica-Oblique", fontSize=9.5,
                                   textColor=p["accent"], spaceAfter=1)
    s["duration"] = ParagraphStyle("duration", fontName="Helvetica", fontSize=9,
                                    textColor=colors.HexColor("#888888"), spaceAfter=3)
    s["bullet"] = ParagraphStyle("bullet", fontName="Helvetica", fontSize=9.5,
                                  textColor=colors.HexColor("#333333"), leftIndent=12,
                                  bulletIndent=4, spaceAfter=2, leading=13)
    s["body"] = ParagraphStyle("body", fontName="Helvetica", fontSize=9.5,
                                textColor=colors.HexColor("#333333"), spaceAfter=3,
                                leading=13, alignment=TA_JUSTIFY)
    s["skill_tag"] = ParagraphStyle("skill_tag", fontName="Helvetica", fontSize=9,
                                     textColor=p["primary"], spaceAfter=2)
    s["sidebar_name"] = ParagraphStyle("sidebar_name", fontName="Helvetica-Bold", fontSize=18,
                                        textColor=colors.white, spaceAfter=4, leading=22)
    s["sidebar_tagline"] = ParagraphStyle("sidebar_tagline", fontName="Helvetica-Oblique",
                                           fontSize=9, textColor=colors.HexColor("#DDDDDD"),
                                           spaceAfter=8)
    s["sidebar_section"] = ParagraphStyle("sidebar_section", fontName="Helvetica-Bold",
                                           fontSize=10, textColor=colors.white,
                                           spaceBefore=10, spaceAfter=4)
    s["sidebar_body"] = ParagraphStyle("sidebar_body", fontName="Helvetica", fontSize=8.5,
                                        textColor=colors.HexColor("#EEEEEE"), spaceAfter=3,
                                        leading=12)
    s["page_num"] = ParagraphStyle("page_num", fontName="Helvetica", fontSize=8,
                                    textColor=colors.HexColor("#AAAAAA"), alignment=TA_CENTER)
    return s, p


def _section_rule(p):
    return HRFlowable(width="100%", thickness=1.5, color=p["primary"], spaceAfter=4)


# ── FORMAT 1: Classic 1-Page ATS ──────────────────────────────────────────────
def build_classic_1page(data: dict, palette="navy") -> bytes:
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4,
                             leftMargin=1.8*cm, rightMargin=1.8*cm,
                             topMargin=1.5*cm, bottomMargin=1.5*cm)
    s, p = _styles(palette)
    story = []

    # Header
    story.append(Paragraph(_safe(data.get("name"), "Your Name"), s["name"]))
    if data.get("tagline"):
        story.append(Paragraph(data["tagline"], s["tagline"]))

    contacts = " | ".join(filter(None, [
        data.get("email"), data.get("phone"),
        data.get("location"), data.get("linkedin")
    ]))
    story.append(Paragraph(contacts, s["contact"]))
    story.append(_section_rule(p))

    # Summary
    if data.get("summary"):
        story.append(Paragraph("PROFESSIONAL SUMMARY", s["section_title"]))
        story.append(Paragraph(data["summary"], s["body"]))

    # Experience
    if data.get("experience"):
        story.append(Paragraph("EXPERIENCE", s["section_title"]))
        story.append(_section_rule(p))
        for exp in data["experience"]:
            story.append(Paragraph(_safe(exp.get("title")), s["job_title"]))
            story.append(Paragraph(
                f"{_safe(exp.get('company'))}  •  {_safe(exp.get('duration'))}",
                s["company"]
            ))
            for b in exp.get("bullets", []):
                story.append(Paragraph(f"▸  {b}", s["bullet"]))
            story.append(Spacer(1, 4))

    # Education
    if data.get("education"):
        story.append(Paragraph("EDUCATION", s["section_title"]))
        story.append(_section_rule(p))
        for edu in data["education"]:
            story.append(Paragraph(
                f"<b>{_safe(edu.get('degree'))}</b> — {_safe(edu.get('institution'))}  ({_safe(edu.get('year'))})",
                s["body"]
            ))
            if edu.get("details"):
                story.append(Paragraph(edu["details"], s["contact"]))

    # Skills
    if data.get("skills"):
        story.append(Paragraph("SKILLS", s["section_title"]))
        story.append(_section_rule(p))
        sk = data["skills"]
        rows = []
        if sk.get("technical"):
            rows.append(["Technical:", ", ".join(sk["technical"])])
        if sk.get("tools"):
            rows.append(["Tools:", ", ".join(sk["tools"])])
        if sk.get("soft"):
            rows.append(["Soft Skills:", ", ".join(sk["soft"])])
        tbl = Table(rows, colWidths=[2.5*cm, 14*cm])
        tbl.setStyle(TableStyle([
            ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 9.5),
            ("TEXTCOLOR", (0, 0), (0, -1), p["primary"]),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]))
        story.append(tbl)

    # Certifications
    if data.get("certifications"):
        story.append(Paragraph("CERTIFICATIONS", s["section_title"]))
        story.append(_section_rule(p))
        for cert in data["certifications"]:
            story.append(Paragraph(f"▸  {cert}", s["bullet"]))

    doc.build(story)
    return buf.getvalue()


# ── FORMAT 2: Modern 2-Page ───────────────────────────────────────────────────
def build_modern_2page(data: dict, palette="slate") -> bytes:
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4,
                             leftMargin=2*cm, rightMargin=2*cm,
                             topMargin=1.8*cm, bottomMargin=1.8*cm)
    s, p = _styles(palette)
    story = []

    # Page 1 Header — large name block
    header_data = [[
        Paragraph(_safe(data.get("name"), "Your Name"), s["name"]),
        Paragraph(_safe(data.get("tagline"), ""), s["tagline"])
    ]]
    ht = Table(header_data, colWidths=[10*cm, 7*cm])
    ht.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "BOTTOM"),
        ("BACKGROUND", (0, 0), (-1, -1), p["light"]),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 12),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
    ]))
    story.append(ht)
    story.append(Spacer(1, 6))

    contacts = "  •  ".join(filter(None, [
        data.get("email"), data.get("phone"),
        data.get("location"), data.get("linkedin")
    ]))
    story.append(Paragraph(contacts, s["contact"]))
    story.append(Spacer(1, 8))

    # Summary
    if data.get("summary"):
        story.append(Paragraph("ABOUT ME", s["section_title"]))
        story.append(_section_rule(p))
        story.append(Paragraph(data["summary"], s["body"]))

    # Experience — full page 1
    if data.get("experience"):
        story.append(Paragraph("PROFESSIONAL EXPERIENCE", s["section_title"]))
        story.append(_section_rule(p))
        for exp in data["experience"]:
            block = []
            block.append(Paragraph(_safe(exp.get("title")), s["job_title"]))
            block.append(Paragraph(
                f"{_safe(exp.get('company'))}  |  {_safe(exp.get('duration'))}", s["company"]
            ))
            for b in exp.get("bullets", []):
                block.append(Paragraph(f"◆  {b}", s["bullet"]))
            block.append(Spacer(1, 6))
            story.extend(block)

    # Page 2
    story.append(PageBreak())
    story.append(Paragraph(_safe(data.get("name"), ""), s["tagline"]))
    story.append(Spacer(1, 4))

    # Education
    if data.get("education"):
        story.append(Paragraph("EDUCATION", s["section_title"]))
        story.append(_section_rule(p))
        for edu in data["education"]:
            story.append(Paragraph(
                f"<b>{_safe(edu.get('degree'))}</b>  —  {_safe(edu.get('institution'))}",
                s["job_title"]
            ))
            story.append(Paragraph(f"{_safe(edu.get('year'))}  {_safe(edu.get('details'))}", s["contact"]))
            story.append(Spacer(1, 4))

    # Projects
    if data.get("projects"):
        story.append(Paragraph("KEY PROJECTS", s["section_title"]))
        story.append(_section_rule(p))
        for proj in data["projects"]:
            story.append(Paragraph(f"<b>{_safe(proj.get('name'))}</b>", s["job_title"]))
            story.append(Paragraph(_safe(proj.get("description")), s["body"]))
            story.append(Paragraph(f"Tech: {_safe(proj.get('tech'))}", s["contact"]))
            story.append(Spacer(1, 4))

    # Skills
    if data.get("skills"):
        story.append(Paragraph("SKILLS & EXPERTISE", s["section_title"]))
        story.append(_section_rule(p))
        sk = data["skills"]
        all_skills = (sk.get("technical", []) + sk.get("tools", []) + sk.get("soft", []))
        story.append(Paragraph("  •  ".join(all_skills), s["body"]))

    # Certifications
    if data.get("certifications"):
        story.append(Paragraph("CERTIFICATIONS", s["section_title"]))
        story.append(_section_rule(p))
        for cert in data["certifications"]:
            story.append(Paragraph(f"✓  {cert}", s["bullet"]))

    doc.build(story)
    return buf.getvalue()


# ── FORMAT 3: Left Sidebar (very popular 2024-25) ────────────────────────────
def _build_sidebar(data: dict, palette: str, sidebar_side: str) -> bytes:
    buf = BytesIO()
    s, p = _styles(palette)

    SIDEBAR_W = 5.8 * cm
    MAIN_W = W - SIDEBAR_W - 2.5 * cm

    # Build sidebar content (name, contact, skills)
    sidebar_items = []
    sidebar_items.append(Paragraph(_safe(data.get("name"), "Your Name"), s["sidebar_name"]))
    if data.get("tagline"):
        sidebar_items.append(Paragraph(data["tagline"], s["sidebar_tagline"]))
    sidebar_items.append(Spacer(1, 6))

    # Contact in sidebar
    sidebar_items.append(Paragraph("CONTACT", s["sidebar_section"]))
    for item in filter(None, [data.get("email"), data.get("phone"),
                               data.get("location"), data.get("linkedin")]):
        sidebar_items.append(Paragraph(item, s["sidebar_body"]))

    # Skills in sidebar
    if data.get("skills"):
        sk = data["skills"]
        if sk.get("technical"):
            sidebar_items.append(Paragraph("TECHNICAL SKILLS", s["sidebar_section"]))
            for skill in sk["technical"]:
                sidebar_items.append(Paragraph(f"• {skill}", s["sidebar_body"]))
        if sk.get("tools"):
            sidebar_items.append(Paragraph("TOOLS", s["sidebar_section"]))
            for t in sk["tools"]:
                sidebar_items.append(Paragraph(f"• {t}", s["sidebar_body"]))
        if sk.get("soft"):
            sidebar_items.append(Paragraph("SOFT SKILLS", s["sidebar_section"]))
            for ss in sk["soft"]:
                sidebar_items.append(Paragraph(f"• {ss}", s["sidebar_body"]))

    if data.get("certifications"):
        sidebar_items.append(Paragraph("CERTIFICATIONS", s["sidebar_section"]))
        for cert in data["certifications"]:
            sidebar_items.append(Paragraph(f"• {cert}", s["sidebar_body"]))

    # Build main content
    main_items = []
    if data.get("summary"):
        main_items.append(Paragraph("PROFESSIONAL SUMMARY", s["section_title"]))
        main_items.append(_section_rule(p))
        main_items.append(Paragraph(data["summary"], s["body"]))
        main_items.append(Spacer(1, 6))

    if data.get("experience"):
        main_items.append(Paragraph("EXPERIENCE", s["section_title"]))
        main_items.append(_section_rule(p))
        for exp in data["experience"]:
            main_items.append(Paragraph(_safe(exp.get("title")), s["job_title"]))
            main_items.append(Paragraph(
                f"{_safe(exp.get('company'))}  |  {_safe(exp.get('duration'))}", s["company"]
            ))
            for b in exp.get("bullets", []):
                main_items.append(Paragraph(f"▸  {b}", s["bullet"]))
            main_items.append(Spacer(1, 5))

    if data.get("education"):
        main_items.append(Paragraph("EDUCATION", s["section_title"]))
        main_items.append(_section_rule(p))
        for edu in data["education"]:
            main_items.append(Paragraph(
                f"<b>{_safe(edu.get('degree'))}</b>  —  {_safe(edu.get('institution'))}  ({_safe(edu.get('year'))})",
                s["body"]
            ))
            if edu.get("details"):
                main_items.append(Paragraph(edu["details"], s["contact"]))
            main_items.append(Spacer(1, 3))

    if data.get("projects"):
        main_items.append(Paragraph("PROJECTS", s["section_title"]))
        main_items.append(_section_rule(p))
        for proj in data["projects"]:
            main_items.append(Paragraph(f"<b>{_safe(proj.get('name'))}</b>", s["job_title"]))
            main_items.append(Paragraph(_safe(proj.get("description")), s["body"]))

    # Render using Table for two-column layout
    def wrap_sidebar(items):
        from reportlab.platypus import Frame
        return items

    if sidebar_side == "left":
        col_data = [[sidebar_items, main_items]]
        col_widths = [SIDEBAR_W, MAIN_W]
    else:
        col_data = [[main_items, sidebar_items]]
        col_widths = [MAIN_W, SIDEBAR_W]

    # We use nested tables — sidebar col gets background color
    sidebar_tbl_data = [[item] for item in sidebar_items]
    main_tbl_data = [[item] for item in main_items]

    sidebar_inner = Table(sidebar_tbl_data, colWidths=[SIDEBAR_W - 0.5*cm])
    sidebar_inner.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), p["primary"]),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))

    main_inner = Table(main_tbl_data, colWidths=[MAIN_W - 0.5*cm])
    main_inner.setStyle(TableStyle([
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))

    if sidebar_side == "left":
        outer = Table([[sidebar_inner, main_inner]], colWidths=[SIDEBAR_W, MAIN_W])
    else:
        outer = Table([[main_inner, sidebar_inner]], colWidths=[MAIN_W, SIDEBAR_W])

    outer.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))

    doc = SimpleDocTemplate(buf, pagesize=A4,
                             leftMargin=0, rightMargin=0,
                             topMargin=0, bottomMargin=0)
    doc.build([outer])
    return buf.getvalue()


def build_sidebar_left(data: dict, palette="navy") -> bytes:
    return _build_sidebar(data, palette, "left")


def build_sidebar_right(data: dict, palette="maroon") -> bytes:
    return _build_sidebar(data, palette, "right")


# ── FORMAT 5: Minimal Clean (best for ATS) ───────────────────────────────────
def build_minimal_clean(data: dict, palette="slate") -> bytes:
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4,
                             leftMargin=2.2*cm, rightMargin=2.2*cm,
                             topMargin=2*cm, bottomMargin=2*cm)
    s, p = _styles("slate")
    story = []

    name_style = ParagraphStyle("mn", fontName="Helvetica-Bold", fontSize=20,
                                  textColor=colors.black, spaceAfter=2, alignment=TA_CENTER)
    contact_style = ParagraphStyle("mc", fontName="Helvetica", fontSize=9,
                                    textColor=colors.HexColor("#444444"), spaceAfter=8,
                                    alignment=TA_CENTER)
    sec_style = ParagraphStyle("ms", fontName="Helvetica-Bold", fontSize=10,
                                 textColor=colors.black, spaceBefore=10, spaceAfter=2,
                                 borderPad=2)

    story.append(Paragraph(_safe(data.get("name"), "Your Name"), name_style))
    contacts = "  |  ".join(filter(None, [
        data.get("email"), data.get("phone"),
        data.get("location"), data.get("linkedin")
    ]))
    story.append(Paragraph(contacts, contact_style))
    story.append(HRFlowable(width="100%", thickness=2, color=colors.black, spaceAfter=6))

    if data.get("summary"):
        story.append(Paragraph("SUMMARY", sec_style))
        story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#CCCCCC")))
        story.append(Spacer(1, 3))
        story.append(Paragraph(data["summary"], s["body"]))

    if data.get("experience"):
        story.append(Paragraph("EXPERIENCE", sec_style))
        story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#CCCCCC")))
        story.append(Spacer(1, 3))
        for exp in data["experience"]:
            row = Table([[
                Paragraph(f"<b>{_safe(exp.get('title'))}</b>, {_safe(exp.get('company'))}", s["body"]),
                Paragraph(_safe(exp.get("duration")), s["duration"])
            ]], colWidths=[12*cm, 4.5*cm])
            row.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0,0),(-1,-1), 0)]))
            story.append(row)
            for b in exp.get("bullets", []):
                story.append(Paragraph(f"•  {b}", s["bullet"]))
            story.append(Spacer(1, 4))

    if data.get("education"):
        story.append(Paragraph("EDUCATION", sec_style))
        story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#CCCCCC")))
        story.append(Spacer(1, 3))
        for edu in data["education"]:
            story.append(Paragraph(
                f"<b>{_safe(edu.get('degree'))}</b>, {_safe(edu.get('institution'))} — {_safe(edu.get('year'))}",
                s["body"]
            ))

    if data.get("skills"):
        story.append(Paragraph("SKILLS", sec_style))
        story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#CCCCCC")))
        story.append(Spacer(1, 3))
        sk = data["skills"]
        all_sk = sk.get("technical", []) + sk.get("tools", []) + sk.get("soft", [])
        story.append(Paragraph(" • ".join(all_sk), s["body"]))

    if data.get("certifications"):
        story.append(Paragraph("CERTIFICATIONS", sec_style))
        story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#CCCCCC")))
        story.append(Spacer(1, 3))
        story.append(Paragraph("  •  ".join(data["certifications"]), s["body"]))

    doc.build(story)
    return buf.getvalue()


# ── Master builder ─────────────────────────────────────────────────────────────
FORMATS = {
    "classic_1page":  ("Classic 1-Page (ATS Friendly)", build_classic_1page),
    "modern_2page":   ("Modern 2-Page",                  build_modern_2page),
    "sidebar_left":   ("Left Sidebar Layout",             build_sidebar_left),
    "sidebar_right":  ("Right Sidebar Layout",            build_sidebar_right),
    "minimal_clean":  ("Minimal Clean (Best ATS)",        build_minimal_clean),
}


def generate_all_formats(data: dict, output_dir: str) -> dict:
    """Generate all CV formats. Returns {format_key: filepath}"""
    os.makedirs(output_dir, exist_ok=True)
    paths = {}
    for key, (label, builder) in FORMATS.items():
        try:
            pdf_bytes = builder(data)
            path = os.path.join(output_dir, f"cv_{key}.pdf")
            with open(path, "wb") as f:
                f.write(pdf_bytes)
            paths[key] = {"path": path, "label": label}
        except Exception as e:
            print(f"Error generating {key}: {e}")
    return paths
