from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate, BaseDocTemplate, PageTemplate, Frame,
    Paragraph, Spacer, Table, TableStyle,
    HRFlowable, PageBreak, KeepTogether, NextPageTemplate
)
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_JUSTIFY
from io import BytesIO
import os

# ── Color Palettes ─────────────────────────────────────────────────────────────
PALETTES = {
    "navy":   {"primary": colors.HexColor("#1B2A4A"), "accent": colors.HexColor("#2E86AB"), "light": colors.HexColor("#EBF5FB")},
    "cvblue": {"primary": colors.HexColor("#304263"), "accent": colors.HexColor("#5D6D8A"), "light": colors.HexColor("#F4F6F9")},
    "slate":  {"primary": colors.HexColor("#2D3748"), "accent": colors.HexColor("#718096"), "light": colors.HexColor("#F7FAFC")},
    "maroon": {"primary": colors.HexColor("#6B2737"), "accent": colors.HexColor("#C9485B"), "light": colors.HexColor("#FEE8ED")},
    "forest": {"primary": colors.HexColor("#1E3A2F"), "accent": colors.HexColor("#4A7C59"), "light": colors.HexColor("#EAF2EC")},
    "charcoal":{"primary": colors.HexColor("#1A1A2E"), "accent": colors.HexColor("#E94560"), "light": colors.HexColor("#F5F5F5")},
}

W, H = A4

def _safe(val, fallback=""): return val if val else fallback

def _safe_list(val):
    """Ensures input is always a list for iteration."""
    if not val: return []
    if isinstance(val, (list, tuple)): return val
    if isinstance(val, str): return [val]
    return []

def md_to_rl(text):
    """Simple converter for basic AI markdown into ReportLab XML-like tags."""
    if not text: return ""
    import re
    text = str(text)
    # Bold: **text** -> <b>text</b>
    text = re.sub(r"\*\*(.*?)\*\*", r"<b>\1</b>", text)
    # Italic: *text* -> <i>text</i>
    text = re.sub(r"\*(.*?)\*", r"<i>\1</i>", text)
    return text

def _styles(palette_name="navy"):
    p = PALETTES.get(palette_name, PALETTES["navy"])
    s = {}
    s["h1"] = ParagraphStyle("h1", fontName="Helvetica-Bold", fontSize=28, textColor=p["primary"], alignment=TA_CENTER, spaceAfter=2, leading=32)
    s["tagline"] = ParagraphStyle("tagline", fontName="Helvetica", fontSize=12, textColor=p["accent"], alignment=TA_CENTER, spaceAfter=8, leading=14)
    s["contact"] = ParagraphStyle("contact", fontName="Helvetica", fontSize=9.5, textColor=colors.HexColor("#555555"), alignment=TA_CENTER, spaceAfter=0)
    s["section_title"] = ParagraphStyle("section_title", fontName="Helvetica-Bold", fontSize=13, textColor=p["primary"], spaceBefore=16, spaceAfter=4)
    s["job_title"] = ParagraphStyle("job_title", fontName="Helvetica-Bold", fontSize=11.5, textColor=colors.black, spaceAfter=1, leading=14)
    s["company"] = ParagraphStyle("company", fontName="Helvetica-Bold", fontSize=10.5, textColor=p["accent"], spaceAfter=2)
    s["duration"] = ParagraphStyle("duration", fontName="Helvetica", fontSize=9.5, textColor=colors.HexColor("#777777"), alignment=TA_RIGHT)
    s["bullet"] = ParagraphStyle("bullet", fontName="Helvetica", fontSize=10.5, textColor=colors.HexColor("#2D3748"), leftIndent=15, bulletIndent=5, spaceAfter=4, leading=15)
    s["body"] = ParagraphStyle("body", fontName="Helvetica", fontSize=10.5, textColor=colors.HexColor("#2D3748"), leading=15, alignment=TA_JUSTIFY, spaceAfter=8)
    
    # Sidebar
    s["side_name"] = ParagraphStyle("side_name", fontName="Helvetica-Bold", fontSize=22, textColor=colors.white, spaceAfter=6, leading=26)
    s["side_sec"] = ParagraphStyle("side_sec", fontName="Helvetica-Bold", fontSize=11.5, textColor=colors.white, spaceBefore=18, spaceAfter=8)
    s["side_body"] = ParagraphStyle("side_body", fontName="Helvetica", fontSize=10, textColor=colors.HexColor("#EEEEEE"), leading=14, spaceAfter=4)
    return s, p

