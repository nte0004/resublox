import yaml
import sys
from pathlib import Path
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
from fontTools.ttLib import TTFont
from dataclasses import dataclass, field
from enum import Enum
import math
from typing import List, Tuple, Dict, Any

@dataclass
class FontInfo:
    name: str
    path: str
    unitsPerEm: int
    fontHeightUnits: int
    fontAvgWidthUnits: int

class Fonts:
    # Values found with fontHelper.py
    ARIAL = FontInfo(
        name = 'arial',
        path = 'fonts/arial/arial.ttf',
        unitsPerEm = 2048,
        fontHeightUnits = 2355,
        fontAvgWidthUnits = 1079
    )

FONT = Fonts.ARIAL
LINE_HEIGHT = 1.15
SCALE_FACTOR = 100

@dataclass
class SizeInfo:
    size: float
    heightPt: float = field(init=False)
    heightInch: float = field(init=False)
    height: int = field(init=False)

    def __post_init__(self):
        self.heightPt = (FONT.fontHeightUnits * self.size * LINE_HEIGHT) / FONT.unitsPerEm
        self.heightInch = (self.heightPt / 72)
        self.height = int(self.heightInch * SCALE_FACTOR)


class FontSize:
    NAME = SizeInfo(13)
    REGULAR = SizeInfo(10)
    TITLE = SizeInfo(12)
    SUBTITLE = SizeInfo(11)

class Spacing:
    GAP = SizeInfo(6)
    GAP_SMALL = SizeInfo(3)

class Models:
    SMALL = './models/all-MiniLM-L6-v2'
    MEDIUM = './models/all-MiniLM-L12-v2'
    LARGE = './models/all-mpnet-base-v2'

MODEL = Models.SMALL

TEMPLATE_PATH='template.example.yaml'

PAGE_WIDTH_INCHES = 8.5
PAGE_WIDTH = int(PAGE_WIDTH_INCHES * SCALE_FACTOR)

PAGE_HEIGHT_INCHES = 11
PAGE_HEIGHT = int(PAGE_HEIGHT_INCHES * SCALE_FACTOR)

MARGIN_INCHES = [1, 1, 1, 1]
MARGIN = [int(m * SCALE_FACTOR) for m in MARGIN_INCHES]

MAX_PAGES = 1


# TODO: Take user input of job posting
JOB_POSTING = """
TechFlow Solutions is a fast-growing fintech startup revolutionizing how small businesses manage their cash flow. We're backed by top-tier VCs and serving over 10,000 customers across North America. Join our mission to democratize financial tools for entrepreneurs everywhere. We're seeking a Senior Software Engineer to join our core platform team. You'll work on high-impact features that directly serve our customers, from building intuitive dashboards to architecting scalable backend systems. This is a chance to wear multiple hats and make a real difference in a collaborative, fast-paced environment. Design and implement full-stack features using React, Node.js, and PostgreSQL. Collaborate with product managers and designers to translate requirements into elegant solutions. Write clean, testable code and participate in code reviews. Optimize application performance and ensure scalability. Mentor junior developers and contribute to technical decision-making. Work with our DevOps team to maintain CI/CD pipelines and AWS infrastructure. 4+ years of software development experience. Strong proficiency in JavaScript/TypeScript and modern React. Experience with Node.js and RESTful API design. Familiarity with SQL databases (PostgreSQL preferred). Understanding of version control (Git) and agile development practices. Excellent communication skills and collaborative mindset. Experience with AWS services (EC2, RDS, Lambda). Knowledge of Docker and containerization. Background in fintech or financial services. Experience with testing frameworks (Jest, Cypress). Familiarity with GraphQL.
"""
class FontMetrics:
    def __init__(self, font_path: str):
        self.font = TTFont(font_path)
        self.cmap = self.font.getBestCmap()
        self.hmtx = self.font['hmtx']
        self.maxWidthInches = PAGE_WIDTH_INCHES - MARGIN_INCHES[1] - MARGIN_INCHES[3]
        self.maxWidth = PAGE_WIDTH - MARGIN[1] - MARGIN[3]
        
    def getWidth(self, text: str, size: SizeInfo) -> int:
        """ Returns the width a string will consume.
            Does not account for line-wrapping.
        """
        totalWidth = 0
        for char in text:
            glyph_name = self.cmap.get(ord(char))
            if glyph_name:
                width, _ = self.hmtx[glyph_name]
                totalWidth += width
            else:
                totalWidth += FONT.fontAvgWidthUnits
        
        widthPts = (totalWidth * size.size) / FONT.unitsPerEm
        widthInches = widthPts / 72
        width = int(widthInches * SCALE_FACTOR)

        return width

    def getHeight(self, text: str, size: SizeInfo) -> int:
        """ Returns the height a string will consume. """
        if not text.strip():  # Empty or whitespace-only text
            return int((size.size / 72) * SCALE_FACTOR)  # Just spacing
            
        width = self.getWidth(text, size)
        lineCount = math.ceil(width / self.maxWidth)
        
        height = size.height * lineCount
        
        return height

