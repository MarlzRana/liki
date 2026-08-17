---
name: process-pdf
description: Process a PDF into the wiki, or do anything else with PDF files. Use when an inbox item is a PDF — especially scans or photos of the owner's handwritten notes, which must be transcribed with their hand-drawn diagrams cropped out and embedded. Also covers reading or extracting text/tables, merging/splitting/rotating, watermarks, creating PDFs, filling forms, encrypting/decrypting, extracting images, and OCR of scanned pages. If the user mentions a .pdf file or asks to produce one, use this skill.
---

# Processing PDFs

PDFs arrive in this vault the same way notes do — dropped into `inbox/` (see
`<inbox_artifacts>` in AGENTS.md). Two kinds show up and they need completely
different handling:

- **Handwritten notes** — the owner's own pages, photographed or scanned. No text
  layer. **Transcribe them, and crop the hand-drawn diagrams into the wiki page.**
- **Born-digital documents** — papers, specs, statements, guides. Real text layer.
  Extract and treat as a *source*, under the same to-do-vs-source doctrine as a
  captured link (`<captured_links>` in AGENTS.md).

Everything below the `---` rule is the generic upstream PDF reference. Read this
part first — it governs how PDFs become wiki pages.

## 1. Triage: is there a text layer?

Never assume. One command tells you which kind of PDF you have:

```bash
uv run --quiet --with pymupdf python -c "
import pymupdf, sys
doc = pymupdf.open(sys.argv[1])
for i, page in enumerate(doc, 1):
    text = page.get_text().strip()
    print(f'p{i}: {len(text):>5} chars  {page.rect.width:.0f}x{page.rect.height:.0f}pt  {len(page.get_images())} embedded image(s)')
" "inbox/some-file.pdf"
```

- **Hundreds+ of chars per page** → born-digital. Go to §4.
- **~0 chars and one big embedded image** → a scan or photo. Go to §2.
- **Mixed** → handle per page; a printed handout with handwritten margin notes is
  both, and the margin notes are usually the part the owner cares about.

## 2. Handwritten notes → transcribe

**Read the pages as images and transcribe what you see. Do not reach for OCR.**
`tesseract` is installed but it is unreliable on cursive and near-useless on
sketches, arrows, and margin scrawl; the vision path is strictly better.

The `Read` tool opens a PDF directly — pass `pages` (max 20 per request):

```
Read(file_path="inbox/lecture-notes.pdf", pages="1-6")
```

If that fails, or you need higher resolution for cramped handwriting, render and
read the PNGs instead. **Render to `/tmp`, never into `assets/`** — scratch page
renders must not end up in the vault:

```bash
mkdir -p /tmp/pdf-pages && uv run --quiet --with pymupdf python -c "
import pymupdf
doc = pymupdf.open('inbox/lecture-notes.pdf')
for i, page in enumerate(doc, 1):
    page.get_pixmap(dpi=200).save(f'/tmp/pdf-pages/page-{i}.png')
print(f'rendered {doc.page_count} pages')
"
```

Then transcribe:

- **These are the owner's own words**, so `<voice_and_editorial_rules>` applies as
  written: messy, fragmentary handwriting gets synthesised and restructured for
  clarity; already-structured pages keep their phrasing; anything personal or
  emotional keeps its voice with only surface fixes.
- Handwriting has its own artifact class, the direct analogue of speech-to-text
  garbling: dropped words, abbreviations (`w/`, `->`, `∴`, `KV$` for KV cache),
  arrows standing in for "leads to", and boxes/circles marking emphasis. Expand
  them into prose silently.
- **Never guess at a word you cannot read.** Write `[illegible]` and flag it in the
  session report. Inventing a plausible term puts a claim the owner never made
  into their own voice — the one failure mode that matters most here.
- Reproduce the *structure* the page implies: a bulleted brain-dump stays bullets,
  a two-column comparison becomes a table, a numbered derivation stays ordered.

## 3. Hand-drawn diagrams → crop into the note

A sketch on the page is content, not decoration. Crop it out and embed it rather
than describing it in prose.

**Locate it.** Read the rendered page and estimate the diagram's bounding box in
pixels. Note that when `Read` downscales a large image it tells you the scale
factor ("multiply coordinates by 1.17") — apply that first to get true pixels.

