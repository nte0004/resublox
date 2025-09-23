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

@dataclass
class SizeInfo:
    size: float
    heightPt: float = field(init=False)
    heightInch: float = field(init=False)

    def __post_init__(self):
        self.heightPt = (FONT.fontHeightUnits * self.size * LINE_HEIGHT) / FONT.unitsPerEm
        self.heightInch = self.heightPt / 72


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
PAGE_HEIGHT_INCHES = 11
MARGIN_INCHES = [1, 1, 1, 1]
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
        
    def getWidth(self, text: str):
        totalWidth = 0
        for char in text:
            glyph_name = self.cmap.get(ord(char))
            if glyph_name:
                width, _ = self.hmtx[glyph_name]
                totalWidth += width
            else:
                totalWidth += FONT.fontAvgWidthUnits
        return totalWidth

    def getLineWeight(self, text: str, size: SizeInfo) -> float:
        if not text.strip():  # Empty or whitespace-only text
            return size.size / 72  # Just spacing
            
        totalWidth = self.getWidth(text)
        
        widthPts = (totalWidth * size.size) / FONT.unitsPerEm
        widthInches = widthPts / 72
        lineCount = math.ceil(widthInches / self.maxWidthInches)
        
        return size.heightInch * lineCount

    def getWordWeight(self, text: str, size: SizeInfo) -> float:
        totalWidth = self.getWidth(text)
        widthPts = (totalWidth * size.size) / FONT.unitsPerEm
        widthInches = widthPts / 72

        return widthInches

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
    lineWeight: float|None
    wordWeight: float|None
    itemType: ItemType
    metadata: Dict[str, Any] = field(default_factory=dict)

def loadYAML(path):
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

def combine(texts, seperator):
    line = ""
    for text in texts[:-1]:
        line += text
        line += seperator
    line += texts[-1];

    return line

def generateRequiredLines(content):
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
    job = e['jobs'][0]

    lines.append((job['role'], FontSize.REGULAR))
    lines.append((job['company'], FontSize.REGULAR))
    lines.append((job['location'], FontSize.REGULAR))

    timeRange = combine([job['from'], job['to']], ' \u2014 ') # Em Dash
    lines.append((timeRange, FontSize.REGULAR))

    lines.append(('', Spacing.GAP_SMALL))

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

def makeBatch(content):
    batchIn = []
    processedItems = []
    rootIdx = 0

    #skills = content['skills']['list']
    #if (skills): 
    #    for s in skills:
    #        lineWeight = FONT_METRICS.getLineWeight(s, FontSize.REGULAR)
    #        batchIn.append(s)
    #        processedItems.append(ProcessedItem(
    #            text = s,
    #            index = rootIdx,
    #            lineWeight = lineWeight,
    #            itemType = ItemType.SKILL
    #        ))

    #        rootIdx += 1

    jobs = content['experience']['jobs']
    for jIdx ,j in enumerate(jobs):
        for sIdx, s in enumerate(j['sections']):
            for pIdx, p in enumerate(s['points']):
                lineWeight = FONT_METRICS.getLineWeight(p, FontSize.REGULAR)
                batchIn.append(p)
                processedItems.append(ProcessedItem(
                    text = p,
                    index = rootIdx,
                    lineWeight = lineWeight,
                    wordWeight = None,
                    itemType = ItemType.POINT,
                    metadata = {
                        'jobIndex': jIdx,
                        'sectionIndex': sIdx,
                        'pointIndex': pIdx
                    }
                ))
                rootIdx += 1

            for kIdx, k in enumerate(s['keywords']):
                wordWeight = FONT_METRICS.getWordWeight(k, FontSize.REGULAR)
                batchIn.append(k)
                processedItems.append(ProcessedItem(
                    text = k,
                    index = rootIdx,
                    lineWeight = None,
                    wordWeight = wordWeight,
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
        lineWeight = None,
        wordWeight = None,
        itemType = ItemType.JOB_POSTING
    ))

    return batchIn, processedItems

