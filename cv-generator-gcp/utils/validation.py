import json
import logging
from jsonschema import validate
from jsonschema.exceptions import ValidationError
import os
from typing import Dict, Any, Optional, Union
from pydantic import ValidationError as PydanticValidationError

from models.schema import CVGenerationRequest

class Validation:
    """
    Validation class for validating request data against schema using Pydantic.
    """
    def __init__(self):
        """Initialize the validation class"""
        pass
    
    def validate_request(self, request: Dict[str, Any], cv_schema: Optional[Dict[str, Any]] = None) -> bool:
        """
        Validate the request data using Pydantic models.
        
        Args:
            request (Dict[str, Any]): The request data to validate.
            cv_schema (Dict[str, Any], optional): Legacy CV schema for backward compatibility.
            
        Returns:
            bool: True if validation succeeded, False otherwise.
        """
        try:
            # Convert legacy keys to snake_case for Pydantic model
            request_copy = self._transform_request_keys(request)
            
            # Validate using Pydantic model
            validated_data = CVGenerationRequest.model_validate(request_copy)
            return True
        except PydanticValidationError as e:
            # Log detailed validation errors
            for error in e.errors():
                logging.error(f"Validation error: {error['msg']} at {'.'.join(str(loc) for loc in error['loc'])}")
            return False
        except Exception as e:
            logging.error(f"Unexpected validation error: {str(e)}")
            return False
    
    def _transform_request_keys(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform camelCase keys to snake_case for Pydantic validation.
        
        Args:
            request (Dict[str, Any]): The request with camelCase keys.
            
        Returns:
            Dict[str, Any]: The request with snake_case keys.
        """
        transformed = {}
        
        # Map known camelCase keys to snake_case
        key_mapping = {
            "outputFormat": "output_format",
            "sectionOrder": "section_order",
            "sectionVisibility": "section_visibility",
            "isAnonymized": "is_anonymized",
            "recruiterProfile": "recruiter_profile",
            "firstName": "first_name",
            "lastName": "last_name",
            "profileStatement": "profile_statement",
            "endDate": "end_date",
            "startDate": "start_date",
            "additionalDetails": "additional_details",
            "professionalMemberships": "professional_memberships",
            "earlierCareer": "earlier_career"
        }
        
        # Process top-level keys
        for key, value in request.items():
            new_key = key_mapping.get(key, key)
            
            # Handle nested dictionaries
            if isinstance(value, dict):
                transformed[new_key] = self._transform_request_keys(value)
            # Handle lists of dictionaries
            elif isinstance(value, list) and all(isinstance(item, dict) for item in value):
                transformed[new_key] = [self._transform_request_keys(item) for item in value]
            else:
                transformed[new_key] = value
        
        return transformed 