import yaml
import sys
from pathlib import Path
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
class Models:
    SMALL = './models/all-MiniLM-L6-v2'
    MEDIUM = './models/all-MiniLM-L12-v2'
    LARGE = './models/all-mpnet-base-v2'

MODEL = Models.SMALL
TEMPLATE_PATH='template.example.yaml'

# TODO: Take user input of job posting
JOB_POSTING = """
TechFlow Solutions is a fast-growing fintech startup revolutionizing how small businesses manage their cash flow. We're backed by top-tier VCs and serving over 10,000 customers across North America. Join our mission to democratize financial tools for entrepreneurs everywhere. We're seeking a Senior Software Engineer to join our core platform team. You'll work on high-impact features that directly serve our customers, from building intuitive dashboards to architecting scalable backend systems. This is a chance to wear multiple hats and make a real difference in a collaborative, fast-paced environment. Design and implement full-stack features using React, Node.js, and PostgreSQL. Collaborate with product managers and designers to translate requirements into elegant solutions. Write clean, testable code and participate in code reviews. Optimize application performance and ensure scalability. Mentor junior developers and contribute to technical decision-making. Work with our DevOps team to maintain CI/CD pipelines and AWS infrastructure. 4+ years of software development experience. Strong proficiency in JavaScript/TypeScript and modern React. Experience with Node.js and RESTful API design. Familiarity with SQL databases (PostgreSQL preferred). Understanding of version control (Git) and agile development practices. Excellent communication skills and collaborative mindset. Experience with AWS services (EC2, RDS, Lambda). Knowledge of Docker and containerization. Background in fintech or financial services. Experience with testing frameworks (Jest, Cypress). Familiarity with GraphQL.
"""

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

def makeBatch(content):
    batchIn = []
    batchMap = {'skills': None, 'jobs': [], 'jobPosting': None}
    rootIdx = 0

    skills = content['skills']['list']
    if (skills):
        skillsStart = rootIdx
        for s in skills:
            batchIn.append(s)
            rootIdx += 1

        skillsEnd = rootIdx - 1

        batchMap['skills'] = {'start': skillsStart, 'end': skillsEnd}

    e = content['experience']
    jobs = e['jobs']
    for j in jobs:
        sections = j['sections']
        sectionsMap = []
        
        jobStart = rootIdx
        
        for s in sections:
            sectionStart = rootIdx
            points = s['points']
            
            for p in points:
                batchIn.append(p)
                rootIdx += 1

            sectionEnd = rootIdx - 1

            keywordsStart = rootIdx
            keywords = s['keywords']
            
            for k in keywords:
                batchIn.append(k)
                rootIdx += 1

            keywordsEnd = rootIdx - 1

            composite = ' '.join(points + keywords)
            batchIn.append(composite)
            compositeIdx = rootIdx
            
            rootIdx += 1

            sectionsMap.append({
                'start': sectionStart,
                'end': sectionEnd, 
                'keywords': {'start': keywordsStart, 'end': keywordsEnd},
                'composite': compositeIdx})

        jobEnd = rootIdx - 1
        batchMap['jobs'].append({'start': jobStart, 'end': jobEnd, 'sections': sectionsMap})

    batchIn.append(JOB_POSTING)
    batchMap['jobPosting'] = {'start': rootIdx, 'end': rootIdx}

    return batchIn, batchMap


def encode(batch):
    model = SentenceTransformer(MODEL)
    return model.encode(batch)

def analyze(batchMap, embeddings):
    results = {'skills': [], 'jobs': []}
    
    job_posting_idx = batchMap['jobPosting']['start']
    job_posting_embedding = embeddings[job_posting_idx].reshape(1, -1)

    skills_start = batchMap['skills']['start']
    skills_end = batchMap['skills']['end']
    skills_embeddings = embeddings[skills_start:skills_end+1]

    skills_similarities = cosine_similarity(skills_embeddings, job_posting_embedding).flatten()

    skills_results = []
    for i, _ in enumerate(range(skills_start, skills_end + 1)):
        skills_results.append({
            'skill_index': i,
            'similarity': float(skills_similarities[i]),
        })

    skills_results.sort(key=lambda x: x['similarity'], reverse=True)
    
    results['skills'] = skills_results

    for job_idx, job in enumerate(batchMap['jobs']):
        job_result = {
            'job_index': job_idx,
            'job_range': f"{job['start']}-{job['end']}",
            'sections': []
        }
        
        for section_idx, section in enumerate(job['sections']):
            section_start = section['start']
            section_end = section['end']
            section_embeddings = embeddings[section_start:section_end+1]
            
            composite_idx = section['composite']
            composite_embedding = embeddings[composite_idx].reshape(1, -1)
            
            keywords_similarities = []
            keywords_results = []
            if 'keywords' in section:
                keywords_start = section['keywords']['start']
                keywords_end = section['keywords']['end']
                keywords_embeddings = embeddings[keywords_start:keywords_end+1]
                keywords_similarities = cosine_similarity(keywords_embeddings, job_posting_embedding).flatten()
                
                for i, _ in enumerate(range(keywords_start, keywords_end + 1)):
                    keywords_results.append({
                        'keyword_index': i,
                        'similarity': float(keywords_similarities[i]),
                    })
                
                keywords_results.sort(key=lambda x: x['similarity'], reverse=True)
            
            section_similarities = cosine_similarity(section_embeddings, job_posting_embedding).flatten()
            composite_similarity = cosine_similarity(composite_embedding, job_posting_embedding)[0][0]
            
            section_result = {
                'section_index': section_idx,
                'composite_similarity': float(composite_similarity),
                'keywords': keywords_results,
                'points': []
            }
            
            for i, _ in enumerate(range(section_start, section_end + 1)):
                section_result['points'].append({
                    'point_index': i,
                    'similarity': float(section_similarities[i]),
                })
            
            section_result['points'].sort(key=lambda x: x['similarity'], reverse=True)
            
            job_result['sections'].append(section_result)
        
        # Keep Sections in inputted order
        results['jobs'].append(job_result)

    return results

if __name__ == "__main__":
    content = loadYAML(TEMPLATE_PATH)

    if content is None:
        exit()
    elif not content:
        print(f"YAML loaded, but there was nothing to work with. Exiting")
        exit()

    # TODO: Something to validate the YAML structure that must exist, does exist.
    batchIn, batchMap = makeBatch(content)

    print("Encoding data... this may take a while.")
    embeddings = encode(batchIn)

    analysis = analyze(batchMap, embeddings)

    # TODO: Reformat content based on analysis, then pass to main.py