def _add_sections(story, data, s, p, width_main=18*cm):
    """Generic section adder for main columns/simple layouts."""
    def add_sec_hdr(title):
        story.append(Paragraph(title.upper(), s["section_title"]))
        story.append(HRFlowable(width="100%", thickness=1.5, color=p["primary"], spaceAfter=8))

    if data.get("summary"):
        add_sec_hdr("Professional Summary")
        story.append(Paragraph(md_to_rl(data["summary"]), s["body"]))

    if data.get("experience"):
        add_sec_hdr("Work Experience")
        for exp in data["experience"]:
            sec = []
            # Duration and Title row
            t = Table([[Paragraph(md_to_rl(f"<b>{exp.get('title')}</b>"), s["job_title"]), 
                        Paragraph(md_to_rl(exp.get("duration")), s["duration"])]], 
                        colWidths=[width_main*0.7, width_main*0.3])
            t.setStyle(TableStyle([("VALIGN",(0,0),(-1,-1),"TOP"), ("LEFTPADDING",(0,0),(-1,-1),0), ("RIGHTPADDING",(0,0),(-1,-1),0)]))
            
            # Keep header and company together
            header_group = [t, Paragraph(md_to_rl(exp.get("company", "")), s["company"])]
            story.append(KeepTogether(header_group))
            
            for b in _safe_list(exp.get("bullets")): 
                story.append(Paragraph(f"• {md_to_rl(b)}", s["bullet"]))
            story.append(Spacer(1, 8))

    if data.get("projects"):
        add_sec_hdr("Key Projects")
        for proj in _safe_list(data.get("projects")):
            story.append(Paragraph(md_to_rl(f"<b>{proj.get('name')}</b>"), s["job_title"]))
            story.append(Paragraph(md_to_rl(proj.get("description", "")), s["body"]))
            if proj.get("tech"):
                story.append(Paragraph(md_to_rl(f"<i>Tech: {proj['tech']}</i>"), s["contact"].clone("p_tech", alignment=0)))
            story.append(Spacer(1, 8))

    if data.get("education"):
        add_sec_hdr("Education")
        for edu in _safe_list(data.get("education")):
            t = Table([[Paragraph(md_to_rl(f"<b>{edu.get('degree')}</b>"), s["job_title"]), 
                        Paragraph(md_to_rl(edu.get("year")), s["duration"])]], 
                        colWidths=[width_main*0.7, width_main*0.3])
            t.setStyle(TableStyle([("VALIGN",(0,0),(-1,-1),"TOP"), ("LEFTPADDING",(0,0),(-1,-1),0), ("RIGHTPADDING",(0,0),(-1,-1),0)]))
            
            # Keep degree and institution together
            edu_group = [t, Paragraph(md_to_rl(edu.get("institution", "")), s["body"])]
            story.append(KeepTogether(edu_group))
            
            if edu.get("details"): 
                story.append(Paragraph(md_to_rl(edu["details"]), s["contact"].clone("ced", alignment=0)))
            story.append(Spacer(1, 8))
            
    if data.get("skills"):
        add_sec_hdr("Skills & Expertise")
        sk = data["skills"]
        skills_text = []
        if sk.get("technical"): skills_text.append(f"<b>Technical:</b> {md_to_rl(', '.join(_safe_list(sk.get('technical'))))}")
        if sk.get("tools"):     skills_text.append(f"<b>Tools:</b> {md_to_rl(', '.join(_safe_list(sk.get('tools'))))}")
        if sk.get("soft"):      skills_text.append(f"<b>Soft Skills:</b> {md_to_rl(', '.join(_safe_list(sk.get('soft'))))}")
        story.append(Paragraph("<br/><br/>".join(skills_text), s["body"]))

    if data.get("certifications"):
        add_sec_hdr("Certifications")
        for cert in _safe_list(data.get("certifications")):
            story.append(Paragraph(f"• {md_to_rl(cert)}", s["bullet"]))

