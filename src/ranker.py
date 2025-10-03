import yaml
from pathlib import Path
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
from src.core import Models, FontMetrics, SpaceInformation, ProcessedItem, SizeInfo, FontSize, Spacing, ItemType
from src.lineGenerator import LineGenerator, LineSpec

MODEL = Models.SMALL
TEMPLATE_PATH='template.example.yaml'
FONT_METRICS = FontMetrics()
LINE_GENERATOR = LineGenerator(FONT_METRICS)
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

def makeBatch(content: dict, jobPosting: str) -> tuple[list[str], list[ProcessedItem]]:
    batchIn = []
    processedItems = []
    rootIdx = 0

    skills = content['skills']['list']
    if (skills): 
        for s in skills:
            lineSpec = LINE_GENERATOR.generateSkillsContent([s])
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
                lineSpec = LINE_GENERATOR.generatePointLine(p, jIdx, sIdx, pIdx)
                lineHeight = LINE_GENERATOR.calculateHeight(lineSpec)
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

def getRequiredLineWeights(content: dict) -> int:
    requiredLines = LINE_GENERATOR.generateAllRequiredLines(content)
    totalHeight = LINE_GENERATOR.calculateTotalHeight(requiredLines)
    #safetyMargin = int(SPACE_INFO.maxHeight * 0.03)
    remainingHeight = max(SPACE_INFO.maxHeight - totalHeight, 0)
    return remainingHeight

def encode(batch: list[str]):
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer(MODEL, device='cpu')
    return model.encode(batch)

def analyze(processedItems: list[ProcessedItem], embeddings) -> list[float]:
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

def calculateJobOverhead(content: dict, jobIndex: int) -> int:
    job = content['experience']['jobs'][jobIndex]
    jobHeaderLines = LINE_GENERATOR.generateJobHeader(job, jobIndex)
    return LINE_GENERATOR.calculateTotalHeight(jobHeaderLines)

def calculateSectionOverhead(content: dict, jobIndex: int, sectionIndex: int, isFirstInJob: bool) -> int:
    section = content['experience']['jobs'][jobIndex]['sections'][sectionIndex]
    sectionHeaderLines = LINE_GENERATOR.generateSectionHeader(section, jobIndex, sectionIndex, isFirstInJob)
    return LINE_GENERATOR.calculateTotalHeight(sectionHeaderLines)

def estimateKeywordsHeight(content: dict, jobIdx: int, sectionIdx: int) -> int:
    section = content['experience']['jobs'][jobIdx]['sections'][sectionIdx]
    if 'keywords' not in section or not section['keywords']:
        return 0
    dummyLine = LINE_GENERATOR.generateKeywordsLine(section['keywords'], jobIdx, sectionIdx)
    return LINE_GENERATOR.calculateHeight(dummyLine)

def estimateLinksHeight(content: dict, jobIdx: int, sectionIdx: int) -> int:
    section = content['experience']['jobs'][jobIdx]['sections'][sectionIdx]
    if 'links' not in section or not section['links']:
        return 0
    dummyLine = LINE_GENERATOR.generateLinksLine(section['links'], jobIdx, sectionIdx)
    return LINE_GENERATOR.calculateHeight(dummyLine)

def prunePoints(content: dict, items: list[ProcessedItem], similarities: list[float], heightRemaining: int) -> tuple[list[ProcessedItem], int, set, set]:
    
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
                distinctSections.add((jobIdx, sectionIdx))

        newJobs = distinctJobs - accountedJobs
        removedJobs = accountedJobs - distinctJobs
        newSections = distinctSections - accountedSections
        removedSections = accountedSections - distinctSections

        newOverhead = 0
        for jobIdx in newJobs:
            newOverhead += calculateJobOverhead(content, jobIdx)
        
        for jobIdx, sectionIdx in newSections:
            jobSections = [s for j, s in distinctSections if j == jobIdx]
            isFirstInJob = sectionIdx == min(jobSections)
            newOverhead += calculateSectionOverhead(content, jobIdx, sectionIdx, isFirstInJob)
            newOverhead += estimateKeywordsHeight(content, jobIdx, sectionIdx)
            newOverhead += estimateLinksHeight(content, jobIdx, sectionIdx)
        
        removedOverhead = 0
        for jobIdx in removedJobs:
            removedOverhead += calculateJobOverhead(content, jobIdx)
        
        for jobIdx, sectionIdx in removedSections:
            oldJobSections = [s for j, s in accountedSections if j == jobIdx]
            isFirstInJob = sectionIdx == min(oldJobSections) if oldJobSections else False
            removedOverhead += calculateSectionOverhead(content, jobIdx, sectionIdx, isFirstInJob)
            removedOverhead += estimateKeywordsHeight(content, jobIdx, sectionIdx)
            removedOverhead += estimateLinksHeight(content, jobIdx, sectionIdx)
        
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
            curCapacity -= netOverheadChange
        
        accountedJobs = distinctJobs.copy()
        accountedSections = distinctSections.copy()

        if abs(netOverheadChange) <= 1:
            break

    keepers = [targets[i] for i, picked in enumerate(chosen) if picked]
    keepersHeight = sum([k.lineHeight for k in keepers])
    
    keepersOverheadHeight = 0
    for jobIdx in accountedJobs:
        keepersOverheadHeight += calculateJobOverhead(content, jobIdx)
    
    for jobIdx, sectionIdx in accountedSections:
        jobSections = [s for j, s in accountedSections if j == jobIdx]
        isFirstInJob = sectionIdx == min(jobSections)
        keepersOverheadHeight += calculateSectionOverhead(content, jobIdx, sectionIdx, isFirstInJob)
    
    usedSpace = keepersHeight + keepersOverheadHeight

    return keepers, usedSpace, accountedJobs, accountedSections