FONT_METRICS = FontMetrics(FONT.path)

class ItemType(Enum):
    SKILL = 0
    POINT = 1
    KEYWORD = 2
    JOB_POSTING = 3

@dataclass
class ProcessedItem:
    text: str
    index: int
    lineHeight: int
    lineWidth: int
    itemType: ItemType
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class SpaceInformation:
    jobOverhead: int = field(init = False)
    sectionOverhead: int = field(init = False)
    skillReserve: int = field(init = False)
    keywordReserve: int = field(init = False)
    keywordLinesPerSection: int = 1
    skillsLineCount: int = 2

    def __init__(self):
        # TODO: Have these be defined relative to some kind of YAML schema
        self.jobOverhead = (4 * FontSize.REGULAR.height) + Spacing.GAP_SMALL.height
        self.sectionOverhead = FontSize.SUBTITLE.height + FontSize.REGULAR.height
        self.skillReserve = self.skillsLineCount * FontSize.REGULAR.height
        self.keywordReserve = self.keywordLinesPerSection * FontSize.REGULAR.height

SPACE_INFO = SpaceInformation()

def loadYAML(path:str) -> dict|None:
    try:
        if not Path(path).exists():
            raise FileNotFoundError(f"Template not found, looking for file: {path}")

        with open(path, 'r', encoding='utf-8') as file:
            content = yaml.safe_load(file)

            if content is None:
                return {}

            return content
    
    except FileNotFoundError as e:
        print(f"Error: {e}")
        return None
    except yaml.YAMLError as e:
        print(f"Error parsing YAML: {e}")
        return None
    except Exception as e:
        print(f"Error loading YAML: {e}")
        return None

def combine(texts: list[str], seperator: str) -> str:
    """ 
        Returns a concatenation of the provided list of words seperated by the seperator.
        The last word in the string does not have a trailing seperator.
    """
    line = ""
    for text in texts[:-1]:
        line += text
        line += seperator
    line += texts[-1];

    return line

def generateRequiredLines(content: dict) -> list[tuple[str, SizeInfo]]:
    lines = []

    # Contact Info
    c = content['contact']
    lines.append((c['name'], FontSize.NAME))
    lines.append((f"Email: {c['email']} | Phone: {c['phone']} | {c['location']}", FontSize.REGULAR))
    lines.append((f"Github: {c['github']} | Website: {c['website']}", FontSize.REGULAR))

    # Gap
    lines.append(('', Spacing.GAP))

    # Skills
    s = content['skills']
    lines.append((s['title'], FontSize.TITLE))
    
    # Gap
    lines.append(('', Spacing.GAP))

    # Experience
    e = content['experience']
    lines.append((e['title'], FontSize.TITLE))
    lines.append(('', Spacing.GAP_SMALL))
    
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
        if grad['hasGraduated']:
            gradLine = f"Graduated: {grad['on']}"
        else:
            gradLine = f"Expected Graduation: {grad['on']}"

        lines.append((gradLine, FontSize.REGULAR))

    lines.append((f"GPA: {e['gpa']}", FontSize.REGULAR))

    honorsList = combine(e['honors'], ', ')
    lines.append((f"Honors: {honorsList}", FontSize.REGULAR))

    courseList = combine(e['courses'], ', ')
    lines.append((f"Relevant Courses: {courseList}", FontSize.REGULAR))

    return lines