# --- Format Builders ---

def build_classic_1page(data, palette="slate"):
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=1.5*cm, rightMargin=1.5*cm, topMargin=1.5*cm, bottomMargin=1.5*cm)
    s, p = _styles(palette)
    story = [Paragraph(data.get("name", "").upper(), s["h1"]), Paragraph(data.get("tagline", ""), s["tagline"])]
    contact_txt = "  |  ".join(filter(None, [data.get("email"), data.get("phone"), data.get("location"), data.get("linkedin")]))
    story.append(Paragraph(contact_txt, s["contact"]))
    _add_sections(story, data, s, p, width_main=18*cm)
    doc.build(story); return buf.getvalue()

def build_specialized(data, palette="charcoal"):
    buf = BytesIO()
    s, p = _styles(palette)
    W, H = A4
    
    class SpecializedDoc(BaseDocTemplate):
        def draw_header(self, canvas, doc):
            # Header ONLY on Page 1
            if doc.page == 1:
                canvas.saveState()
                canvas.setFillColor(p["primary"])
                canvas.rect(0, H-4*cm, W, 4*cm, stroke=0, fill=1)
                
                h_s = ParagraphStyle("h_s", fontName="Helvetica-Bold", fontSize=26, textColor=colors.white, alignment=TA_CENTER)
                t_s = ParagraphStyle("t_s", fontName="Helvetica", fontSize=12, textColor=colors.HexColor("#CCCCCC"), alignment=TA_CENTER)
                
                hdr_table = Table([
                    [Paragraph(data.get("name", "").upper(), h_s)],
                    [Paragraph(data.get("tagline", ""), t_s)]
                ], colWidths=[W-2*cm])
                
                w, h = hdr_table.wrap(W-2*cm, 4*cm)
                hdr_table.drawOn(canvas, 1*cm, H - 0.5*cm - h)
                canvas.restoreState()

    doc = SpecializedDoc(buf, pagesize=A4, leftMargin=1.5*cm, rightMargin=1.5*cm, topMargin=4.5*cm, bottomMargin=1.5*cm)
    
    # Define Frames with precise coordinates
    # f1: Room for 4.5cm header
    f1 = Frame(1.5*cm, 1.5*cm, W-3*cm, H-6*cm, id='normal')
    # f2: Full page with 1.5cm margins
    f2 = Frame(1.5*cm, 1.5*cm, W-3*cm, H-3*cm, id='later') 
    
    doc.addPageTemplates([
        PageTemplate(id='First', frames=[f1], onPage=doc.draw_header),
        PageTemplate(id='Later', frames=[f2], onPage=doc.draw_header)
    ])
    
    story = [NextPageTemplate('Later')]
    contact_txt = "  •  ".join(filter(None, [data.get("email"), data.get("phone"), data.get("location"), data.get("linkedin")]))
    story.append(Paragraph(md_to_rl(contact_txt), s["contact"]))
    story.append(Spacer(1, 10))
    _add_sections(story, data, s, p, width_main=18*cm)
    
    doc.build(story)
    return buf.getvalue()

# ── Sidebar Template Support ──────────────────────────────────────────────────

class SidebarDocTemplate(BaseDocTemplate):
    def __init__(self, filename, side="left", palette=None, sidebar_content=None, styles=None, **kwargs):
        BaseDocTemplate.__init__(self, filename, **kwargs)
        self.side_pos = side
        self.p = palette
        self.sidebar_content = sidebar_content
        self.s = styles
        W, H = A4
        sw = 6.5*cm
        mw = W-sw
        if side == "left":
            f = Frame(sw, 0, mw, H, leftPadding=20, rightPadding=20, topPadding=30, bottomPadding=30)
        else:
            f = Frame(0, 0, mw, H, leftPadding=20, rightPadding=20, topPadding=30, bottomPadding=30)
        self.addPageTemplates([PageTemplate(id='Sidebar', frames=[f], onPage=self.draw_sidebar)])

    def draw_sidebar(self, canvas, doc):
        canvas.saveState()
        W, H = A4
        sw = 6.5*cm
        canvas.setFillColor(self.p["primary"])
        if self.side_pos == "left":
            canvas.rect(0, 0, sw, H, stroke=0, fill=1)
            sx = 0
        else:
            canvas.rect(W-sw, 0, sw, H, stroke=0, fill=1)
            sx = W-sw
        
        # Draw Sidebar content on first page
        if doc.page == 1 and self.sidebar_content:
            curr_y = H - 30
            for item in self.sidebar_content:
                w, h = item.wrap(sw-40, H)
                item.drawOn(canvas, sx+20, curr_y-h)
                curr_y -= (h+5)
        canvas.restoreState()