def getRequiredLineWeights(lines):
    maxHeightInches = (PAGE_HEIGHT_INCHES - MARGIN_INCHES[0] - MARGIN_INCHES[2]) * MAX_PAGES
    totalHeight = sum(FONT_METRICS.getLineWeight(text, size) for text, size in lines)
    remainingHeight = max(maxHeightInches - totalHeight, 0)
    
    return totalHeight, remainingHeight

def encode(batch):
    model = SentenceTransformer(MODEL)
    return model.encode(batch)

def analyze(processedItems, embeddings):
    # NOTE: Maybe iterate in reverse since jobPosting is the last thing appended
    jobPostingItem = next(item for item in processedItems if item.itemType == ItemType.JOB_POSTING)
    jobPostingEmbedding = embeddings[jobPostingItem.index].reshape(1, -1)

    similarities = cosine_similarity(embeddings, jobPostingEmbedding).flatten()
    
    return similarities.tolist()

def knapsack(values, weights, capacity):
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
            w -= weights[i - 1]

    return selected

def getLineOverhead(fontSize = FontSize.REGULAR):
    lineHeight = fontSize.heightInch
    
    jobOverheadHeight = FontSize.TITLE.heightInch + 4 * FontSize.REGULAR.heightInch + Spacing.GAP_SMALL.heightInch
    jobOverheadLines = math.ceil(jobOverheadHeight / lineHeight)
    
    sectionOverheadHeight = (FontSize.SUBTITLE.heightInch + Spacing.GAP_SMALL.heightInch)
    sectionOverheadLines = math.ceil(sectionOverheadHeight / lineHeight)
    
    return jobOverheadLines, sectionOverheadLines

def getDistinctionsFromChosen(items, chosen):
    jobs = set()
    sections = set()

    for i, picked in enumerate(chosen):
        if picked:
            item = items[i]
            jobIdx = item.metadata['jobIndex']
            sectionIdx = item.metadata['sectionIndex']

            jobs.add(jobIdx)
            sections.add(sectionIdx)

    return jobs, sections

def prunePoints(items, similarities, heightRemaining):
    jobOverhead, sectionOverhead = getLineOverhead()

    def iterate(_capacity, maxIterations = 10):
        if _capacity <= 0:
            return [False] * len(targetValues)

        if all(twl == targetLineWeights[0] for twl in targetLineWeights):
            sortedTargets = sorted(range(len(targetValues)), key = lambda i: targetValues[i], reverse = True)
            chosen = [False] * len(targetValues)
            for i in sortedTargets[:_capacity]:
                chosen[i] = True
        else:
            chosen = knapsack(targetValues, targetWeights, _capacity)

        return chosen

    targets = [item for item in items if item.itemType == ItemType.POINT]
    targetValues = [similarities[item.index] for item in targets]
    targetWeights = [item.lineWeight for item in targets]
    
    lineHeight = FontSize.REGULAR.heightInch
    targetLineWeights = [(math.ceil(tw / lineHeight)) for tw in targetWeights]

    capacity = math.floor(heightRemaining / lineHeight)

    print(f"Available space: {capacity} lines")
    print(f"Total job points available: {len(targets)}")

    accountedJobs = set()
    accountedSections = set()
    curCapacity = capacity
    iteration = 0
    maxIterations = 10
    
    print(f"Starting optimization with capacity: {curCapacity} lines")
    while iteration < maxIterations:
        iteration += 1

        chosen = iterate(curCapacity)

        distinctJobs, distinctSections = getDistinctionsFromChosen(items, chosen)

        newJobs = distinctJobs - accountedJobs
        removedJobs = accountedJobs - distinctJobs
        newSections = distinctSections - accountedSections
        removedSections = accountedSections - distinctSections

        newOverhead = jobOverhead * len(newJobs) + sectionOverhead * len(newSections)
        removedOverhead = jobOverhead * len(removedJobs) + sectionOverhead * len(removedSections)

        netOverheadChange = newOverhead - removedOverhead
        
        print(f"Iteration {iteration}:")
        print(f"  Current capacity: {curCapacity} lines")
        print(f"  Selected: {sum(chosen)} points from {len(distinctJobs)} jobs, {len(distinctSections)} sections")
        print(f"  New jobs: {len(newJobs)}, Removed jobs: {len(removedJobs)}")
        print(f"  New sections: {len(newSections)}, Removed sections: {len(removedSections)}")
        print(f"  Overhead change: +{newOverhead} -{removedOverhead} = {netOverheadChange} lines")
        
        if netOverheadChange == 0:
            break
        elif netOverheadChange > 0:
            curCapacity -= netOverheadChange
            if curCapacity <= 0:
                chosen = [False] * len(items)
                distinctJobs, distinctSections = set(), set()
                break
        else:
            # Increase capacity when netOverheadChange is negative
            curCapacity -= netOverheadChange
        
        accountedJobs = distinctJobs.copy()
        accountedSections = distinctSections.copy()

        if abs(netOverheadChange) < 2:
            break

    print(f"\nOptimization completed in {iteration} iterations")

    cnt = 0
    ocnt = 0
    sumIn = 0
    sumOut = 0
    for i, picked in enumerate(chosen):
        if picked:
            cnt += 1
            sumIn += targetValues[i]
            print(f"{cnt}. {targets[i].text}")
        else:
            ocnt += 1
            sumOut += targetValues[i]

    Iavg = sumIn / (cnt)
    Oavg = sumOut / (ocnt)

    print(f"In Average: {Iavg}")
    print(f"Out Average: {Oavg}")

    return chosen, accountedJobs, accountedSections