def makeBatch(content: dict) -> tuple[list[str], list[ProcessedItem]]:
    batchIn = []
    processedItems = []
    rootIdx = 0

    skills = content['skills']['list']
    if (skills): 
        for s in skills:
            lineWidth = FONT_METRICS.getWidth(s, FontSize.REGULAR)
            batchIn.append(s)
            processedItems.append(ProcessedItem(
                text = s,
                index = rootIdx,
                lineHeight = 0,
                lineWidth = lineWidth,
                itemType = ItemType.SKILL
            ))

            rootIdx += 1

    jobs = content['experience']['jobs']
    for jIdx ,j in enumerate(jobs):
        for sIdx, s in enumerate(j['sections']):
            for pIdx, p in enumerate(s['points']):
                lineHeight = FONT_METRICS.getHeight(f"- {p}", FontSize.REGULAR)
                batchIn.append(p)
                processedItems.append(ProcessedItem(
                    text = p,
                    index = rootIdx,
                    lineHeight = lineHeight,
                    lineWidth = 0,
                    itemType = ItemType.POINT,
                    metadata = {
                        'jobIndex': jIdx,
                        'sectionIndex': sIdx,
                        'pointIndex': pIdx
                    }
                ))
                rootIdx += 1

            for kIdx, k in enumerate(s['keywords']):
                lineWidth = FONT_METRICS.getWidth(k, FontSize.REGULAR)
                batchIn.append(k)
                processedItems.append(ProcessedItem(
                    text = k,
                    index = rootIdx,
                    lineHeight = 0,
                    lineWidth = lineWidth,
                    itemType = ItemType.KEYWORD,
                    metadata = {
                        'jobIndex': jIdx,
                        'sectionIndex': sIdx,
                        'keywordIndex': kIdx
                    }
                ))
                rootIdx += 1

    batchIn.append(JOB_POSTING)
    processedItems.append(ProcessedItem(
        text = JOB_POSTING,
        index = rootIdx,
        lineHeight = 0,
        lineWidth = 0,
        itemType = ItemType.JOB_POSTING
    ))

    return batchIn, processedItems

def getRequiredLineWeights(lines: list[tuple[str, SizeInfo]]) -> int:
    maxHeight = (PAGE_HEIGHT - MARGIN[0] - MARGIN[2]) * MAX_PAGES
    totalHeight = sum(FONT_METRICS.getHeight(text, size) for text, size in lines)
    remainingHeight = max(maxHeight - totalHeight, 0)
    
    return remainingHeight

def encode(batch: list[str]):
    model = SentenceTransformer(MODEL)
    return model.encode(batch)

def analyze(processedItems: list[ProcessedItem], embeddings) -> list[float]:
    # NOTE: Maybe iterate in reverse since jobPosting is the last thing appended
    jobPostingItem = next(item for item in processedItems if item.itemType == ItemType.JOB_POSTING)
    jobPostingEmbedding = embeddings[jobPostingItem.index].reshape(1, -1)

    similarities = cosine_similarity(embeddings, jobPostingEmbedding).flatten()
    
    return similarities.tolist()

def knapsack(values: list[float], weights: list[int], capacity: int) -> list[bool]:
    n = len(values)
    if n != len(weights):
        print("Every value must have a weight")
        exit()

    intCapacity = int(capacity)
    intWeights = [int(w) for w in weights]

    table = np.zeros((n + 1, intCapacity + 1), dtype=np.float32)

    for i in range(1, n + 1):
        for w in range (1, intCapacity + 1):
            if intWeights[i - 1] <= w:
                table[i][w] = max(
                    values[i - 1] + table[i - 1][w - intWeights[i - 1]],
                    table[i - 1][w]
                )
            else:
                table[i][w] = table[i - 1][w]

    selected = [False] * n
    w = intCapacity
    for i in range(n, 0, -1):
        if table[i][w] != table[i - 1][w]:
            selected[i - 1] = True
            w -= intWeights[i - 1]

    return selected