**Convert pixels to points.** `pymupdf` clips in PDF points (72 per inch), so from
a render at `dpi`: `points = pixels × 72 / dpi`. At the 200 dpi above, divide by
2.78.

**Crop at 300 dpi** — higher than you'd use for reading, because pencil and biro
lines thin out badly on a screen:

```bash
uv run --quiet --with pymupdf python -c "
import pymupdf
page = pymupdf.open('inbox/lecture-notes.pdf')[2]   # 0-indexed: page 3
clip = pymupdf.Rect(60, 210, 540, 470)              # x0, y0, x1, y1 in points
page.get_pixmap(dpi=300, clip=clip).save('assets/kv-cache-eviction-sketch.png')
"
```

**Verify by reading the crop back.** A wrong clip fails silently — it writes a
perfectly valid PNG of half a diagram, or of blank paper. Look at it, adjust, and
only then embed. Leave a little whitespace margin; a crop shaved to the ink looks
cramped in Obsidian.

Then follow the normal asset rules (`<assets>` in AGENTS.md): descriptive
kebab-case name saying what the diagram *is*, private `assets/` by default,
promoted to `assets/public/` only when the note embedding it lives under
`wiki/Technical/`, embedded with an explicit vault-root path:

```markdown
![[assets/public/kv-cache-eviction-sketch.png]]
```

Place each diagram in the transcription where it sat in the notes, and make the
surrounding prose refer to it. Delete the `/tmp` renders when you're done.

## 4. Born-digital documents

Extract the text (`page.get_text()`, or `pdftotext file.pdf -` for a quick dump;
use `pdfplumber` for real tables — see the reference below), then route it exactly
like a captured link:

- **The owner has written their own notes around it** → it's a **source**. Their
  notes are the substance and their voice governs; use the PDF to disambiguate and
  sanity-check, not to pad the page. Keep the attribution footer.
- **A bare drop with no notes of their own** → **ask before writing a page.**
  Unlike a URL, a PDF gives no cue as to whether it's been read, so don't guess: it
  either belongs on `wiki/Other/Reading List.md` with a substantive descriptor, or
  it's a source they've already read. Skim it enough to describe it accurately
  either way.
- **A form, statement, or reference table** (ISA comparison, payslip, medical
  letter) is usually not a prose page at all — pull the figures into a table on the
  relevant page and link the original.

## 5. Where the PDF itself ends up

- **Archive the original to `inbox/processed/`** (private) — the default, same as
  any processed note.
