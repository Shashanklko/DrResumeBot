#!/usr/bin/env node
/**
 * docx_generator.js — Professional CV Word Document Generator
 * 5 formats matching the PDF generator:
 *   1. classic_1page    — Classic ATS single column
 *   2. specialized      — Specialized/Technical dark header accent
 *   3. sidebar_left     — Two-column left sidebar
 *   4. sidebar_right    — Two-column right sidebar
 *   5. modern_2page     — Full 2-page modern layout
 */

const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  AlignmentType, BorderStyle, WidthType, ShadingType,
  VerticalAlign, LevelFormat, HeightRule
} = require('docx');
const fs = require('fs');
const path = require('path');

// ── Palette definitions (hex strings) ─────────────────────────────────────────
const PALETTES = {
  slate:    { primary: "2D3748", accent: "718096", light: "F7FAFC" },
  charcoal: { primary: "1A1A2E", accent: "E94560", light: "F5F5F5" },
  navy:     { primary: "1B2A4A", accent: "2E86AB", light: "EBF5FB" },
  maroon:   { primary: "6B2737", accent: "C9485B", light: "FEE8ED" },
  cvblue:   { primary: "304263", accent: "5D6D8A", light: "F4F6F9" },
};

const safe = (val, fallback = "") => val || fallback;

// Helper to ensure bullets are an array
const safeBullets = (bullets) => {
  if (!bullets) return [];
  if (Array.isArray(bullets)) return bullets;
  if (typeof bullets === 'string') return [bullets];
  return [];
};

// Page: A4, margins in DXA (1 inch = 1440)
const PAGE_W = 11906;
const CONTENT_W = 9026;

function noBorder() {
  const nb = { style: BorderStyle.NONE, size: 0, color: "FFFFFF" };
  return { top: nb, bottom: nb, left: nb, right: nb };
}

function bottomBorderOnly(color, size = 8) {
  return {
    top:    { style: BorderStyle.NONE, size: 0, color: "FFFFFF" },
    left:   { style: BorderStyle.NONE, size: 0, color: "FFFFFF" },
    right:  { style: BorderStyle.NONE, size: 0, color: "FFFFFF" },
    bottom: { style: BorderStyle.SINGLE, size, color },
  };
}

function hrParagraph(color, size = 8) {
  return new Paragraph({
    border: bottomBorderOnly(color, size),
    spacing: { before: 0, after: 120 },
    children: [new TextRun("")],
  });
}

// ── Section Helpers ─────────────────────────────────────────────────────────

function sectionHeader(title, p, options = {}) {
  const color = options.color || p.primary;
  return [
    new Paragraph({ 
      spacing: { before: 240, after: 60 }, 
      children: [new TextRun({ text: title.toUpperCase(), bold: true, size: 22, font: "Arial", color: color })] 
    }),
    hrParagraph(options.hrColor || color, 8)
  ];
}

function experienceBlock(exp, p, bulletRef, width = CONTENT_W) {
  const titleW = Math.floor(width * 0.75);
  const dateW = width - titleW;
  
  const cells = [
    new TableCell({
      width: { size: titleW, type: WidthType.DXA },
      borders: noBorder(),
      children: [new Paragraph({ children: [new TextRun({ text: safe(exp.title), bold: true, size: 21, font: "Arial", color: "000000" })] })],
    }),
    new TableCell({
      width: { size: dateW, type: WidthType.DXA },
      borders: noBorder(),
      children: [new Paragraph({ alignment: AlignmentType.RIGHT, children: [new TextRun({ text: safe(exp.duration), size: 18, font: "Arial", color: "666666" })] })],
    })
  ];

  const rows = [
    new Table({ width: { size: width, type: WidthType.DXA }, rows: [new TableRow({ children: cells })], borders: noBorder() }),
    new Paragraph({ spacing: { before: 20, after: 40 }, children: [new TextRun({ text: safe(exp.company), bold: true, size: 19, color: p.accent, font: "Arial" })] })
  ];

  safeBullets(exp.bullets).forEach(b => {
    rows.push(new Paragraph({ numbering: { reference: bulletRef, level: 0 }, spacing: { before: 20, after: 20 }, children: [new TextRun({ text: b, size: 19, font: "Arial" })] }));
  });
  
  rows.push(new Paragraph({ spacing: { after: 60 }, children: [new TextRun("")] }));
  return rows;
}