def prunePoints(items: list[ProcessedItem], similarities: list[float], heightRemaining: int) -> tuple[list[ProcessedItem], int, set]:
    print(f"Height Remaining: {heightRemaining}")
    
    def iterate(_capacity):
        if _capacity <= 0:
            return [False] * len(targetValues)

        # OPTIMIZE: Apparently there is an optimization here
        if all(tw == targetWeights[0] for tw in targetWeights):
            print('targets are the same weight')
            maxItems = _capacity // targetWeights[0]
            sortedTargets = sorted(range(len(targetValues)), key = lambda i: targetValues[i], reverse = True)
            chosen = [False] * len(targetValues)
            for i in sortedTargets[:maxItems]:
                chosen[i] = True
        else:
            print(f"targetWeights: {targetWeights}")
            print(f'_capacity: {_capacity}')
            chosen = knapsack(targetValues, targetWeights, _capacity)

        return chosen

    targets = [item for item in items if item.itemType == ItemType.POINT]
    targetValues = [similarities[item.index] for item in targets]
    targetWeights = [item.lineHeight for item in targets]
    capacity = heightRemaining

    chosen = []
    accountedJobs = set()
    accountedSections = set()
    curCapacity = capacity
    iteration = 0
    maxIterations = 10 
    while iteration < maxIterations:
        iteration += 1
        print(f'Iteration: {iteration}')

        print(f'Capacity: {curCapacity}')
        chosen = iterate(curCapacity)

        ckeepers = [targets[i] for i, picked in enumerate(chosen) if picked]
    
        distinctJobs, distinctSections = set(), set()
        for i, picked in enumerate(chosen):
            if picked:
                item = targets[i]
                jobIdx = item.metadata['jobIndex']
                sectionIdx = item.metadata['sectionIndex']

                distinctJobs.add(jobIdx)
                distinctSections.add(sectionIdx)

        newJobs = distinctJobs - accountedJobs
        removedJobs = accountedJobs - distinctJobs
        newSections = distinctSections - accountedSections
        removedSections = accountedSections - distinctSections

        newOverhead = SPACE_INFO.jobOverhead * len(newJobs) + SPACE_INFO.sectionOverhead * len(newSections)
        removedOverhead = SPACE_INFO.jobOverhead * len(removedJobs) + SPACE_INFO.sectionOverhead * len(removedSections)
        netOverheadChange = newOverhead - removedOverhead
        
        if netOverheadChange == 0:
            print('no change, breaking')
            break
        elif netOverheadChange > 0:
            print(f'increased overhead, reducing capacity by {netOverheadChange}')
            curCapacity -= netOverheadChange
            if curCapacity <= 0:
                chosen = [False] * len(items)
                distinctJobs, distinctSections = set(), set()
                break
        else:
            print(f'decreased overhead, increasing capacity by {netOverheadChange}')
            # Increase capacity when netOverheadChange is negative
            curCapacity -= netOverheadChange
        
        accountedJobs = distinctJobs.copy()
        accountedSections = distinctSections.copy()

        if abs(netOverheadChange) <= 1:
            break

    keepers = [targets[i] for i, picked in enumerate(chosen) if picked]
    keepersHeight = sum([k.lineHeight for k in keepers])
    print(f"Chosen take up: {keepersHeight}")
    keepersOverheadHeight = (SPACE_INFO.jobOverhead * len(accountedJobs)) + (SPACE_INFO.sectionOverhead * len(accountedSections))
    print(f"Overhead takes up: {keepersOverheadHeight}")

    # HACK: Space reserved for keywords here, as we need to know how many sections are being used first.
    keywordReserve = len(accountedSections) * SPACE_INFO.keywordReserve
    usedSpace = keepersHeight + keepersOverheadHeight - keywordReserve
    
    remainingSpace = heightRemaining - usedSpace
    print(f"Remaining Space = {remainingSpace}")

    return keepers, usedSpace, accountedSections

