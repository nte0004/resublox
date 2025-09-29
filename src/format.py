from docx import Document
from docx.shared import Inches, Pt
import tempfile
import os
import platform
import subprocess
from src.core import FontSize, Spacing, FONT

PAGE_WIDTH_INCHES = 8.5
PAGE_HEIGHT_INCHES = 11
MARGIN_INCHES = [1, 1, 1, 1]
LINE_HEIGHT = 1.15
MAX_PAGES = 1

def combine(texts, seperator):
    line = ""
    for text in texts[:-1]:
        line += text
        line += seperator
    line += texts[-1];

    return line

def generateLines(content):
    lines = []
    
    # Contact Info
    c = content['contact']
    lines.append((c['name'], FontSize.NAME))

    line = f"Email: {c['email']} | Phone: {c['phone']} | {c['location']}"
    lines.append((line, FontSize.REGULAR))

    line = f"Github: {c['github']} | Website: {c['website']}"
    lines.append((line, FontSize.REGULAR))

    # Gap
    lines.append(('', Spacing.GAP))

    # Skills
    s = content['skills']
    lines.append((s['title'], FontSize.TITLE))

    skills = combine(s['list'], ', ')
    lines.append((skills, FontSize.REGULAR))
    
    # Gap
    lines.append(('', Spacing.GAP))

    # Experience
    e = content['experience']
    lines.append((e['title'], FontSize.TITLE))
    for i, job in enumerate(e['jobs']):
        lines.append((job['role'], FontSize.REGULAR))
        lines.append((job['company'], FontSize.REGULAR))
        lines.append((job['location'], FontSize.REGULAR))

        timeRange = combine([job['from_date'], job['to_date']], ' \u2014 ') # Em Dash
        lines.append((timeRange, FontSize.REGULAR))

        lines.append(('', Spacing.GAP_SMALL))

        sections = job['sections']
        lastSec = len(sections) - 1
        for idx, sec in enumerate(job['sections']):
            lines.append((sec['title'], FontSize.SUBTITLE))
            
            for point in sec['points']:
                lines.append((f"- {point}", FontSize.REGULAR))

            if "keywords" in sec:
                keywords = combine(sec['keywords'], ', ')
                lines.append((f"- Technologies: {keywords}", FontSize.REGULAR))

            if "links" in sec and sec['links'] is not None:
                links = []
                for link in sec['links']:
                    links.append(f"{link['descriptor']}: {link['link']}")
                linkLine = combine(links, ' | ');
                lines.append((linkLine, FontSize.REGULAR))
            
            if idx != lastSec:
                lines.append(('', Spacing.GAP_SMALL))
        
        if i != len(e['jobs']) - 1:
            lines.append(('', Spacing.GAP))

    # Gap
    lines.append(('', Spacing.GAP))
    
    # Education
    e = content['education']
    lines.append((e['title'], FontSize.TITLE))
    
    degree = f"{e['degree']} in {e['major']}"
    lines.append((degree, FontSize.REGULAR))

    conc = e.get('concentration', None)
    if conc:
        lines.append((f"Concentration in {conc}", FontSize.REGULAR))

    school = f"{e['school']}, {e['location']}"
    lines.append((school, FontSize.REGULAR))

    grad = e.get('graduation', None)
    if grad:
        print(grad)
        if grad['hasGraduated']:
            gradLine = f"Graduated: {grad['on']}"
        else:
            gradLine = f"Expected Graduation: {grad['on']}"
        lines.append((gradLine, FontSize.REGULAR))

    gpa = f"GPA: {e['gpa']}"
    lines.append((gpa, FontSize.REGULAR))

    honorsList = combine(e['honors'], ', ')
    honors = f"Honors: {honorsList}"
    lines.append((honors, FontSize.REGULAR))

    courseList = combine(e['courses'], ', ')
    courses = f"Relevant Courses: {courseList}"
    lines.append((courses, FontSize.REGULAR))

    return lines

def createDocx(lines):
    doc = Document()

    section = doc.sections[0]
    section.page_width = Inches(PAGE_WIDTH_INCHES)
    section.page_height = Inches(PAGE_HEIGHT_INCHES)
    section.top_margin = Inches(MARGIN_INCHES[0])
    section.right_margin = Inches(MARGIN_INCHES[1])
    section.bottom_margin = Inches(MARGIN_INCHES[2])
    section.left_margin = Inches(MARGIN_INCHES[3])

    for text, size in lines:
        if text:
            insertion = doc.add_paragraph()
            run = insertion.add_run(text)
            run.font.name = FONT.name
            run.font.size = Pt(size.size)

            insertion.paragraph_format.space_after = Pt(0)
            insertion.paragraph_format.space_before = Pt(0)
        else:
            insertion = doc.add_paragraph()
            insertion.paragraph_format.space_after = Pt(size.size)
            insertion.paragraph_format.space_before = Pt(0)
            insertion.paragraph_format.line_spacing = Pt(0)

    return doc

def docxToPdf(doc):
    with tempfile.NamedTemporaryFile(suffix='.docx', delete=False) as tmpFile:
        doc.save(tmpFile.name)
        tempPath = tmpFile.name

    system = platform.system()
    if system == "Darwin":
        LIBREOFFICE_PATH='/Applications/LibreOffice.app/Contents/MacOS/soffice'
    elif system == "Linux":
        LIBREOFFICE_PATH='libreoffice'
    else:
        print("Error: Windows docx to pdf conversion not implemented.")
        exit(1)

    subprocess.run([
        LIBREOFFICE_PATH, '--headless', '--convert-to', 'pdf',
        '--outdir', os.path.dirname(tempPath), tempPath
    ])

    return tempPath

def openPdf(path):
    pdfPath = path.replace('.docx', '.pdf')
    subprocess.run(['open', pdfPath])

def output(content):
    lines = generateLines(content)
    doc = createDocx(lines)
    path = docxToPdf(doc)
    openPdf(path)


