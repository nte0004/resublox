#! /usr/bin/env/python3
import argparse
import os
import src.validator as validator
import src.ranker as ranker
import src.format as formatter
from src.core import ProcessedItem

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
                        prog='python3 resublox',
                        description='Generate optimized resume',
                        )

    parser.add_argument("resume", help="Path to your resume template. See template.example.yaml")
    parser.add_argument("target", help="The content for which the resume will be optimized (in quotes \"like this\").")

    args = parser.parse_args()

    resumePath = args.resume
    if not os.path.exists(resumePath):
        print(f"Error: The supplied path to your resume template was not found. Path: {resumePath}")
        exit(1)

    if not os.path.isfile(resumePath):
        print(f"Error: The supplied path to your resume template was found, but it is not a file. Path: {resumePath}")
        exit(1)

    target = args.target

    resumeContent = validator.validate(resumePath)
    if resumeContent is None:
        print("Failed to load and validate YAML file")
        exit(1)

    # HACK: Not built to work with Pydantic Model right now. Only dicts
    content = resumeContent.model_dump()
    points, keywords, skills, usedJobs, usedSections = ranker.rank(content, target)

    jobs = content['experience']['jobs']
    jobs[:] = [jobs[i] for i in sorted(usedJobs)]

    # OPTIMIZE: There's gotta be a better way.
    for i, job in enumerate(jobs):
        sections = job['sections']
        jobPoints = [p for p in points if p.metadata['jobIndex'] == i]
        jobKeywords = [k for k in keywords if k.metadata['jobIndex'] == i]
        for j, section in enumerate(sections):
            sectionIndices = [jp.metadata['pointIndex'] for jp in jobPoints if jp.metadata['sectionIndex'] == j]
            keywordIndices = [jk.metadata['keywordIndex'] for jk in jobKeywords if jk.metadata['sectionIndex'] == j]
            section['points'][:] = [section['points'][k] for k in sorted(sectionIndices)]
            section['keywords'][:] = [section['keywords'][l] for l in sorted(keywordIndices)]

    content['skills']['list'][:] = [content['skills']['list'][m] for m in sorted([s.index for s in skills])]
    
    formatter.output(content)
    