function educationBlock(edu, width = CONTENT_W) {
  const titleW = Math.floor(width * 0.75);
  const dateW = width - titleW;

  return [
    new Table({
      width: { size: width, type: WidthType.DXA },
      borders: noBorder(),
      rows: [new TableRow({ children: [
        new TableCell({
          width: { size: titleW, type: WidthType.DXA },
          borders: noBorder(),
          children: [new Paragraph({ children: [new TextRun({ text: safe(edu.degree), bold: true, size: 21, font: "Arial" })] })],
        }),
        new TableCell({
          width: { size: dateW, type: WidthType.DXA },
          borders: noBorder(),
          children: [new Paragraph({ alignment: AlignmentType.RIGHT, children: [new TextRun({ text: safe(edu.year), size: 18, font: "Arial", color: "666666" })] })],
        }),
      ]})],
    }),
    new Paragraph({ spacing: { before: 20, after: 40 }, children: [new TextRun({ text: safe(edu.institution), size: 19, font: "Arial" })] }),
    edu.details ? new Paragraph({ spacing: { after: 60 }, children: [new TextRun({ text: edu.details, size: 18, font: "Arial", italic: true, color: "444444" })] }) : new Paragraph({ spacing: { after: 40 }, children: [new TextRun("")] })
  ];
}

function projectBlock(proj, width = CONTENT_W) {
  const rows = [
    new Paragraph({ spacing: { before: 40, after: 20 }, children: [new TextRun({ text: safe(proj.name), bold: true, size: 20, font: "Arial" })] }),
    new Paragraph({ spacing: { after: 40 }, children: [new TextRun({ text: safe(proj.description), size: 19, font: "Arial" })] })
  ];
  if (proj.tech) {
    rows.push(new Paragraph({ spacing: { after: 60 }, children: [new TextRun({ text: `Technologies: ${proj.tech}`, size: 18, font: "Arial", italic: true, color: "666666" })] }));
  }
  return rows;
}

function addAllSections(children, data, p, width = CONTENT_W) {
  if (data.summary) {
    children.push(...sectionHeader("Professional Summary", p));
    children.push(new Paragraph({ spacing: { before: 80, after: 120 }, children: [new TextRun({ text: data.summary, size: 19, font: "Arial" })] }));
  }

  if (data.experience?.length) {
    children.push(...sectionHeader("Work Experience", p));
    data.experience.forEach(exp => children.push(...experienceBlock(exp, p, "bullets", width)));
  }

  if (data.projects?.length) {
    children.push(...sectionHeader("Key Projects", p));
    data.projects.forEach(proj => children.push(...projectBlock(proj, width)));
  }

  if (data.education?.length) {
    children.push(...sectionHeader("Education", p));
    data.education.forEach(edu => children.push(...educationBlock(edu, width)));
  }

  if (data.skills) {
    children.push(...sectionHeader("Skills & Expertise", p));
    const sk = data.skills;
    if (Array.isArray(sk.technical) && sk.technical.length) {
      children.push(new Paragraph({ spacing: { before: 40 }, children: [new TextRun({ text: "Technical Skills: ", bold: true, size: 19, font: "Arial" }), new TextRun({ text: sk.technical.join(", "), size: 19, font: "Arial" })] }));
    }
    if (Array.isArray(sk.tools) && sk.tools.length) {
      children.push(new Paragraph({ spacing: { before: 40 }, children: [new TextRun({ text: "Tools & Technologies: ", bold: true, size: 19, font: "Arial" }), new TextRun({ text: sk.tools.join(", "), size: 19, font: "Arial" })] }));
    }
    if (Array.isArray(sk.soft) && sk.soft.length) {
      children.push(new Paragraph({ spacing: { before: 40, after: 120 }, children: [new TextRun({ text: "Soft Skills: ", bold: true, size: 19, font: "Arial" }), new TextRun({ text: sk.soft.join(", "), size: 19, font: "Arial" })] }));
    }
  }

  if (Array.isArray(data.certifications) && data.certifications.length) {
    children.push(...sectionHeader("Certifications", p));
    data.certifications.forEach(cert => {
      children.push(new Paragraph({ numbering: { reference: "bullets", level: 0 }, spacing: { before: 20, after: 20 }, children: [new TextRun({ text: cert, size: 19, font: "Arial" })] }));
    });
  }
}

// ── Format Builders ─────────────────────────────────────────────────────────

