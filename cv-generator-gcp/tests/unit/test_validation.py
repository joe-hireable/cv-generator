import json
import pytest
import os
from utils.validation import Validation
from models.schema import CVGenerationRequest

class TestValidation:
    """Test suite for the Validation class."""
    
    def test_validate_request_valid(self, valid_cv_request, cv_schema):
        """Test validation with a valid request."""
        validator = Validation()
        result = validator.validate_request(valid_cv_request, cv_schema)
        assert result is True
    
    def test_validate_request_invalid(self, invalid_cv_request, cv_schema):
        """Test validation with an invalid request (missing required fields)."""
        validator = Validation()
        result = validator.validate_request(invalid_cv_request, cv_schema)
        assert result is False
    
    def test_transform_request_keys(self):
        """Test the transformation of camelCase keys to snake_case."""
        validator = Validation()
        
        # Input with camelCase keys
        input_data = {
            "outputFormat": "pdf",
            "isAnonymized": True,
            "recruiterProfile": {
                "firstName": "Jane",
                "lastName": "Smith"
            },
            "data": {
                "firstName": "John",
                "surname": "Doe",
                "profileStatement": "Test",
                "experience": [
                    {
                        "startDate": "2020-01",
                        "endDate": "2023-05"
                    }
                ]
            }
        }
        
        # Transform the keys
        result = validator._transform_request_keys(input_data)
        
        # Check top-level keys were transformed
        assert "output_format" in result
        assert "is_anonymized" in result
        assert "recruiter_profile" in result
        
        # Check nested keys in recruiterProfile were transformed
        assert "first_name" in result["recruiter_profile"]
        assert "last_name" in result["recruiter_profile"]
        
        # Check the data field
        assert "first_name" in result["data"]
        assert "profile_statement" in result["data"]
        
        # Check keys in array items
        assert "start_date" in result["data"]["experience"][0]
        assert "end_date" in result["data"]["experience"][0]
    
    def test_pydantic_model_validation_valid(self, valid_cv_request):
        """Test direct validation using Pydantic model."""
        validator = Validation()
        
        # Transform keys to snake_case for Pydantic
        transformed = validator._transform_request_keys(valid_cv_request)
        
        # Validate using Pydantic model directly
        try:
            model = CVGenerationRequest.model_validate(transformed)
            assert model.data.first_name == "John"
            assert model.data.surname == "Doe"
            assert model.output_format == "pdf"
            assert model.is_anonymized is False
            assert model.recruiter_profile is not None
            assert model.recruiter_profile.first_name == "Jane"
        except Exception as e:
            pytest.fail(f"Pydantic validation failed: {e}")
    
    def test_pydantic_model_validation_invalid(self, invalid_cv_request):
        """Test direct validation using Pydantic model with invalid data."""
        validator = Validation()
        
        # Transform keys to snake_case for Pydantic
        transformed = validator._transform_request_keys(invalid_cv_request)
        
        # Validation should fail due to missing required fields
        with pytest.raises(Exception):
            CVGenerationRequest.model_validate(transformed)
    
    def test_empty_request(self):
        """Test validation with an empty request."""
        validator = Validation()
        result = validator.validate_request({}, {})
        assert result is False 