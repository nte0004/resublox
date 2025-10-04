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
    
    optimizedContent = ranker.rank(content, target)
    
    formatter.output(optimizedContent)
    