function buildClassic(data, paletteName = "slate") {
  const p = PALETTES[paletteName] || PALETTES.slate;
  const contacts = [data.email, data.phone, data.location, data.linkedin].filter(Boolean).join("  |  ");
  const children = [];
  
  children.push(new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: safe(data.name, "Your Name").toUpperCase(), bold: true, size: 48, font: "Arial", color: p.primary })] }));
  children.push(new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: safe(data.tagline), size: 22, font: "Arial", color: p.accent })] }));
  children.push(new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 80, after: 120 }, children: [new TextRun({ text: contacts, size: 18, font: "Arial", color: "444444" })] }));
  children.push(hrParagraph("000000", 14));

  addAllSections(children, data, p, CONTENT_W);

  return new Document({
    numbering: { config: [{ reference: "bullets", levels: [{ level: 0, format: LevelFormat.BULLET, text: "\u2022", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 440, hanging: 240 } } } }] }] },
    sections: [{ properties: { page: { size: { width: PAGE_W, height: 16838 } } }, children }]
  });
}

function buildSpecialized(data, paletteName = "charcoal") {
  const p = PALETTES[paletteName] || PALETTES.charcoal;
  const children = [];
  
  const headerTbl = new Table({
    width: { size: PAGE_W, type: WidthType.DXA },
    borders: noBorder(),
    rows: [new TableRow({
      height: { value: 1800, rule: HeightRule.ATLEAST },
      children: [new TableCell({
        shading: { fill: p.primary, type: ShadingType.CLEAR },
        borders: noBorder(),
        verticalAlign: VerticalAlign.CENTER,
        margins: { left: 600, right: 600 },
        children: [
          new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: safe(data.name, "Your Name").toUpperCase(), bold: true, size: 52, font: "Arial", color: "FFFFFF" })] }),
          new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: safe(data.tagline), size: 24, font: "Arial", color: "CCCCCC" })] })
        ],
      })]
    })]
  });
  children.push(headerTbl);

  const contacts = [data.email, data.phone, data.location, data.linkedin].filter(Boolean).join("  •  ");
  children.push(new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 120, after: 120 }, children: [new TextRun({ text: contacts, size: 18, font: "Arial", color: "666666" })] }));

  // Wrap body in a nested table for unified margins
  const bodyChildren = [];
  addAllSections(bodyChildren, data, p, CONTENT_W);
  
  children.push(new Table({
    width: { size: PAGE_W, type: WidthType.DXA },
    borders: noBorder(),
    rows: [new TableRow({ children: [new TableCell({ borders: noBorder(), margins: { left: 800, right: 800 }, children: bodyChildren })] })]
  }));

  return new Document({
    numbering: { config: [{ reference: "bullets", levels: [{ level: 0, format: LevelFormat.BULLET, text: "\u2022", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 440, hanging: 240 } } } }] }] },
    sections: [{ properties: { page: { size: { width: PAGE_W, height: 16838 }, margin: { top: 0, bottom: 800, left: 0, right: 0 } } }, children }]
  });
}

