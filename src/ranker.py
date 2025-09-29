import yaml
from pathlib import Path
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
from src.core import Models, FontMetrics, SpaceInformation, ProcessedItem, SizeInfo, FontSize, Spacing, ItemType

MODEL = Models.SMALL
TEMPLATE_PATH='template.example.yaml'
FONT_METRICS = FontMetrics()
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

def makeBatch(content: dict, jobPosting: str) -> tuple[list[str], list[ProcessedItem]]:
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

    batchIn.append(jobPosting)
    processedItems.append(ProcessedItem(
        text = jobPosting,
        index = rootIdx,
        lineHeight = 0,
        lineWidth = 0,
        itemType = ItemType.JOB_POSTING
    ))

    return batchIn, processedItems

def getRequiredLineWeights(lines: list[tuple[str, SizeInfo]]) -> int:
    totalHeight = sum(FONT_METRICS.getHeight(text, size) for text, size in lines)
    remainingHeight = max(SPACE_INFO.maxHeight - totalHeight, 0)
    
    return remainingHeight

def encode(batch: list[str]):
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer(MODEL, device='cpu')
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

def prunePoints(items: list[ProcessedItem], similarities: list[float], heightRemaining: int) -> tuple[list[ProcessedItem], int, set, set]:
    
    def iterate(_capacity):
        if _capacity <= 0:
            return [False] * len(targetValues)

        if all(tw == targetWeights[0] for tw in targetWeights):
            maxItems = _capacity // targetWeights[0]
            sortedTargets = sorted(range(len(targetValues)), key = lambda i: targetValues[i], reverse = True)
            chosen = [False] * len(targetValues)
            for i in sortedTargets[:maxItems]:
                chosen[i] = True
        else:
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


        # TODO: Account for link line in sections
        newOverhead = (SPACE_INFO.jobOverhead * len(newJobs) - Spacing.GAP.height) + (SPACE_INFO.sectionOverhead + SPACE_INFO.keywordReserve) * len(newSections) - Spacing.GAP_SMALL.height
        removedOverhead = SPACE_INFO.jobOverhead * len(removedJobs) + (SPACE_INFO.sectionOverhead + SPACE_INFO.keywordReserve) * len(removedSections)
        netOverheadChange = newOverhead - removedOverhead
        
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

        if abs(netOverheadChange) <= 1:
            break

    keepers = [targets[i] for i, picked in enumerate(chosen) if picked]
    keepersHeight = sum([k.lineHeight for k in keepers])
    keepersOverheadHeight = (SPACE_INFO.jobOverhead * len(accountedJobs)) + (SPACE_INFO.sectionOverhead * len(accountedSections))

    # HACK: Space reserved for keywords here, as we need to know how many sections are being used first.
    keywordReserve = len(accountedSections) * SPACE_INFO.keywordReserve
    usedSpace = keepersHeight + keepersOverheadHeight - keywordReserve
    
    remainingSpace = heightRemaining - usedSpace

    return keepers, usedSpace, accountedJobs, accountedSections

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


def rank(content: dict, jobPosting: str):
    requiredLines = generateRequiredLines(content)

    heightRemaining = getRequiredLineWeights(requiredLines) - SPACE_INFO.skillReserve

    if (heightRemaining <= 0):
        # NOTE: This check misses that fact that remainingHeight may be less than the height of a single line
        print("The required content takes up all the space!")
        exit()

    # TODO: Something to validate the YAML structure that must exist, does exist.
    batchIn, processedItems = makeBatch(content, jobPosting)

    print("Encoding data... this may take a while.")
    
    embeddings = encode(batchIn)
    
    similarities = analyze(processedItems, embeddings)

    points, pointsSpace, jobs, sections = prunePoints(processedItems, similarities, heightRemaining)

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

    return points, keywords, skills, jobs, sections

