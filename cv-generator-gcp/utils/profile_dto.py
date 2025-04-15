from typing import Dict, Any, Optional
from pydantic import BaseModel, Field

class Profile(BaseModel):
    """
    Pydantic model for profile configuration.
    """
    schema_file: str = Field(..., alias="schema")
    template: str
    agency_name: Optional[str] = None
    agency_logo: Optional[str] = None
    default_section_visibility: Optional[Dict[str, bool]] = None
    default_section_order: Optional[Dict[str, Any]] = None

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "schema": "cv_schema.json",
                    "template": "template_WIP.docx",
                    "agency_name": "Hireable Recruiting",
                    "agency_logo": "agency_logo.png" 
                }
            ]
        },
        "populate_by_name": True
    }

def map_to_dto(data: dict) -> Profile:
    """
    Maps a dictionary to a Profile Pydantic model.
    
    Args:
        data (dict): The data to map.
        
    Returns:
        Profile: The mapped Profile object.
    """
    return Profile.model_validate(data) 