def _sidebar_content(data, s, p):
    content = [Spacer(1, 25), Paragraph(md_to_rl(data.get("name", "")), s["side_name"]), Spacer(1, 10)]
    content.append(Paragraph("CONTACT", s["side_sec"]))
    for item in filter(None, [data.get("phone"), data.get("location"), data.get("email")]):
        content.append(Paragraph(f"• {md_to_rl(item)}", s["side_body"]))
    if data.get("skills"):
        content.append(Paragraph("TOP SKILLS", s["side_sec"]))
        for sk in _safe_list(data["skills"].get("technical"))[:10]: 
            content.append(Paragraph(f"• {md_to_rl(sk)}", s["side_body"]))
    if data.get("education"):
        content.append(Paragraph("EDUCATION", s["side_sec"]))
        for edu in _safe_list(data.get("education")):
            content.append(Paragraph(md_to_rl(f"<b>{edu.get('degree')}</b>"), s["side_body"].clone("edu_d", textColor=colors.white)))
            content.append(Paragraph(md_to_rl(edu.get("institution", "")), s["side_body"]))
            content.append(Paragraph(md_to_rl(edu.get("year", "")), s["side_body"]))
            content.append(Spacer(1, 8))
    return content

def build_sidebar_left(data, palette="navy"):
    buf = BytesIO()
    s, p = _styles(palette)
    side = _sidebar_content(data, s, p)
    main = []; _add_sections(main, data, s, p, width_main=12.5*cm)
    doc = SidebarDocTemplate(buf, side="left", palette=p, sidebar_content=side, styles=s, pagesize=A4)
    doc.build(main)
    return buf.getvalue()

def build_sidebar_right(data, palette="maroon"):
    buf = BytesIO()
    s, p = _styles(palette)
    side = _sidebar_content(data, s, p)
    main = []; _add_sections(main, data, s, p, width_main=12.5*cm)
    doc = SidebarDocTemplate(buf, side="right", palette=p, sidebar_content=side, styles=s, pagesize=A4)
    doc.build(main)
    return buf.getvalue()

def build_modern_2page(data, palette="cvblue"):
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=1.8*cm, rightMargin=1.8*cm, topMargin=1.5*cm, bottomMargin=1.5*cm)
    s, p = _styles(palette); story = []
    # Header
    hdr = Table([[Paragraph(data.get("name", ""), s["h1"].clone("hL", alignment=0)), Paragraph(data.get("tagline", ""), s["tagline"].clone("tL", alignment=2))]], colWidths=[10*cm, 7*cm])
    story.append(hdr); story.append(HRFlowable(width="100%", thickness=2.5, color=p["primary"], spaceAfter=10))
    # Standard sections with PageBreak potential (automatic in ReportLab)
    _add_sections(story, data, s, p, width_main=17*cm)
    doc.build(story); return buf.getvalue()

FORMATS = {
    "classic_1page": ("Classic ATS Single Column", build_classic_1page, "slate"),
    "specialized": ("Specialized Technical (Dark)", build_specialized, "charcoal"),
    "sidebar_left": ("Elite Two-Column (Left)", build_sidebar_left, "navy"),
    "sidebar_right": ("Elite Two-Column (Right)", build_sidebar_right, "maroon"),
    "modern_2page": ("Modern 2-Page Elite", build_modern_2page, "cvblue"),
}
