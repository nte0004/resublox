from dataclasses import dataclass
from typing import List, Tuple, Optional, Set, Any
from src.core import FontSize, Spacing, SizeInfo, FontMetrics
from src.linkHandler import Link, LinkCollection, LinkFormatter

@dataclass
class LineSpec:
    text: str
    size: SizeInfo
    isRequired: bool
    jobIndex: Optional[int] = None
    sectionIndex: Optional[int] = None
    pointIndex: Optional[int] = None
    lineType: str = "regular" # TODO: // Enum of lineType
    links: Optional[LinkCollection] = None

class LineGenerator:
    def __init__(self, fontMetrics: FontMetrics):
        self.fontMetrics = fontMetrics
        self.linkFormatter = LinkFormatter()
    
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
        
        if contact.get('contactInformation', None):
            link_collection = LinkCollection.from_list(contact['contactInformation'])
            if link_collection:
                display_text = link_collection.get_display_text()
                if contact['location'] is not None:
                    display_text += f" | {contact['location']}"

                lines.append(LineSpec(
                    text=display_text,
                    size=FontSize.REGULAR,
                    isRequired=True,
                    lineType="contact",
                    links=link_collection
                ))
        
        if 'links' in contact and contact['links'] is not None:
            link_collection = LinkCollection.from_list(contact['links'])
            
            if link_collection:
                display_text = link_collection.get_display_text()
                lines.append(LineSpec(
                    text=display_text,
                    size=FontSize.REGULAR,
                    isRequired=True,
                    lineType="contact",
                    links=link_collection
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
                size=Spacing.GAP_SMALL,
                isRequired=False,
                jobIndex=jobIndex,
                lineType="gap"
            ))
        
        fromDate = job.get('from', job.get('from_date', ''))
        toDate = job.get('to', job.get('to_date', ''))
        
        text = f"{job['role']}"
        if job['company'] is not None:
            text += f" at {job['company']}"

        lines.append(LineSpec(
            text=text,
            size = FontSize.SUBTITLE,
            isRequired = False,
            jobIndex = jobIndex,
            lineType = 'jobHeader'
        ))
        
        lines.append(LineSpec(
            text = f"{fromDate} — {toDate}",
            size = FontSize.REGULAR,
            isRequired = False,
            jobIndex = jobIndex,
            lineType = 'jobHeader'
        ))

        lines.append(LineSpec(text="", size=Spacing.GAP_SMALL, isRequired=False, jobIndex=jobIndex, lineType="gap"))
        
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
        # Convert to LinkCollection
        link_collection = LinkCollection.from_list(links)
        
        # Get display text for height calculation
        display_text = link_collection.get_display_text()
        
        return LineSpec(
            text=display_text,
            size=FontSize.REGULAR,
            isRequired=False,
            jobIndex=jobIndex,
            sectionIndex=sectionIndex,
            lineType="links",
            links=link_collection
        )
    
    def generateEducationLines(self, education: dict) -> List[LineSpec]:
        lines = []
        
        lines.append(LineSpec(text="", size=Spacing.GAP, isRequired=True, lineType="gap"))
        lines.append(LineSpec(text=education['title'], size=FontSize.TITLE, isRequired=True, lineType="header"))
        
        degree = f"{education['degree']} in {education['major']}"
        conc = education.get('concentration', None)
        if conc:
            degree += f", Concentration in {conc}"

        lines.append(LineSpec(text=degree, size=FontSize.REGULAR, isRequired=True, lineType="education"))
        
        grad = education.get('graduation', None)
        if grad:
            if grad['hasGraduated']:
                gradLine = f"Graduated: {grad['on']}"
            else:
                gradLine = f"Expected: {grad['on']}"
        else:
            gradLine = None

        school = f"{education['school']}, {education['location']}"
        if gradLine is not None:
            school += f" | {gradLine}"

        if education['gpa'] is not None:
            school += f" | GPA: {education['gpa']}"

        lines.append(LineSpec(text=school, size=FontSize.REGULAR, isRequired=True, lineType="education"))
        
        if len(education['honors']) > 0:
            honorsList = self.combine(education['honors'], ', ')
            lines.append(LineSpec(text=f"Honors: {honorsList}", size=FontSize.REGULAR, isRequired=True, lineType="education"))
        
        return lines
    
    def generateProjectsHeader(self, projects: dict) -> List[LineSpec]:
        return [
            LineSpec(text="", size=Spacing.GAP, isRequired=True, lineType="gap"),
            LineSpec(text=projects['title'], size=FontSize.TITLE, isRequired=True, lineType="header")
        ]
    
    def generateProjectHeader(self, project: dict, projectIndex: int) -> List[LineSpec]:
        lines = []
        
        if projectIndex > 0:
            lines.append(LineSpec(
                text="",
                size=Spacing.GAP_SMALL,
                isRequired=False,
                lineType="gap"
            ))
        
        lines.append(LineSpec(
            text=project['title'],
            size=FontSize.SUBTITLE,
            isRequired=False,
            lineType="projectHeader"
        ))
        
        return lines
    
    def generateProjectPointLine(self, point: str, projectIndex: int, pointIndex: int) -> LineSpec:
        return LineSpec(
            text=f"- {point}",
            size=FontSize.REGULAR,
            isRequired=False,
            lineType="projectPoint"
        )
    
    def generateProjectKeywordsLine(self, keywords: List[str], projectIndex: int) -> LineSpec:
        keywordsText = self.combine(keywords, ', ')
        return LineSpec(
            text=f"Technologies Used: {keywordsText}",
            size=FontSize.REGULAR,
            isRequired=False,
            lineType="projectKeywords"
        )
    
    def generateProjectLinksLine(self, links: List[dict], projectIndex: int) -> LineSpec:
        # Convert to LinkCollection
        link_collection = LinkCollection.from_list(links)
        
        # Get display text for height calculation
        display_text = link_collection.get_display_text()
        
        return LineSpec(
            text=display_text,
            size=FontSize.REGULAR,
            isRequired=False,
            lineType="projectLinks",
            links=link_collection  # Store for later rendering
        )

    def generateCoursesLine(self, courses: List[str]) -> LineSpec:
        coursesText = self.combine(courses, ', ')
        return LineSpec(
            text=f"Relevant Courses: {coursesText}",
            size=FontSize.REGULAR,
            isRequired=False,
            lineType="courses"
        )

    def calculateHeight(self, lineSpec: LineSpec) -> int:
        """Calculate height using display text (which accounts for aliases)"""
        return self.fontMetrics.getHeight(lineSpec.text, lineSpec.size)
    
    def generateAllRequiredLines(self, content: dict) -> List[LineSpec]:
        lines = []
        lines.extend(self.generateContactLines(content['contact']))
        lines.extend(self.generateSkillsHeader(content['skills']))
        lines.extend(self.generateExperienceHeader(content['experience']))
        # TODO: Decide whether or not project header should be required?
        lines.extend(self.generateEducationLines(content['education']))
        return lines
    
    def calculateTotalHeight(self, lines: List[LineSpec]) -> int:
        return sum(self.calculateHeight(line) for line in lines)
