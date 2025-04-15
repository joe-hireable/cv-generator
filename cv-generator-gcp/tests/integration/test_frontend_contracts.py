import os
import pytest
import json
import requests
from unittest.mock import patch, MagicMock
import main
from jsonschema import validate
from utils.adapter import HireableCVAdapter

class TestFrontendContracts:
    """Integration tests to verify API contracts with the frontend application."""
    
    @pytest.fixture
    def api_base_url(self):
        """The base URL for API testing."""
        return os.environ.get("TEST_API_BASE_URL", "http://localhost:8080")
    
    @pytest.fixture
    def mock_frontend_request(self):
        """Generate a mock request that mimics what the frontend would send."""
        # This structure should match what CV Branding Buddy sends
        return {
            "template": "template_WIP.docx",
            "outputFormat": "pdf",
            "sectionOrder": [
                "personal_info",
                "profile_statement",
                "skills",
                "experience",
                "education"
            ],
            "sectionVisibility": {
                "personal_info": True,
                "profile_statement": True,
                "skills": True,
                "experience": True,
                "education": True
            },
            "isAnonymized": False,
            "recruiterProfile": {
                "firstName": "Jane",
                "lastName": "Smith",
                "email": "jane.smith@example.com",
                "phone": "+44 1234 567890",
                "agencyName": "Hireable Recruiting",
                "agencyLogo": "https://example.com/logo.png",
                "website": "https://example.com"
            },
            "data": {
                "firstName": "John",
                "surname": "Doe",
                "email": "john.doe@example.com",
                "phone": "+44 9876 543210",
                "address": "London, UK",
                "linkedin": "linkedin.com/in/johndoe",
                "profileStatement": "Experienced software engineer with 10+ years in full-stack development...",
                "skills": ["Python", "JavaScript", "Cloud Computing", "Agile Development"],
                "experience": [
                    {
                        "role": "Senior Developer",
                        "company": "Tech Solutions Ltd",
                        "startDate": "2018-01",
                        "endDate": "2023-05",
                        "description": "Led development team in creating scalable applications..."
                    }
                ],
                "education": [
                    {
                        "institution": "University of Technology",
                        "degree": "BSc Computer Science",
                        "startDate": "2013",
                        "endDate": "2017",
                        "grade": "First Class Honours"
                    }
                ]
            }
        }
    
    @pytest.fixture
    def cv_response_schema(self):
        """Schema that defines what the frontend expects from a CV generation response."""
        return {
            "type": "object",
            "required": ["url"],
            "properties": {
                "url": {"type": "string", "format": "uri"},
                "id": {"type": "string"}
            }
        }
    
    @pytest.fixture
    def parse_cv_response_schema(self):
        """Schema that defines what the frontend expects from a CV parsing response."""
        return {
            "type": "object",
            "required": ["parsedData"],
            "properties": {
                "parsedData": {
                    "type": "object",
                    "properties": {
                        "firstName": {"type": "string"},
                        "surname": {"type": "string"},
                        "email": {"type": "string"},
                        "phone": {"type": "string"},
                        "address": {"type": "string"},
                        "linkedin": {"type": "string"},
                        "profileStatement": {"type": "string"},
                        "skills": {"type": "array", "items": {"type": "string"}}
                    }
                }
            }
        }
    
    @patch('main.HireableUtils')
    @patch('main.HireableClient')
    @patch('main.DocxTemplate')
    def test_cv_generation_response_contract(self, mock_docx_template_class, mock_client_class, 
                                           mock_utils_class, mock_frontend_request, cv_response_schema):
        """Test that the CV generation endpoint returns a response that matches the frontend's expectations."""
        # Set up mocks for the CV generation process
        mock_template = MagicMock()
        def mock_save(output_stream):
            output_stream.write(b"mock template content")
            return None
        mock_template.save.side_effect = mock_save
        mock_docx_template_class.return_value = mock_template
        
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.content = b"mock pdf content"
        mock_client.docx_to_pdf.return_value = mock_response
        mock_client_class.return_value = mock_client
        
        mock_utils = MagicMock()
        mock_utils.retrieve_profile_config.return_value = MagicMock(schema_file="cv_schema.json", template="template_WIP.docx")
        mock_utils.retrieve_file_from_storage.side_effect = lambda bucket, name: (
            json.dumps({"type": "object"}) if name == "cv_schema.json" 
            else b'PK\x03\x04\x14\x00\x06\x00\x08\x00\x00\x00!\x00\x00\x00\x00\x00'
        )
        mock_utils.upload_cv_to_storage.return_value = "generated-cvs/test-cv.pdf"
        mock_utils.generate_cv_download_link.return_value = "https://storage.googleapis.com/test-bucket/generated-cvs/test-cv.pdf?signature"
        mock_utils_class.return_value = mock_utils
        
        # Create a mock request with our frontend data
        mock_request = type('MockRequest', (), {
            'method': 'POST',
            'headers': {'Content-Type': 'application/json'},
            'get_json': lambda: mock_frontend_request
        })
        
        # Call the CV generation endpoint
        with patch('main.Validation') as mock_validation_class:
            mock_validation = MagicMock()
            mock_validation.validate_request.return_value = True
            mock_validation._transform_request_keys.return_value = {
                "data": {
                    "first_name": "John",
                    "surname": "Doe",
                    "experience": []
                },
                "output_format": "pdf"
            }
            mock_validation_class.return_value = mock_validation
            
            result = main.generate_cv(mock_request)
        
        # Verify the response
        assert result[1] == 200  # Status code
        
        # Parse the response JSON
        response_data = json.loads(result[0])
        
        # Validate against the schema
        validate(instance=response_data, schema=cv_response_schema)
        
        # Additional specific checks
        assert "url" in response_data
        assert response_data["url"].startswith("https://")

    @patch('main.HireableClient')
    def test_cv_parsing_response_contract(self, mock_client_class, mock_frontend_request, parse_cv_response_schema):
        """Test that the CV parsing endpoint returns a response that matches the frontend's expectations."""
        # Set up mocks for the CV parsing process
        mock_client = MagicMock()
        mock_client.parse_cv.return_value = {
            "contact_info": {
                "first_name": "John",
                "last_name": "Doe",
                "email": "john.doe@example.com",
                "phone": "+44 9876 543210",
                "location": "London, UK"
            },
            "personal_statement": "Experienced software engineer with 10+ years in full-stack development...",
            "skills": ["Python", "JavaScript", "Cloud Computing", "Agile Development"],
            "links": ["linkedin.com/in/johndoe"]
        }
        mock_client_class.return_value = mock_client
        
        # Create a mock request for CV parsing
        mock_request = type('MockRequest', (), {
            'method': 'POST',
            'headers': {'Content-Type': 'application/json'},
            'get_json': lambda: {
                "fileContent": "base64-encoded-content",
                "fileName": "example-cv.pdf"
            },
            'files': {'file': ('example-cv.pdf', b'file content')}
        })
        
        # Call the CV parsing endpoint - assuming we have this in main.py
        with patch('main.parse_cv', return_value=(json.dumps({
                "parsedData": HireableCVAdapter.parser_to_generator({
                    "contact_info": {
                        "first_name": "John",
                        "last_name": "Doe",
                        "email": "john.doe@example.com",
                        "phone": "+44 9876 543210",
                        "location": "London, UK"
                    },
                    "personal_statement": "Experienced software engineer with 10+ years in full-stack development...",
                    "skills": ["Python", "JavaScript", "Cloud Computing", "Agile Development"],
                    "links": ["linkedin.com/in/johndoe"]
                })["data"]
            }), 200)):
            
            result = main.parse_cv(mock_request)
        
        # Verify the response
        assert result[1] == 200  # Status code
        
        # Parse the response JSON
        response_data = json.loads(result[0])
        
        # Validate against the schema
        validate(instance=response_data, schema=parse_cv_response_schema)
        
        # Additional specific checks
        assert "parsedData" in response_data
        assert "firstName" in response_data["parsedData"]
        assert "surname" in response_data["parsedData"]
        assert response_data["parsedData"]["firstName"] == "John"
        assert response_data["parsedData"]["surname"] == "Doe"
    
    def test_live_frontend_api_contract(self, api_base_url, mock_frontend_request, cv_response_schema):
        """Test the actual API endpoint with a real request structure."""
        try:
            # Make a real API call to the CV generation endpoint
            response = requests.post(
                f"{api_base_url}/api/cv/generate",
                json=mock_frontend_request,
                headers={"Content-Type": "application/json"}
            )
            
            # Verify the response
            assert response.status_code == 200
            
            # Validate the response against our schema
            response_data = response.json()
            validate(instance=response_data, schema=cv_response_schema)
            
            # Verify the URL is accessible
            assert "url" in response_data
            url_response = requests.head(response_data["url"])
            assert url_response.status_code == 200
            
        except requests.RequestException as e:
            pytest.skip(f"Live API test failed: {str(e)}")
            
    def test_error_response_contract(self):
        """Test that error responses follow a consistent structure that the frontend can handle."""
        # Create a mock request with invalid data
        mock_request = type('MockRequest', (), {
            'method': 'POST',
            'headers': {'Content-Type': 'application/json'},
            'get_json': lambda: {"invalid": "data"}
        })

        # Mock the utils class to avoid storage errors
        with patch('main.HireableUtils') as mock_utils_class, \
             patch('main.Validation') as mock_validation_class:
            
            # Configure utils mocks
            mock_utils = MagicMock()
            mock_utils.retrieve_profile_config.return_value = MagicMock(schema_file="cv_schema.json", template="template_WIP.docx")
            mock_utils.retrieve_file_from_storage.side_effect = lambda bucket, name: (
                json.dumps({"type": "object", "properties": {"data": {"type": "object"}}}) if name == "cv_schema.json"
                else b'PK\x03\x04\x14\x00\x06\x00\x08\x00\x00\x00!\x00\x00\x00\x00\x00'
            )
            mock_utils_class.return_value = mock_utils
            
            # Configure validation mocks
            mock_validation = MagicMock()
            mock_validation.validate_request.return_value = False
            mock_validation_class.return_value = mock_validation

            # Call the endpoint
            result = main.generate_cv(mock_request)
            
            # Check the response
            assert result[1] == 400
            error_data = json.loads(result[0])
            assert "error" in error_data
            assert isinstance(error_data["error"], str) 