function buildSidebar(data, paletteName = "navy", side = "left") {
  const p = PALETTES[paletteName] || PALETTES.navy;
  const sidebarW = 3600;
  const mainW = PAGE_W - sidebarW;
  
  // Sidebar Content
  const sidebarContent = [];
  sidebarContent.push(new Paragraph({ spacing: { before: 800, after: 200 }, children: [new TextRun({ text: safe(data.name), bold: true, size: 36, font: "Arial", color: "FFFFFF" })] }));
  
  const sideHdr = (text) => new Paragraph({ spacing: { before: 400, after: 100 }, children: [new TextRun({ text: text.toUpperCase(), bold: true, size: 18, font: "Arial", color: "FFFFFF" })] });
  const sideTxt = (text) => new Paragraph({ spacing: { before: 40, after: 40 }, children: [new TextRun({ text: text, size: 17, font: "Arial", color: "DDDDDD" })] });

  sideHdr("Contact");
  [data.email, data.phone, data.location].filter(Boolean).forEach(c => sidebarContent.push(sideTxt(`• ${c}`)));

  if (data.skills?.technical?.length) {
    sideHdr("Top Skills");
    data.skills.technical.slice(0, 8).forEach(s => sidebarContent.push(sideTxt(`• ${s}`)));
  }

  if (data.education?.length) {
    sideHdr("Education");
    data.education.forEach(edu => {
      sidebarContent.push(new Paragraph({ spacing: { before: 60 }, children: [new TextRun({ text: safe(edu.degree), bold: true, size: 17, font: "Arial", color: "FFFFFF" })] }));
      sidebarContent.push(sideTxt(safe(edu.institution)));
      sidebarContent.push(sideTxt(safe(edu.year)));
    });
  }

  // Main Content
  const mainContent = [];
  addAllSections(mainContent, data, p, mainW - 1000); // Inner width

  const sideCell = new TableCell({
    width: { size: sidebarW, type: WidthType.DXA },
    shading: { fill: p.primary, type: ShadingType.CLEAR },
    borders: noBorder(),
    margins: { left: 400, right: 400 },
    children: sidebarContent
  });

  const mainCell = new TableCell({
    width: { size: mainW, type: WidthType.DXA },
    borders: noBorder(),
    margins: { left: 600, right: 600, top: 400 },
    children: mainContent
  });

  const row = new TableRow({ children: side === "left" ? [sideCell, mainCell] : [mainCell, sideCell] });
  const table = new Table({ width: { size: PAGE_W, type: WidthType.DXA }, borders: noBorder(), rows: [row] });

  return new Document({
    numbering: { config: [{ reference: "bullets", levels: [{ level: 0, format: LevelFormat.BULLET, text: "\u2022", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 440, hanging: 240 } } } }] }] },
    sections: [{ properties: { page: { size: { width: PAGE_W, height: 16838 }, margin: { top: 0, bottom: 0, left: 0, right: 0 } } }, children: [table] }]
  });
}

function buildModern2Page(data, paletteName = "cvblue") {
  const p = PALETTES[paletteName] || PALETTES.cvblue;
  const children = [];
  
  const headerTbl = new Table({
    width: { size: CONTENT_W, type: WidthType.DXA },
    borders: noBorder(),
    rows: [new TableRow({ children: [
      new TableCell({
        width: { size: CONTENT_W * 0.6, type: WidthType.DXA },
        borders: noBorder(),
        children: [new Paragraph({ children: [new TextRun({ text: safe(data.name).toUpperCase(), bold: true, size: 48, font: "Arial", color: p.primary })] })]
      }),
      new TableCell({
        width: { size: CONTENT_W * 0.4, type: WidthType.DXA },
        borders: noBorder(),
        children: [new Paragraph({ alignment: AlignmentType.RIGHT, children: [new TextRun({ text: safe(data.tagline), size: 18, font: "Arial", color: p.accent })] })]
      })
    ]})]
  });
  children.push(headerTbl);
  children.push(hrParagraph(p.primary, 16));

  addAllSections(children, data, p, CONTENT_W);

  return new Document({
    numbering: { config: [{ reference: "bullets", levels: [{ level: 0, format: LevelFormat.BULLET, text: "\u2022", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 440, hanging: 240 } } } }] }] },
    sections: [{ properties: { page: { size: { width: PAGE_W, height: 16838 } } }, children }]
  });
}

// ── Master Orchestrator ──────────────────────────────────────────────────

const FORMATS = {
  classic_1page:  { builder: buildClassic,      palette: "slate"    },
  specialized:    { builder: buildSpecialized,  palette: "charcoal" },
  sidebar_left:   { builder: (data, p) => buildSidebar(data, p, "left"),  palette: "navy"   },
  sidebar_right:  { builder: (data, p) => buildSidebar(data, p, "right"), palette: "maroon" },
  modern_2page:   { builder: buildModern2Page,  palette: "cvblue"   },
};

async function generate(data, style, outDir) {
  if (!fs.existsSync(outDir)) fs.mkdirSync(outDir, { recursive: true });
  const cfg = FORMATS[style] || FORMATS.classic_1page;
  const doc = cfg.builder(data, cfg.palette);
  const buffer = await Packer.toBuffer(doc);
  const filePath = path.join(outDir, `cv_${style}.docx`);
  fs.writeFileSync(filePath, buffer);
  return filePath;
}

const dataPath = process.argv[2];
const style    = process.argv[3];
const outDir   = process.argv[4];

if (!dataPath || !style) process.exit(1);

try {
  const data = JSON.parse(fs.readFileSync(dataPath, "utf8"));
  generate(data, style, outDir)
    .then(f => console.log(f))
    .catch(e => {
      console.error("GENERATE ERROR:", e);
      process.exit(1);
    });
} catch (e) {
  console.error("PARSE/FILE ERROR:", e);
  process.exit(1);
}