def pruneKeywords(items: list[ProcessedItem], similarities: list[float], sections: set) -> tuple[list[ProcessedItem], int]:
    keywords = [item for item in items if item.itemType == ItemType.KEYWORD]
    if not keywords:
        return [], 0

    header = "Technologies Used: "
    seperator = ", "

    headerWeight = FONT_METRICS.getWidth(header, FontSize.REGULAR)
    seperatorWeight = FONT_METRICS.getWidth(seperator, FontSize.REGULAR)
    constWeight = FONT_METRICS.maxWidth * SPACE_INFO.keywordLinesPerSection - headerWeight

    keepers = []
    keepersHeight = 0
    for sectionIdx in sections:
        sectionKeywords = [k for k in keywords if k.metadata['sectionIndex'] == sectionIdx]
        validationText = [k.text for k in sectionKeywords]
        
        skValues = [similarities[sk.index] for sk in sectionKeywords]
        skWeights = [sk.lineWidth for sk in sectionKeywords]
        
        capacity = constWeight - (len(keywords) - 1) * seperatorWeight
        if capacity <= 0:
            return [], 0

        chosen = knapsack(skValues, skWeights, capacity)

        keepersText = []
        for i, picked in enumerate(chosen):
            if picked:
                keepers.append(sectionKeywords[i])
                keepersText.append(validationText[i])
        
        keepersHeight += FONT_METRICS.getHeight(combine(keepersText, seperator), FontSize.REGULAR)

    return keepers, keepersHeight

def pruneSkills(items: list[ProcessedItem], similarities: list[float]) -> tuple[list[ProcessedItem], int]:
    skills = [item for item in items if item.itemType == ItemType.SKILL]
    if not skills:
        return [], 0

    seperator = ", "

    seperatorWeight = FONT_METRICS.getWidth(seperator, FontSize.REGULAR)
    constWeight = FONT_METRICS.maxWidth * SPACE_INFO.skillsLineCount

    keepers = []
    keepersHeight = 0
        
    validationText = [s.text for s in skills]
        
    skillValues = [similarities[s.index] for s in skills]
    skillWeights = [s.lineWidth for s in skills]
        
    capacity = constWeight - (len(skills) - 1) * seperatorWeight
    if capacity <= 0:
        return [], 0

    chosen = knapsack(skillValues, skillWeights, capacity)

    keepersText = []
    for i, picked in enumerate(chosen):
        if picked:
            keepers.append(skills[i])
            keepersText.append(validationText[i])
    
    keepersHeight += FONT_METRICS.getHeight(combine(keepersText, seperator), FontSize.REGULAR)

    return keepers, keepersHeight


if __name__ == "__main__":
    content = loadYAML(TEMPLATE_PATH)

    if content is None:
        exit()
    elif not content:
        print(f"YAML loaded, but there was nothing to work with. Exiting")
        exit()

    requiredLines = generateRequiredLines(content)

    heightRemaining = getRequiredLineWeights(requiredLines) - SPACE_INFO.skillReserve

    if (heightRemaining <= 0):
        # NOTE: This check misses that fact that remainingHeight may be less than the height of a single line
        print("The required content takes up all the space!")
        exit()

    # TODO: Something to validate the YAML structure that must exist, does exist.
    batchIn, processedItems = makeBatch(content)

    print("Encoding data... this may take a while.")
    
    embeddings = encode(batchIn)
    
    similarities = analyze(processedItems, embeddings)

    points, pointsSpace, sections = prunePoints(processedItems, similarities, heightRemaining)

    heightRemaining -= pointsSpace
    
    print(f"Height Remaining Inches: {heightRemaining}")

    keywords, keywordsHeight = pruneKeywords(processedItems, similarities, sections)

    print(f"Keyword Height: {keywordsHeight}")

    heightRemaining -= keywordsHeight

    print(f"Height Remaining: {heightRemaining}")
    
    heightRemaining += SPACE_INFO.skillReserve

    skills, skillsHeight = pruneSkills(processedItems, similarities)

    print(f"Skills Height: {skillsHeight}")
    heightRemaining -= skillsHeight

    print(f"Remaining Height: {heightRemaining}")