- **Also preserve it in `assets/` and link it from the page when it's a durable
  reference** — a paper, spec, or statement worth reopening later. Give it a
  descriptive kebab-case name and link (don't embed) it in the footer, since
  `![[…pdf]]` renders a full inline PDF viewer in Obsidian:

  ```markdown
  ---
  Source: Leviathan et al., "Fast Inference from Transformers via Speculative
  Decoding" — [[assets/public/speculative-decoding-paper.pdf]]
  ```

- `assets/public/` is committed to git, so a PDF may only go there if a
  `wiki/Technical/` note references it. **PDFs carry personal data far more often
  than images do** — statements, payslips, letters, anything with a name and
  address on it. Those stay in private `assets/`, never `assets/public/`; if the
  page discussing one is itself sensitive, use the `.local.md` convention.
- **A transcribed handwritten scan usually needs no copy in `assets/`** — the
  transcription plus cropped diagrams *is* the durable record. Archive the scan and
  keep the crops.

## Environment notes

- **`uv run --with <pkg>`** is the way to get Python libraries here. The system
  Python has neither `pypdf` nor `PIL`, and nothing should be installed into it.
  `pymupdf` alone covers rendering, cropping, text, and images with no system
  dependencies, so prefer it over the `pdf2image`-based scripts in `scripts/`,
  which additionally need poppler.
- **poppler** (`pdftotext`, `pdftoppm`) and **tesseract** are installed via brew.
  `Read`'s PDF support shells out to `pdftoppm`, so on a fresh machine
  `brew install poppler` is what makes reading a PDF work at all.
- **Provenance:** this skill is a vendored copy of the `pdf` skill from
  [anthropics/skills](https://github.com/anthropics/skills), renamed and extended
  with the wiki-specific guidance above. The `skills` CLI records provenance only
  in a root `skills-lock.json`, never inside the skill directory, and that file was
  removed — which is what protects the additions above. For project scope,
  `skills update` reinstalls every lock entry unconditionally: `rm -rf` on the skill
  directory then a fresh copy from upstream, with no diff and no prompt. Being
  absent from the lock is the only thing that hides a skill from it; the rename
  alone would not have (that yields a pristine duplicate). Pull upstream changes in
  by hand, and if a future `npx skills add … --skill pdf` drops one in as
  `.agents/skills/pdf/`, merge and delete the duplicate.

---

# PDF Processing Guide (generic reference)

## Overview

This guide covers essential PDF processing operations using Python libraries and command-line tools. For advanced features, JavaScript libraries, and detailed examples, see `reference.md`. If you need to fill out a PDF form, read `forms.md` and follow its instructions.

## Quick Start

```python
from pypdf import PdfReader, PdfWriter

# Read a PDF
reader = PdfReader("document.pdf")
print(f"Pages: {len(reader.pages)}")

# Extract text
text = ""
for page in reader.pages:
    text += page.extract_text()
```

## Python Libraries

### pypdf - Basic Operations

#### Merge PDFs

```python
from pypdf import PdfWriter, PdfReader

writer = PdfWriter()
for pdf_file in ["doc1.pdf", "doc2.pdf", "doc3.pdf"]:
    reader = PdfReader(pdf_file)
    for page in reader.pages:
        writer.add_page(page)

with open("merged.pdf", "wb") as output:
    writer.write(output)
```

#### Split PDF

```python
reader = PdfReader("input.pdf")
for i, page in enumerate(reader.pages):
    writer = PdfWriter()
    writer.add_page(page)
    with open(f"page_{i+1}.pdf", "wb") as output:
        writer.write(output)
```

#### Extract Metadata

```python
reader = PdfReader("document.pdf")
meta = reader.metadata
print(f"Title: {meta.title}")
print(f"Author: {meta.author}")
print(f"Subject: {meta.subject}")
print(f"Creator: {meta.creator}")
```

#### Rotate Pages

```python
reader = PdfReader("input.pdf")
writer = PdfWriter()

page = reader.pages[0]
page.rotate(90)  # Rotate 90 degrees clockwise
writer.add_page(page)

with open("rotated.pdf", "wb") as output:
    writer.write(output)
```

### pdfplumber - Text and Table Extraction

#### Extract Text with Layout

```python
import pdfplumber

with pdfplumber.open("document.pdf") as pdf:
    for page in pdf.pages:
        text = page.extract_text()
        print(text)
```

#### Extract Tables

```python
with pdfplumber.open("document.pdf") as pdf:
    for i, page in enumerate(pdf.pages):
        tables = page.extract_tables()
        for j, table in enumerate(tables):
            print(f"Table {j+1} on page {i+1}:")
            for row in table:
                print(row)
```

#### Advanced Table Extraction

```python
import pandas as pd

with pdfplumber.open("document.pdf") as pdf:
    all_tables = []
    for page in pdf.pages:
        tables = page.extract_tables()
        for table in tables:
            if table:  # Check if table is not empty
                df = pd.DataFrame(table[1:], columns=table[0])
                all_tables.append(df)

# Combine all tables
if all_tables:
    combined_df = pd.concat(all_tables, ignore_index=True)
    combined_df.to_excel("extracted_tables.xlsx", index=False)
```

### reportlab - Create PDFs

#### Basic PDF Creation

```python
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

c = canvas.Canvas("hello.pdf", pagesize=letter)
width, height = letter

# Add text
c.drawString(100, height - 100, "Hello World!")
c.drawString(100, height - 120, "This is a PDF created with reportlab")

# Add a line
c.line(100, height - 140, 400, height - 140)

# Save
c.save()
```

#### Create PDF with Multiple Pages

```python
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet

doc = SimpleDocTemplate("report.pdf", pagesize=letter)
styles = getSampleStyleSheet()
story = []

# Add content
title = Paragraph("Report Title", styles['Title'])
story.append(title)
story.append(Spacer(1, 12))

body = Paragraph("This is the body of the report. " * 20, styles['Normal'])
story.append(body)
story.append(PageBreak())

# Page 2
story.append(Paragraph("Page 2", styles['Heading1']))
story.append(Paragraph("Content for page 2", styles['Normal']))

# Build PDF
doc.build(story)
```

#### Subscripts and Superscripts

**IMPORTANT**: Never use Unicode subscript/superscript characters (₀₁₂₃₄₅₆₇₈₉, ⁰¹²³⁴⁵⁶⁷⁸⁹) in ReportLab PDFs. The built-in fonts do not include these glyphs, causing them to render as solid black boxes.

Instead, use ReportLab's XML markup tags in Paragraph objects:

```python
from reportlab.platypus import Paragraph
from reportlab.lib.styles import getSampleStyleSheet

styles = getSampleStyleSheet()

# Subscripts: use <sub> tag
chemical = Paragraph("H<sub>2</sub>O", styles['Normal'])

# Superscripts: use <super> tag
squared = Paragraph("x<super>2</super> + y<super>2</super>", styles['Normal'])
```

For canvas-drawn text (not Paragraph objects), manually adjust font the size and position rather than using Unicode subscripts/superscripts.

## Command-Line Tools

### pdftotext (poppler-utils)

```bash
# Extract text
pdftotext input.pdf output.txt

# Extract text preserving layout
pdftotext -layout input.pdf output.txt

# Extract specific pages
pdftotext -f 1 -l 5 input.pdf output.txt  # Pages 1-5
```

### qpdf

```bash
# Merge PDFs
qpdf --empty --pages file1.pdf file2.pdf -- merged.pdf

# Split pages
qpdf input.pdf --pages . 1-5 -- pages1-5.pdf
qpdf input.pdf --pages . 6-10 -- pages6-10.pdf

# Rotate pages
qpdf input.pdf output.pdf --rotate=+90:1  # Rotate page 1 by 90 degrees

# Remove password
qpdf --password=mypassword --decrypt encrypted.pdf decrypted.pdf
```

### pdftk (if available)

```bash
# Merge
pdftk file1.pdf file2.pdf cat output merged.pdf

# Split
pdftk input.pdf burst

# Rotate
pdftk input.pdf rotate 1east output rotated.pdf
```

## Common Tasks

### Extract Text from Scanned PDFs

```python
# Requires: pip install pytesseract pdf2image
import pytesseract
from pdf2image import convert_from_path

# Convert PDF to images
images = convert_from_path('scanned.pdf')

# OCR each page
text = ""
for i, image in enumerate(images):
    text += f"Page {i+1}:\n"
    text += pytesseract.image_to_string(image)
    text += "\n\n"

print(text)
```

### Add Watermark

```python
from pypdf import PdfReader, PdfWriter

# Create watermark (or load existing)
watermark = PdfReader("watermark.pdf").pages[0]

# Apply to all pages
reader = PdfReader("document.pdf")
writer = PdfWriter()

for page in reader.pages:
    page.merge_page(watermark)
    writer.add_page(page)

with open("watermarked.pdf", "wb") as output:
    writer.write(output)
```

### Extract Images

```bash
# Using pdfimages (poppler-utils)
pdfimages -j input.pdf output_prefix

# This extracts all images as output_prefix-000.jpg, output_prefix-001.jpg, etc.
```

### Password Protection

```python
from pypdf import PdfReader, PdfWriter

reader = PdfReader("input.pdf")
writer = PdfWriter()

for page in reader.pages:
    writer.add_page(page)

# Add password
writer.encrypt("userpassword", "ownerpassword")

with open("encrypted.pdf", "wb") as output:
    writer.write(output)
```

## Quick Reference

| Task               | Best Tool                       | Command/Code               |
| ------------------ | ------------------------------- | -------------------------- |
| Merge PDFs         | pypdf                           | `writer.add_page(page)`    |
| Split PDFs         | pypdf                           | One page per file          |
| Extract text       | pdfplumber                      | `page.extract_text()`      |
| Extract tables     | pdfplumber                      | `page.extract_tables()`    |
| Create PDFs        | reportlab                       | Canvas or Platypus         |
| Command line merge | qpdf                            | `qpdf --empty --pages ...` |
| OCR scanned PDFs   | pytesseract                     | Convert to image first     |
| Fill PDF forms     | pdf-lib or pypdf (see `forms.md`) | See `forms.md`             |

## Next Steps

- For advanced pypdfium2 usage, see `reference.md`
- For JavaScript libraries (pdf-lib), see `reference.md`
- If you need to fill out a PDF form, follow the instructions in `forms.md`
- For troubleshooting guides, see `reference.md`
