import yaml

TEMPLATE_PATH='template.example.yaml'

with open(TEMPLATE_PATH, 'r') as file:
    content = yaml.safe_load(file)

from docx import Document
from docx.shared import Inches, Pt

class FontSize:
    NAME = 13
    REGULAR = 10
    TITLE = 12
    SUBTITLE = 11

class Spacing:
    GAP = 6
    GAP_SMALL = 3

doc = Document()

# Page Setup
def setupPage():
    section = doc.sections[0]
    section.page_width = Inches(8.5)
    section.page_height = Inches(11)
    section.top_margin = Inches(1)
    section.right_margin = Inches(1)
    section.bottom_margin = Inches(1)
    section.left_margin = Inches(1)

def insert(text, size = FontSize.REGULAR):
    insertion = doc.add_paragraph()
    run = insertion.add_run(text)
    run.font.size = Pt(size)

    insertion.paragraph_format.space_after = Pt(0)
    insertion.paragraph_format.space_before = Pt(0)

def insertGap(space=Spacing.GAP):
    insertion = doc.add_paragraph()
    insertion.paragraph_format.space_after = Pt(space)
    insertion.paragraph_format.space_before = Pt(0)
    insertion.paragraph_format.line_spacing = Pt(0)

def combine(texts, seperator):
    line = ""
    for text in texts[:-1]:
        line += text
        line += seperator
    line += texts[-1];

    return line

def addContact():
    c = content['contact']
    insert(c['name'], FontSize.NAME)

    line = f"Email: {c['email']} | Phone: {c['phone']} | {c['location']}"
    insert(line)

    line = f"Github: {c['github']} | Website: {c['website']}"
    insert(line)


def addSkills():
    s = content['skills']
    insert(s['title'], FontSize.TITLE)
    skills = combine(s['list'], ', ')
    insert(skills)

def addSection(section):
    insert(section['title'], FontSize.SUBTITLE)
    
    for point in section['points']:
        insert(f"- {point}")

    keywords = combine(section['keywords'], ', ')
    insert(f"- Technologies: {keywords}")

    if "links" in section:
        links = []
        for link in section['links']:
            links.append(f"{link['descriptor']}: {link['link']}")
        linkLine = combine(links, ' | ');
        insert(linkLine)

def addExperience():
    e = content['experience']
    insert(e['title'], FontSize.TITLE)
    for job in e['jobs']:
        insert(job['role'])
        insert(job['company'])
        insert(job['location'])

        timeRange = combine([job['from'], job['to']], ' \u2014 ') # Em Dash
        insert(timeRange)

        insertGap(Spacing.GAP_SMALL)

        for sec in job['sections'][:-1]:
            addSection(sec)
            insertGap(Spacing.GAP_SMALL)

        addSection(job['sections'][-1])

def addEducation():
    e = content['education']
    insert(e['title'], FontSize.TITLE)
    
    degree = f"{e['degree']} in {e['major']}"
    insert(degree)

    conc = f"Concentration in {e['concentration']}"
    insert(conc)

    school = f"{e['school']}, {e['location']}"
    insert(school)

    grad = f"Graduated: {e['graduated']}"
    insert(grad)

    gpa = f"GPA: {e['gpa']}"
    insert(gpa)

    honorsList = combine(e['honors'], ', ')
    honors = f"Honors: {honorsList}"
    insert(honors)

setupPage()
addContact()

insertGap()

addSkills()

insertGap()

addExperience()

insertGap()

addEducation()

import tempfile
import os
import platform
import subprocess

with tempfile.NamedTemporaryFile(suffix='.docx', delete=False) as tmp_file:
    doc.save(tmp_file.name)
    temp_path = tmp_file.name

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
    '--outdir', os.path.dirname(temp_path), temp_path
])

temp_pdf_path = temp_path.replace('.docx', '.pdf')
subprocess.run(['open', temp_pdf_path])
