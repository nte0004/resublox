from dataclasses import dataclass
from typing import List, Tuple, Optional, Set
from src.core import FontSize, Spacing, SizeInfo, FontMetrics

@dataclass
class LineSpec:
    text: str
    size: SizeInfo
    isRequired: bool
    jobIndex: Optional[int] = None
    sectionIndex: Optional[int] = None
    pointIndex: Optional[int] = None
    lineType: str = "regular"

class LineGenerator:
    def __init__(self, fontMetrics: FontMetrics):
        self.fontMetrics = fontMetrics
    
    def combine(self, texts: List[str], separator: str) -> str:
        if not texts:
            return ""
        return separator.join(texts)
    
    def generateContactLines(self, contact: dict) -> List[LineSpec]:
        lines = []
        lines.append(LineSpec(
            text=contact['name'],
            size=FontSize.NAME,
            isRequired=True,
            lineType="header"
        ))
        lines.append(LineSpec(
            text=f"Email: {contact['email']} | Phone: {contact['phone']} | {contact['location']}",
            size=FontSize.REGULAR,
            isRequired=True,
            lineType="contact"
        ))
        lines.append(LineSpec(
            text=f"Github: {contact['github']} | Website: {contact['website']}",
            size=FontSize.REGULAR,
            isRequired=True,
            lineType="contact"
        ))
        return lines
    
    def generateSkillsHeader(self, skills: dict) -> List[LineSpec]:
        return [
            LineSpec(text="", size=Spacing.GAP, isRequired=True, lineType="gap"),
            LineSpec(text=skills['title'], size=FontSize.TITLE, isRequired=True, lineType="header")
        ]
    
    def generateSkillsContent(self, skillItems: List[str]) -> LineSpec:
        skillsText = self.combine(skillItems, ', ')
        return LineSpec(
            text=skillsText,
            size=FontSize.REGULAR,
            isRequired=False,
            lineType="skills"
        )
    
    def generateExperienceHeader(self, experience: dict) -> List[LineSpec]:
        return [
            LineSpec(text="", size=Spacing.GAP, isRequired=True, lineType="gap"),
            LineSpec(text=experience['title'], size=FontSize.TITLE, isRequired=True, lineType="header")
        ]
    
    def generateJobHeader(self, job: dict, jobIndex: int) -> List[LineSpec]:
        lines = []
        
        if jobIndex > 0:
            lines.append(LineSpec(
                text="",
                size=Spacing.GAP,
                isRequired=False,
                jobIndex=jobIndex,
                lineType="gap"
            ))
        else:
            lines.append(LineSpec(
                text="",
                size=Spacing.GAP,
                isRequired=False,
                jobIndex=jobIndex,
                lineType="gap"
            ))
        
        fromDate = job.get('from', job.get('from_date', ''))
        toDate = job.get('to', job.get('to_date', ''))
        
        lines.extend([
            LineSpec(text=job['role'], size=FontSize.REGULAR, isRequired=False, jobIndex=jobIndex, lineType="jobHeader"),
            LineSpec(text=job['company'], size=FontSize.REGULAR, isRequired=False, jobIndex=jobIndex, lineType="jobHeader"),
            LineSpec(text=job['location'], size=FontSize.REGULAR, isRequired=False, jobIndex=jobIndex, lineType="jobHeader"),
            LineSpec(text=self.combine([fromDate, toDate], ' — '), size=FontSize.REGULAR, isRequired=False, jobIndex=jobIndex, lineType="jobHeader"),
            LineSpec(text="", size=Spacing.GAP_SMALL, isRequired=False, jobIndex=jobIndex, lineType="gap")
        ])
        
        return lines
    
    def generateSectionHeader(self, section: dict, jobIndex: int, sectionIndex: int, isFirstInJob: bool) -> List[LineSpec]:
        lines = []
        
        if not isFirstInJob:
            lines.append(LineSpec(
                text="",
                size=Spacing.GAP_SMALL,
                isRequired=False,
                jobIndex=jobIndex,
                sectionIndex=sectionIndex,
                lineType="gap"
            ))
        
        lines.append(LineSpec(
            text=section['title'],
            size=FontSize.SUBTITLE,
            isRequired=False,
            jobIndex=jobIndex,
            sectionIndex=sectionIndex,
            lineType="sectionHeader"
        ))
        
        return lines
    
    def generatePointLine(self, point: str, jobIndex: int, sectionIndex: int, pointIndex: int) -> LineSpec:
        return LineSpec(
            text=f"- {point}",
            size=FontSize.REGULAR,
            isRequired=False,
            jobIndex=jobIndex,
            sectionIndex=sectionIndex,
            pointIndex=pointIndex,
            lineType="point"
        )
    
    def generateKeywordsLine(self, keywords: List[str], jobIndex: int, sectionIndex: int) -> LineSpec:
        keywordsText = self.combine(keywords, ', ')
        return LineSpec(
            text=f"Technologies Used: {keywordsText}",
            size=FontSize.REGULAR,
            isRequired=False,
            jobIndex=jobIndex,
            sectionIndex=sectionIndex,
            lineType="keywords"
        )
    
    def generateLinksLine(self, links: List[dict], jobIndex: int, sectionIndex: int) -> LineSpec:
        linkTexts = [f"{link['descriptor']}: {link['link']}" for link in links]
        linksText = self.combine(linkTexts, ' | ')
        return LineSpec(
            text=linksText,
            size=FontSize.REGULAR,
            isRequired=False,
            jobIndex=jobIndex,
            sectionIndex=sectionIndex,
            lineType="links"
        )
    
    def generateEducationLines(self, education: dict) -> List[LineSpec]:
        lines = []
        
        lines.append(LineSpec(text="", size=Spacing.GAP, isRequired=True, lineType="gap"))
        lines.append(LineSpec(text=education['title'], size=FontSize.TITLE, isRequired=True, lineType="header"))
        
        degree = f"{education['degree']} in {education['major']}"
        lines.append(LineSpec(text=degree, size=FontSize.REGULAR, isRequired=True, lineType="education"))
        
        conc = education.get('concentration', None)
        if conc:
            lines.append(LineSpec(
                text=f"Concentration in {conc}",
                size=FontSize.REGULAR,
                isRequired=True,
                lineType="education"
            ))
        
        school = f"{education['school']}, {education['location']}"
        lines.append(LineSpec(text=school, size=FontSize.REGULAR, isRequired=True, lineType="education"))
        
        grad = education.get('graduation', None)
        if grad:
            if grad['hasGraduated']:
                gradLine = f"Graduated: {grad['on']}"
            else:
                gradLine = f"Expected Graduation: {grad['on']}"
            lines.append(LineSpec(text=gradLine, size=FontSize.REGULAR, isRequired=True, lineType="education"))
        
        lines.append(LineSpec(text=f"GPA: {education['gpa']}", size=FontSize.REGULAR, isRequired=True, lineType="education"))
        
        honorsList = self.combine(education['honors'], ', ')
        lines.append(LineSpec(text=f"Honors: {honorsList}", size=FontSize.REGULAR, isRequired=True, lineType="education"))
        
        courseList = self.combine(education['courses'], ', ')
        lines.append(LineSpec(text=f"Relevant Courses: {courseList}", size=FontSize.REGULAR, isRequired=True, lineType="education"))
        
        return lines
    
    def calculateHeight(self, lineSpec: LineSpec) -> int:
        return self.fontMetrics.getHeight(lineSpec.text, lineSpec.size)
    
    def generateAllRequiredLines(self, content: dict) -> List[LineSpec]:
        lines = []
        lines.extend(self.generateContactLines(content['contact']))
        lines.extend(self.generateSkillsHeader(content['skills']))
        lines.extend(self.generateExperienceHeader(content['experience']))
        lines.extend(self.generateEducationLines(content['education']))
        return lines
    
    def calculateTotalHeight(self, lines: List[LineSpec]) -> int:
        return sum(self.calculateHeight(line) for line in lines)
