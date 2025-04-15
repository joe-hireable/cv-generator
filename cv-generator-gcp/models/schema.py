from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field

class RecruiterProfile(BaseModel):
    """
    Recruiter and agency information for CV branding
    """
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    agency_name: Optional[str] = None
    agency_logo: Optional[str] = None
    website: Optional[str] = None

class PersonalInfo(BaseModel):
    """
    Personal information for the CV
    """
    first_name: str
    surname: str
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    linkedin: Optional[str] = None
    website: Optional[str] = None
    profile_statement: Optional[str] = None

class Experience(BaseModel):
    """
    Work experience entry
    """
    role: str
    company: str
    start_date: str
    end_date: Optional[str] = None
    current: Optional[bool] = False
    description: Optional[str] = None
    achievements: Optional[List[str]] = None

class Education(BaseModel):
    """
    Education entry
    """
    institution: str
    degree: str
    field: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    grade: Optional[str] = None
    description: Optional[str] = None

class Certification(BaseModel):
    """
    Professional certification
    """
    name: str
    issuer: Optional[str] = None
    date: Optional[str] = None
    description: Optional[str] = None

class Achievement(BaseModel):
    """
    Professional achievement
    """
    title: str
    description: Optional[str] = None
    date: Optional[str] = None

class Language(BaseModel):
    """
    Language proficiency
    """
    language: str
    proficiency: Optional[str] = None

class ProfessionalMembership(BaseModel):
    """
    Professional organization membership
    """
    organization: str
    role: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None

class EarlierCareer(BaseModel):
    """
    Earlier career positions (summarized)
    """
    role: str
    company: Optional[str] = None
    period: Optional[str] = None
    description: Optional[str] = None

class Publication(BaseModel):
    """
    Published work
    """
    title: str
    publisher: Optional[str] = None
    date: Optional[str] = None
    url: Optional[str] = None
    description: Optional[str] = None

class CVData(BaseModel):
    """
    All CV data to be rendered in the template
    """
    first_name: str
    surname: str
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    linkedin: Optional[str] = None
    website: Optional[str] = None
    profile_statement: Optional[str] = None
    
    experience: Optional[List[Experience]] = None
    education: Optional[List[Education]] = None
    skills: Optional[List[str]] = None
    certifications: Optional[List[Certification]] = None
    achievements: Optional[List[Achievement]] = None
    languages: Optional[List[Language]] = None
    professional_memberships: Optional[List[ProfessionalMembership]] = None
    earlier_career: Optional[List[EarlierCareer]] = None
    publications: Optional[List[Publication]] = None
    additional_details: Optional[List[str]] = None

class SectionVisibility(BaseModel):
    """
    Controls which sections of the CV are visible
    """
    personal_info: Optional[bool] = True
    profile_statement: Optional[bool] = True
    skills: Optional[bool] = True
    experience: Optional[bool] = True
    education: Optional[bool] = True
    certifications: Optional[bool] = True
    achievements: Optional[bool] = True
    languages: Optional[bool] = True
    professional_memberships: Optional[bool] = True
    earlier_career: Optional[bool] = True
    publications: Optional[bool] = True
    additional_details: Optional[bool] = True

class CVGenerationRequest(BaseModel):
    """
    Request model for CV generation
    """
    template: Optional[str] = None
    output_format: Optional[str] = Field(None, pattern="^(doc|docx|pdf)$")
    section_order: Optional[List[str]] = None
    section_visibility: Optional[SectionVisibility] = None
    is_anonymized: Optional[bool] = False
    recruiter_profile: Optional[RecruiterProfile] = None
    data: CVData
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "template": "template_WIP.docx",
                    "output_format": "pdf",
                    "is_anonymized": False,
                    "data": {
                        "first_name": "John",
                        "surname": "Doe",
                        "email": "john.doe@example.com",
                        "profile_statement": "Experienced software developer with 10+ years of experience."
                    }
                }
            ]
        }
    } 