def pruneKeywords(items, similarities, sections, maxLines = 1):
    SCALE_FACTOR = 100

    keywords = [item for item in items if item.itemType == ItemType.KEYWORD]

    if not keywords:
        return []

    header = "Technologies Used: "
    seperator = ", "

    headerWeight = FONT_METRICS.getWordWeight(header, FontSize.REGULAR)
    seperatorWeight = FONT_METRICS.getWordWeight(seperator, FontSize.REGULAR)
    constWeight = FONT_METRICS.maxWidthInches * maxLines - headerWeight

    keepers = []
    for sectionIdx in sections:
        sectionKeywords = [k for k in keywords if k.metadata['sectionIndex'] == sectionIdx]
        
        skValues = [similarities[sk.index] for sk in sectionKeywords]
        skWeights = [int(sk.wordWeight * SCALE_FACTOR) for sk in sectionKeywords]
        
        availableSpace = constWeight - (len(keywords) - 1) * seperatorWeight
        if availableSpace <= 0:
            return []

        capacity = int(availableSpace * SCALE_FACTOR)

        chosen = knapsack(skValues, skWeights, capacity)

        for i, picked in enumerate(chosen):
            if picked:
                keepers.append(sectionKeywords[i])

    return keepers


if __name__ == "__main__":
    content = loadYAML(TEMPLATE_PATH)

    if content is None:
        exit()
    elif not content:
        print(f"YAML loaded, but there was nothing to work with. Exiting")
        exit()

    requiredLines = generateRequiredLines(content)

    heightUsed, heightRemaining = getRequiredLineWeights(requiredLines)

    if (heightRemaining <= 0):
        # NOTE: This check misses that fact that remainingHeight may be less than the height of a single line
        print("The required content takes up all the space!")
        exit()

    # TODO: Something to validate the YAML structure that must exist, does exist.
    batchIn, processedItems = makeBatch(content)

    print("Encoding data... this may take a while.")
    
    embeddings = encode(batchIn)
    
    similarities = analyze(processedItems, embeddings)

    # TODO: prune skills, and prune keywords with traditional knapsack. Need height remaining out of prior pruning.
    # Account for keywords and skills being seperated with ", ". Then subtract that from the max_width as capacity.
    # Can turn weight and capacity into integers by multiplying by 100, then correcting afterwards. For pruning these
    # we can pass a maxLines which will be determined by the height remaining, should be at least 1 though.

    # TODO: just pass what you're pruning instead of all of the items
    points, jobs, sections = prunePoints(processedItems, similarities, heightRemaining)

    print(jobs)
    print(sections)

    keywords = pruneKeywords(processedItems, similarities, sections, 1)
    for k in keywords:
        print(k)