def pruneKeywords(content: dict, items: list[ProcessedItem], similarities: list[float], sections: set) -> tuple[list[ProcessedItem], int]:
    keywords = [item for item in items if item.itemType == ItemType.KEYWORD]
    if not keywords:
        return [], 0

    seperator = ", "
    seperatorWeight = FONT_METRICS.getWidth(seperator, FontSize.REGULAR)

    keepers = []
    keepersHeight = 0
    
    for jobIdx, sectionIdx in sections:
        sectionKeywords = [k for k in keywords if k.metadata['jobIndex'] == jobIdx and k.metadata['sectionIndex'] == sectionIdx]
        if not sectionKeywords:
            continue
            
        validationText = [k.text for k in sectionKeywords]
        
        skValues = [similarities[sk.index] for sk in sectionKeywords]
        skWeights = [sk.lineWidth for sk in sectionKeywords]
        
        dummyLine = LINE_GENERATOR.generateKeywordsLine(validationText, jobIdx, sectionIdx)
        maxWidth = FONT_METRICS.maxWidth
        headerWidth = FONT_METRICS.getWidth("Technologies Used: ", FontSize.REGULAR)
        
        capacity = maxWidth * SPACE_INFO.keywordLinesPerSection - headerWidth - (len(sectionKeywords) - 1) * seperatorWeight
        
        if capacity <= 0:
            continue

        chosen = knapsack(skValues, skWeights, capacity)

        keepersText = []
        for i, picked in enumerate(chosen):
            if picked:
                keepers.append(sectionKeywords[i])
                keepersText.append(validationText[i])
        
        if keepersText:
            finalLine = LINE_GENERATOR.generateKeywordsLine(keepersText, jobIdx, sectionIdx)
            keepersHeight += LINE_GENERATOR.calculateHeight(finalLine)

    return keepers, keepersHeight

def pruneSkills(items: list[ProcessedItem], similarities: list[float]) -> tuple[list[ProcessedItem], int]:
    skills = [item for item in items if item.itemType == ItemType.SKILL]
    if not skills:
        return [], 0

    seperator = ", "
    seperatorWeight = FONT_METRICS.getWidth(seperator, FontSize.REGULAR)
    constWeight = FONT_METRICS.maxWidth * SPACE_INFO.skillsLineCount

    keepers = []
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
    
    keepersHeight = 0
    if keepersText:
        finalLine = LINE_GENERATOR.generateSkillsContent(keepersText)
        keepersHeight = LINE_GENERATOR.calculateHeight(finalLine)

    return keepers, keepersHeight

def rank(content: dict, jobPosting: str):
    heightRemaining = getRequiredLineWeights(content) - SPACE_INFO.skillReserve

    if (heightRemaining <= 0):
        print("The required content takes up all the space!")
        exit()

    batchIn, processedItems = makeBatch(content, jobPosting)

    print("Encoding data... this may take a while.")
    embeddings = encode(batchIn)
    similarities = analyze(processedItems, embeddings)

    points, pointsSpace, jobs, sections = prunePoints(content, processedItems, similarities, heightRemaining)
    heightRemaining -= pointsSpace
    
    print(f"Height Remaining Inches: {heightRemaining}")

    keywords, keywordsHeight = pruneKeywords(content, processedItems, similarities, sections)
    print(f"Keyword Height: {keywordsHeight}")

    heightRemaining -= keywordsHeight
    print(f"Height Remaining: {heightRemaining}")
    
    heightRemaining += SPACE_INFO.skillReserve

    skills, skillsHeight = pruneSkills(processedItems, similarities)
    print(f"Skills Height: {skillsHeight}")
    
    heightRemaining -= skillsHeight
    print(f"Remaining Height: {heightRemaining}")

    return points, keywords, skills, jobs, sections
