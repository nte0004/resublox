from docx import Document
from docx.shared import Inches, Pt
import tempfile
import os
import platform
import subprocess
from src.core import FontMetrics, PAGE_WIDTH_INCHES, PAGE_HEIGHT_INCHES, MARGIN_INCHES, FONT
from src.lineGenerator import LineGenerator

FONT_METRICS = FontMetrics()
LINE_GENERATOR = LineGenerator(FONT_METRICS)

def generateLines(content):
    lines = []
    
    lines.extend(LINE_GENERATOR.generateContactLines(content['contact']))
    lines.extend(LINE_GENERATOR.generateSkillsHeader(content['skills']))
    
    skillsContent = LINE_GENERATOR.generateSkillsContent(content['skills']['list'])
    lines.append(skillsContent)
    
    lines.extend(LINE_GENERATOR.generateExperienceHeader(content['experience']))
    
    for jobIdx, job in enumerate(content['experience']['jobs']):
        lines.extend(LINE_GENERATOR.generateJobHeader(job, jobIdx))
        
        for sectionIdx, section in enumerate(job['sections']):
            isFirstInJob = (sectionIdx == 0)
            lines.extend(LINE_GENERATOR.generateSectionHeader(section, jobIdx, sectionIdx, isFirstInJob))
            
            for pointIdx, point in enumerate(section['points']):
                lines.append(LINE_GENERATOR.generatePointLine(point, jobIdx, sectionIdx, pointIdx))
            
            if 'keywords' in section and section['keywords']:
                lines.append(LINE_GENERATOR.generateKeywordsLine(section['keywords'], jobIdx, sectionIdx))
            
            if 'links' in section and section['links'] is not None:
                lines.append(LINE_GENERATOR.generateLinksLine(section['links'], jobIdx, sectionIdx))
    
    lines.extend(LINE_GENERATOR.generateEducationLines(content['education']))

    if 'courses' in content['education'] and content['education']['courses']:
            coursesLine = LINE_GENERATOR.generateCoursesLine(content['education']['courses'])
            lines.append(coursesLine)
        
    return lines

def createDocx(lineSpecs):
    doc = Document()

    section = doc.sections[0]
    section.page_width = Inches(PAGE_WIDTH_INCHES)
    section.page_height = Inches(PAGE_HEIGHT_INCHES)
    section.top_margin = Inches(MARGIN_INCHES[0])
    section.right_margin = Inches(MARGIN_INCHES[1])
    section.bottom_margin = Inches(MARGIN_INCHES[2])
    section.left_margin = Inches(MARGIN_INCHES[3])

    for lineSpec in lineSpecs:
        if lineSpec.text:
            insertion = doc.add_paragraph()
            run = insertion.add_run(lineSpec.text)
            run.font.name = FONT.name
            run.font.size = Pt(lineSpec.size.size)

            insertion.paragraph_format.space_after = Pt(0)
            insertion.paragraph_format.space_before = Pt(0)
        else:
            insertion = doc.add_paragraph()
            insertion.paragraph_format.space_after = Pt(lineSpec.size.size)
            insertion.paragraph_format.space_before = Pt(0)
            insertion.paragraph_format.line_spacing = Pt(0)

    return doc

def docxToPdf(tempPath):
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

def output(content, editableFlag = False):
    lineSpecs = generateLines(content)
    doc = createDocx(lineSpecs)

    with tempfile.NamedTemporaryFile(suffix='.docx', delete=False) as tmpFile:
        doc.save(tmpFile.name)
        tempPath = tmpFile.name
    
    if (editableFlag):
        # Just open as docx, allows by-hand changes
        subprocess.run(['open', tempPath])
    else:
        docxToPdf(tempPath)
        pdfPath = tempPath.replace('.docx', '.pdf')
        subprocess.run(['open', pdfPath])
