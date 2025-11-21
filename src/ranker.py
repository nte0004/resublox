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
        for sIdx, s in enumerate(skills):
            lineSpec = LINE_GENERATOR.generateSkillsContent([s])
            lineWidth = FONT_METRICS.getWidth(s, FontSize.REGULAR)
            batchIn.append(s)
            processedItems.append(ProcessedItem(
                text = s,
                index = rootIdx,
                lineHeight = 0,
                lineWidth = lineWidth,
                itemType = ItemType.SKILL,
                metadata = {
                    'skillIndex': sIdx
                }
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

    courses = content['education']['courses']
    if courses:
        for cIdx, c in enumerate(courses):
            lineWidth = FONT_METRICS.getWidth(c, FontSize.REGULAR)
            batchIn.append(c)
            processedItems.append(ProcessedItem(
                text = c,
                index = rootIdx,
                lineHeight = 0,
                lineWidth = lineWidth,
                itemType = ItemType.COURSE,
                metadata = {
                    'courseIndex': cIdx
                }
            ))
            rootIdx += 1
    
    # Add project points if projects exist
    if 'projects' in content and content['projects'] is not None:
        projects = content['projects']['projects']
        for pIdx, proj in enumerate(projects):
            for ppIdx, pp in enumerate(proj['points']):
                lineSpec = LINE_GENERATOR.generateProjectPointLine(pp, pIdx, ppIdx)
                lineHeight = LINE_GENERATOR.calculateHeight(lineSpec)
                batchIn.append(pp)
                processedItems.append(ProcessedItem(
                    text = pp,
                    index = rootIdx,
                    lineHeight = lineHeight,
                    lineWidth = 0,
                    itemType = ItemType.PROJECT_POINT,
                    metadata = {
                        'projectIndex': pIdx,
                        'pointIndex': ppIdx
                    }
                ))
                rootIdx += 1
            
            for kIdx, k in enumerate(proj['keywords']):
                lineWidth = FONT_METRICS.getWidth(k, FontSize.REGULAR)
                batchIn.append(k)
                processedItems.append(ProcessedItem(
                    text = k,
                    index = rootIdx,
                    lineHeight = 0,
                    lineWidth = lineWidth,
                    itemType = ItemType.KEYWORD,
                    metadata = {
                        'projectIndex': pIdx,
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
    remainingHeight = max(SPACE_INFO.maxHeight - totalHeight, 0)
    return remainingHeight

def encode(batch: list[str]):
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer(MODEL)
    return model.encode(batch, show_progress_bar=True)

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

def calculateProjectOverhead(content: dict, projectIndex: int) -> int:
    project = content['projects']['projects'][projectIndex]
    projectHeaderLines = LINE_GENERATOR.generateProjectHeader(project, projectIndex)
    return LINE_GENERATOR.calculateTotalHeight(projectHeaderLines)

def estimateProjectKeywordsHeight(content: dict, projectIdx: int) -> int:
    project = content['projects']['projects'][projectIdx]
    if 'keywords' not in project or not project['keywords']:
        return 0
    dummyLine = LINE_GENERATOR.generateProjectKeywordsLine(project['keywords'], projectIdx)
    return LINE_GENERATOR.calculateHeight(dummyLine)

def estimateProjectLinksHeight(content: dict, projectIdx: int) -> int:
    project = content['projects']['projects'][projectIdx]
    if 'links' not in project or not project['links']:
        return 0
    dummyLine = LINE_GENERATOR.generateProjectLinksLine(project['links'], projectIdx)
    return LINE_GENERATOR.calculateHeight(dummyLine)

def prunePoints(content: dict, items: list[ProcessedItem], similarities: list[float], heightRemaining: int) -> tuple[list[ProcessedItem], list[ProcessedItem], int, set, set, set]:
    
    BLACKLIST_WEIGHT = SPACE_INFO.maxHeight + 1

    def iterate(_capacity, _targetValues, _targetWeights):
        if _capacity <= 0:
            return [False] * len(_targetValues)

        if all(tw == _targetWeights[0] for tw in _targetWeights):
            maxItems = _capacity // _targetWeights[0]
            sortedTargets = sorted(range(len(_targetValues)), key = lambda i: _targetValues[i], reverse = True)
            chosen = [False] * len(_targetValues)
            for i in sortedTargets[:maxItems]:
                chosen[i] = True
        else:
            chosen = knapsack(_targetValues, _targetWeights, _capacity)

        return chosen

    # Separate experience points and project points
    expPoints = [item for item in items if item.itemType == ItemType.POINT]
    projPoints = [item for item in items if item.itemType == ItemType.PROJECT_POINT]
    
    # Combine both types with weighted values for project points
    allPoints = expPoints + projPoints
    allValues = []
    allWeights = []
    
    for item in expPoints:
        allValues.append(similarities[item.index])
        allWeights.append(item.lineHeight)
    
    for item in projPoints:
        # Apply project weighting (85% as valuable as experience)
        allValues.append(similarities[item.index] * SPACE_INFO.projectToExperienceRatio)
        allWeights.append(item.lineHeight)
    
    capacity = heightRemaining
    chosen = []
    accountedJobs = set()
    accountedSections = set()
    accountedProjects = set()
    curCapacity = capacity
    iteration = 0
    maxIterations = 10 
    
    while iteration < maxIterations:
        iteration += 1
        chosen = iterate(curCapacity, allValues, allWeights)

        sectionPointIndices = {}
        projectPointIndices = {}
        
        for i, picked in enumerate(chosen):
            if picked:
                item = allPoints[i]
                if item.itemType == ItemType.POINT:
                    sectionKey = (item.metadata['jobIndex'], item.metadata['sectionIndex'])
                    if sectionKey not in sectionPointIndices:
                        sectionPointIndices[sectionKey] = []
                    sectionPointIndices[sectionKey].append(i)
                elif item.itemType == ItemType.PROJECT_POINT:
                    projectIdx = item.metadata['projectIndex']
                    if projectIdx not in projectPointIndices:
                        projectPointIndices[projectIdx] = []
                    projectPointIndices[projectIdx].append(i)

        # Remove sections with too few points
        sectionsToRemove = {
            sectionKey for sectionKey, indices in sectionPointIndices.items()
            if len(indices) < SPACE_INFO.minPointsPerSection
        }
        
        # Remove projects with too few points
        projectsToRemove = {
            projectIdx for projectIdx, indices in projectPointIndices.items()
            if len(indices) < SPACE_INFO.minPointsPerSection
        }

        if sectionsToRemove:
            for sectionKey in sectionsToRemove:
                for idx in sectionPointIndices[sectionKey]:
                    chosen[idx] = False
                    allWeights[idx] = BLACKLIST_WEIGHT
                del sectionPointIndices[sectionKey]
        
        if projectsToRemove:
            for projectIdx in projectsToRemove:
                for idx in projectPointIndices[projectIdx]:
                    chosen[idx] = False
                    allWeights[idx] = BLACKLIST_WEIGHT
                del projectPointIndices[projectIdx]

        distinctJobs, distinctSections = set(), set()
        for sectionKey in sectionPointIndices.keys():
            jobIdx, sectionIdx = sectionKey
            distinctJobs.add(jobIdx)
            distinctSections.add((jobIdx, sectionIdx))
        
        distinctProjects = set(projectPointIndices.keys())

        newJobs = distinctJobs - accountedJobs
        removedJobs = accountedJobs - distinctJobs
        newSections = distinctSections - accountedSections
        removedSections = accountedSections - distinctSections
        newProjects = distinctProjects - accountedProjects
        removedProjects = accountedProjects - distinctProjects

        newOverhead = 0
        for jobIdx in newJobs:
            newOverhead += calculateJobOverhead(content, jobIdx)
        
        for jobIdx, sectionIdx in newSections:
            jobSections = [s for j, s in distinctSections if j == jobIdx]
            isFirstInJob = sectionIdx == min(jobSections)
            newOverhead += calculateSectionOverhead(content, jobIdx, sectionIdx, isFirstInJob)
            newOverhead += estimateKeywordsHeight(content, jobIdx, sectionIdx)
            newOverhead += estimateLinksHeight(content, jobIdx, sectionIdx)
        
        # Add project overhead
        if 'projects' in content and content['projects'] is not None:
            for projectIdx in newProjects:
                newOverhead += calculateProjectOverhead(content, projectIdx)
                newOverhead += estimateProjectKeywordsHeight(content, projectIdx)
                newOverhead += estimateProjectLinksHeight(content, projectIdx)
        
        removedOverhead = 0
        for jobIdx in removedJobs:
            removedOverhead += calculateJobOverhead(content, jobIdx)
        
        for jobIdx, sectionIdx in removedSections:
            oldJobSections = [s for j, s in accountedSections if j == jobIdx]
            isFirstInJob = sectionIdx == min(oldJobSections) if oldJobSections else False
            removedOverhead += calculateSectionOverhead(content, jobIdx, sectionIdx, isFirstInJob)
            removedOverhead += estimateKeywordsHeight(content, jobIdx, sectionIdx)
            removedOverhead += estimateLinksHeight(content, jobIdx, sectionIdx)
        
        # Remove project overhead
        if 'projects' in content and content['projects'] is not None:
            for projectIdx in removedProjects:
                removedOverhead += calculateProjectOverhead(content, projectIdx)
                removedOverhead += estimateProjectKeywordsHeight(content, projectIdx)
                removedOverhead += estimateProjectLinksHeight(content, projectIdx)
        
        netOverheadChange = newOverhead - removedOverhead
       
        if netOverheadChange == 0:
            break
        elif netOverheadChange > 0:
            curCapacity -= netOverheadChange
            if curCapacity <= 0:
                chosen = [False] * len(allPoints)
                distinctJobs, distinctSections, distinctProjects = set(), set(), set()
                break
        else:
            curCapacity -= netOverheadChange
        
        accountedJobs = distinctJobs.copy()
        accountedSections = distinctSections.copy()
        accountedProjects = distinctProjects.copy()

        if abs(netOverheadChange) <= 1:
            break

    expKeepers = []
    projKeepers = []
    for i, picked in enumerate(chosen):
        if picked:
            if allPoints[i].itemType == ItemType.POINT:
                expKeepers.append(allPoints[i])
            elif allPoints[i].itemType == ItemType.PROJECT_POINT:
                projKeepers.append(allPoints[i])
    
    keepersHeight = sum([k.lineHeight for k in expKeepers]) + sum([k.lineHeight for k in projKeepers])
    
    keepersOverheadHeight = 0
    for jobIdx in accountedJobs:
        keepersOverheadHeight += calculateJobOverhead(content, jobIdx)
    
    for jobIdx, sectionIdx in accountedSections:
        jobSections = [s for j, s in accountedSections if j == jobIdx]
        isFirstInJob = sectionIdx == min(jobSections)
        keepersOverheadHeight += calculateSectionOverhead(content, jobIdx, sectionIdx, isFirstInJob)
    
    if 'projects' in content and content['projects'] is not None:
        for projectIdx in accountedProjects:
            keepersOverheadHeight += calculateProjectOverhead(content, projectIdx)
    
    usedSpace = keepersHeight + keepersOverheadHeight

    return expKeepers, projKeepers, usedSpace, accountedJobs, accountedSections, accountedProjects

def pruneKeywords(content: dict, items: list[ProcessedItem], similarities: list[float], sections: set, projects: set) -> tuple[list[ProcessedItem], int]:
    keywords = [item for item in items if item.itemType == ItemType.KEYWORD]
    if not keywords:
        return [], 0

    separator = ", "
    separatorWeight = FONT_METRICS.getWidth(separator, FontSize.REGULAR)

    keepers = []
    keepersHeight = 0
    
    # Process section keywords (for experience)
    for jobIdx, sectionIdx in sections:
        sectionKeywords = [k for k in keywords if 'jobIndex' in k.metadata and k.metadata['jobIndex'] == jobIdx and k.metadata['sectionIndex'] == sectionIdx]
        if not sectionKeywords:
            continue
            
        validationText = [k.text for k in sectionKeywords]
        
        skValues = [similarities[sk.index] for sk in sectionKeywords]
        skWeights = [sk.lineWidth for sk in sectionKeywords]
        
        dummyLine = LINE_GENERATOR.generateKeywordsLine(validationText, jobIdx, sectionIdx)
        maxWidth = FONT_METRICS.maxWidth
        # TODO: Let Technologies used be a descriptor decided by the user in the template or core.py
        headerWidth = FONT_METRICS.getWidth("Technologies Used: ", FontSize.REGULAR)
        
        capacity = maxWidth * SPACE_INFO.keywordLinesPerSection - headerWidth - (len(sectionKeywords) - 1) * separatorWeight
        
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
    
    # Process project keywords
    for projectIdx in projects:
        projectKeywords = [k for k in keywords if 'projectIndex' in k.metadata and k.metadata['projectIndex'] == projectIdx]
        if not projectKeywords:
            continue
            
        validationText = [k.text for k in projectKeywords]
        
        pkValues = [similarities[pk.index] for pk in projectKeywords]
        pkWeights = [pk.lineWidth for pk in projectKeywords]
        
        dummyLine = LINE_GENERATOR.generateProjectKeywordsLine(validationText, projectIdx)
        maxWidth = FONT_METRICS.maxWidth
        headerWidth = FONT_METRICS.getWidth("Technologies Used: ", FontSize.REGULAR)
        
        capacity = maxWidth * SPACE_INFO.keywordLinesPerSection - headerWidth - (len(projectKeywords) - 1) * separatorWeight
        
        if capacity <= 0:
            continue

        chosen = knapsack(pkValues, pkWeights, capacity)

        keepersText = []
        for i, picked in enumerate(chosen):
            if picked:
                keepers.append(projectKeywords[i])
                keepersText.append(validationText[i])
        
        if keepersText:
            finalLine = LINE_GENERATOR.generateProjectKeywordsLine(keepersText, projectIdx)
            keepersHeight += LINE_GENERATOR.calculateHeight(finalLine)

    return keepers, keepersHeight

def pruneSkills(items: list[ProcessedItem], similarities: list[float]) -> tuple[list[ProcessedItem], int]:
    skills = [item for item in items if item.itemType == ItemType.SKILL]
    if not skills:
        return [], 0

    separator = ", "
    separatorWeight = FONT_METRICS.getWidth(separator, FontSize.REGULAR)
    constWeight = FONT_METRICS.maxWidth * SPACE_INFO.skillsLineCount

    keepers = []
    validationText = [s.text for s in skills]
    skillValues = [similarities[s.index] for s in skills]
    skillWeights = [s.lineWidth for s in skills]
    
    capacity = constWeight - (len(skills) - 1) * separatorWeight
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

def pruneCourses(items: list[ProcessedItem], similarities: list[float]) -> tuple[list[ProcessedItem], int]:
    courses = [item for item in items if item.itemType == ItemType.COURSE]
    if not courses:
        return [], 0

    separator = ", "
    separatorWeight = FONT_METRICS.getWidth(separator, FontSize.REGULAR)
    constWeight = FONT_METRICS.maxWidth * SPACE_INFO.coursesLineCount

    keepers = []
    validationText = [c.text for c in courses]
    courseValues = [similarities[c.index] for c in courses]
    courseWeights = [c.lineWidth for c in courses]
    
    # TODO: Derive Relevant Courses better.
    headerWidth = FONT_METRICS.getWidth("Relevant Courses: ", FontSize.REGULAR)
    capacity = constWeight - headerWidth - (len(courses) - 1) * separatorWeight
    
    if capacity <= 0:
        return [], 0

    chosen = knapsack(courseValues, courseWeights, capacity)

    keepersText = []
    for i, picked in enumerate(chosen):
        if picked:
            keepers.append(courses[i])
            keepersText.append(validationText[i])
    
    keepersHeight = 0
    if keepersText:
        finalLine = LINE_GENERATOR.generateCoursesLine(keepersText)
        keepersHeight = LINE_GENERATOR.calculateHeight(finalLine)

    return keepers, keepersHeight

def filter(content: dict, skills: list[ProcessedItem], courses: list[ProcessedItem],
           expPoints: list[ProcessedItem], projPoints: list[ProcessedItem], keywords: list[ProcessedItem],
           jobs: set, sections: set, projects: set) -> dict:

    '''
        Boils the dictionary (that was produced by the template) down to only the content that should be rendered.
    '''


    filteredContent = {
        'contact': content['contact'],
        'skills': content['skills'].copy(),
        'experience': content['experience'].copy(),
        'education': content['education'].copy()
    }
    
    # Filter skills
    skillIndices = sorted([s.metadata['skillIndex'] for s in skills])
    filteredContent['skills']['list'] = [
        content['skills']['list'][i] for i in skillIndices
    ]
    
    # Filter courses
    courseIndices = sorted([c.metadata['courseIndex'] for c in courses])
    filteredContent['education']['courses'] = [
        content['education']['courses'][i] for i in courseIndices
    ]
    
    # Filter jobs and their sections/points
    sortedJobIndices = sorted(jobs)
    filteredContent['experience']['jobs'] = []
    
    for oldJobIdx in sortedJobIndices:
        originalJob = content['experience']['jobs'][oldJobIdx]
        filteredJob = {
            'role': originalJob['role'],
            'company': originalJob['company'],
            'location': originalJob['location'],
            'from': originalJob.get('from', originalJob.get('from_date', '')),
            'to': originalJob.get('to', originalJob.get('to_date', '')),
            'sections': []
        }
        
        # Get sections for this job
        jobSections = sorted([s for (j, s) in sections if j == oldJobIdx])
        
        for oldSectionIdx in jobSections:
            originalSection = originalJob['sections'][oldSectionIdx]
            
            # Get points for this section
            sectionPoints = [
                p for p in expPoints 
                if p.metadata['jobIndex'] == oldJobIdx 
                and p.metadata['sectionIndex'] == oldSectionIdx
            ]
            pointIndices = sorted([p.metadata['pointIndex'] for p in sectionPoints])
            
            # Get keywords for this section
            sectionKeywords = [
                k for k in keywords
                if 'jobIndex' in k.metadata and k.metadata['jobIndex'] == oldJobIdx
                and k.metadata['sectionIndex'] == oldSectionIdx
            ]
            keywordIndices = sorted([k.metadata['keywordIndex'] for k in sectionKeywords])
            
            filteredSection = {
                'title': originalSection['title'],
                'points': [originalSection['points'][i] for i in pointIndices],
                'keywords': [originalSection['keywords'][i] for i in keywordIndices]
            }
            
            # Preserve links if they exist
            if 'links' in originalSection and originalSection['links']:
                filteredSection['links'] = originalSection['links']
            
            filteredJob['sections'].append(filteredSection)
        
        filteredContent['experience']['jobs'].append(filteredJob)
    
    # Filter projects if they exist
    if 'projects' in content and content['projects'] is not None and projects:
        sortedProjectIndices = sorted(projects)
        filteredContent['projects'] = {
            'title': content['projects']['title'],
            'projects': []
        }
        
        for oldProjectIdx in sortedProjectIndices:
            originalProject = content['projects']['projects'][oldProjectIdx]
            
            # Get points for this project
            projectPoints = [
                p for p in projPoints
                if p.metadata['projectIndex'] == oldProjectIdx
            ]
            pointIndices = sorted([p.metadata['pointIndex'] for p in projectPoints])
            
            # Get keywords for this project
            projectKeywords = [
                k for k in keywords
                if 'projectIndex' in k.metadata and k.metadata['projectIndex'] == oldProjectIdx
            ]
            keywordIndices = sorted([k.metadata['keywordIndex'] for k in projectKeywords])
            
            filteredProject = {
                'title': originalProject['title'],
                'keywords': [originalProject['keywords'][i] for i in keywordIndices],
                'points': [originalProject['points'][i] for i in pointIndices]
            }
            
            # Preserve links if they exist
            if 'links' in originalProject and originalProject['links']:
                filteredProject['links'] = originalProject['links']
            
            filteredContent['projects']['projects'].append(filteredProject)
    
    return filteredContent


def rank(content: dict, jobPosting: str):
    # Height allotted to skills and courses is removed now, guranteeing space later.
    heightRemaining = getRequiredLineWeights(content) - SPACE_INFO.skillReserve - SPACE_INFO.courseReserve

    if (heightRemaining <= 0):
        print("The required content takes up all the space!")
        exit()

    batchIn, processedItems = makeBatch(content, jobPosting)

    print("Encoding data... this may take a while.")
    embeddings = encode(batchIn)
    similarities = analyze(processedItems, embeddings)

    expPoints, projPoints, pointsSpace, jobs, sections, projects = prunePoints(content, processedItems, similarities, heightRemaining)
    heightRemaining -= pointsSpace
    
    keywords, keywordsHeight = pruneKeywords(content, processedItems, similarities, sections, projects)

    heightRemaining -= keywordsHeight
    
    # prunePoints and prunKeywords operate as if the skills and courses space if already filled.
    
    heightRemaining += SPACE_INFO.skillReserve + SPACE_INFO.courseReserve

    skills, skillsHeight = pruneSkills(processedItems, similarities)
    
    heightRemaining -= skillsHeight

    courses, coursesHeight = pruneCourses(processedItems, similarities)
    heightRemaining -= coursesHeight

    return filter(content, skills, courses, expPoints, projPoints, keywords, jobs, sections, projects)
