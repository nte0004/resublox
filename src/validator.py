from pydantic import BaseModel, Field, field_validator, model_validator
from typing import List, Optional
import yaml
from pathlib import Path

class Link(BaseModel):
    descriptor: str = Field(..., min_length=1, description="Link description")
    url: str = Field(..., min_length=1, description="URL")
    alias: Optional[str] = Field(None, description="Optional, display text of url")

class Contact(BaseModel):
    name: str = Field(..., min_length=1, description="Full name")
    contactInformation: Optional[List[Link]] = Field(None, description="Email, phone links")
    location: Optional[str] = Field(None, min_length=1, description="Optional, Location")
    links: Optional[List[Link]] = Field(None, description="Optional, more links")

class Skills(BaseModel):
    title: str = Field(..., min_length=1, description="Skills section title")
    list: List[str] = Field(..., min_length=1, description="List of technical skills")
    
    @field_validator('list')
    @classmethod
    def validate_skills_not_empty(cls, v):
        if not v or all(not skill.strip() for skill in v):
            raise ValueError('Skills list cannot be empty or contain only whitespace')
        return [skill.strip() for skill in v]

class Section(BaseModel):
    title: str = Field(..., min_length=1, description="Section title")
    keywords: List[str] = Field(..., min_length=1, description="Technology keywords")
    points: List[str] = Field(..., min_length=1, description="Achievement/responsibility points")
    links: Optional[List[Link]] = Field(None, description="Optional, project links")
    
    @field_validator('keywords', 'points')
    @classmethod
    def validate_non_empty_strings(cls, v):
        if not v or all(not item.strip() for item in v):
            raise ValueError('List cannot be empty or contain only whitespace')
        return [item.strip() for item in v]

class Job(BaseModel):
    role: str = Field(..., min_length=1, description="Job title/role")
    company: Optional[str] = Field(None, min_length=1, description="Optional, Company name")
    location: str = Field(..., min_length=1, description="Job location")
    from_date: str = Field(..., alias='from', description="Start date")
    to_date: str = Field(..., alias='to', description="End date")
    sections: List[Section] = Field(..., min_length=1, description="Job experience sections")

class Experience(BaseModel):
    title: str = Field(..., min_length=1, description="Experience section title")
    jobs: List[Job] = Field(..., min_length=1, description="List of work experiences")

class Graduation(BaseModel):
    on: str = Field(..., alias='on', description="Graduation date")
    hasGraduated: bool = Field(..., description="Whether already graduated")

class Education(BaseModel):
    title: str = Field(..., min_length=1, description="Education section title")
    school: str = Field(..., min_length=1, description="School name")
    location: str = Field(..., min_length=1, description="School location")
    degree: str = Field(..., min_length=1, description="Degree type")
    major: str = Field(..., min_length=1, description="Major field of study")
    concentration: Optional[str] = Field(None, min_length=1, description="Optional, concentration")
    graduation: Graduation = Field(..., description="Graduation information")
    gpa: Optional[str] = Field(None, min_length=1, description="Optional, GPA")
    honors: List[str] = Field(default_factory=list, description="Academic honors")
    courses: List[str] = Field(default_factory=list, description="Relevant courses")

class Projects(BaseModel):
    title: str = Field(..., min_length=1, description="Projects section title")
    projects: List[Section] = Field(..., min_length=0, description="List of projects")

class ResumeData(BaseModel):
    contact: Contact = Field(..., description="Contact information")
    skills: Skills = Field(..., description="Technical skills")
    experience: Experience = Field(..., description="Work experience")
    projects: Optional[Projects] = Field(None, description="Optional, Projects")
    education: Education = Field(..., description="Education information")
    
    @model_validator(mode='after')
    def checkExperienceOrProjects(self):
        if self.experience is None and self.projects is None:
            raise ValueError('Must have experience and/or project section(s). Neither found.')
        return self

    class Config:
        # Allow field aliases (like 'from' -> 'from_date')
        validate_by_name = True
        # Validate assignment to catch issues early
        validate_assignment = True

def load_and_validate_yaml(yaml_path: str) -> Optional[ResumeData]:
    """
    Load and validate a resume YAML file.
    
    Args:
        yaml_path: Path to the YAML file
        
    Returns:
        Validated ResumeData object or None if validation fails
    """
    try:
        if not Path(yaml_path).exists():
            raise FileNotFoundError(f"YAML file not found: {yaml_path}")
        
        with open(yaml_path, 'r', encoding='utf-8') as file:
            raw_data = yaml.safe_load(file)
        
        if raw_data is None:
            raise ValueError("YAML file is empty")
        
        # Validate the data structure
        validated_data = ResumeData(**raw_data)
        return validated_data
        
    except FileNotFoundError as e:
        print(f"File Error: {e}")
        return None
    except yaml.YAMLError as e:
        print(f"YAML Parsing Error: {e}")
        return None
    except Exception as e:
        print(f"Validation Error: {e}")
        if hasattr(e, 'errors'):
            for error in e.errors():
                location = " -> ".join(str(loc) for loc in error['loc'])
                print(f"   Field '{location}': {error['msg']}")
        return None

def validate(path: str) -> ResumeData | None:
    resume_data = load_and_validate_yaml(path)
    return resume_data
