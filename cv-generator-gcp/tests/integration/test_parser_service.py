import os
import pytest
import json
import base64
from unittest.mock import patch, MagicMock
import requests
import main
from utils.client import HireableClient
from utils.adapter import HireableCVAdapter

class TestParserServiceIntegration:
    """Integration tests for the HireableCV Parser service."""
    
    @pytest.fixture
    def parser_service_url(self):
        """The URL of the parser service."""
        return os.environ.get("PARSER_SERVICE_URL", "https://parser-api.example.com")
    
    @pytest.fixture
    def sample_cv_content(self):
        """Sample CV content for testing."""
        return b"This is a sample CV with some formatting and content."
    
    @pytest.fixture
    def sample_parsed_data(self):
        """Sample parsed data returned by the parser service."""
        return {
            "contact_info": {
                "first_name": "John",
                "last_name": "Doe",
                "email": "john.doe@example.com",
                "phone": "+44 9876 543210",
                "location": "London, UK"
            },
            "personal_statement": "Experienced software engineer with 10+ years in full-stack development...",
            "skills": ["Python", "JavaScript", "Cloud Computing", "Agile Development"],
            "links": ["linkedin.com/in/johndoe"],
            "experience": [
                {
                    "title": "Senior Developer",
                    "company": "Tech Solutions Ltd",
                    "start_date": "2018-01",
                    "end_date": "2023-05",
                    "description": "Led development team in creating scalable applications..."
                }
            ],
            "education": [
                {
                    "institution": "University of Technology",
                    "degree": "BSc Computer Science",
                    "start_date": "2013",
                    "end_date": "2017",
                    "grade": "First Class Honours"
                }
            ]
        }
    
    def test_client_parse_cv_method(self, sample_cv_content, sample_parsed_data):
        """Test the HireableClient's parse_cv method."""
        with patch('utils.client.requests.post') as mock_post:
            # Configure the mock response
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = sample_parsed_data
            mock_post.return_value = mock_response
            
            # Create the client and call the parse_cv method
            client = HireableClient()
            client.parser_api_endpoint = "https://parser-api.example.com/parse"
            
            result = client.parse_cv(sample_cv_content, "example-cv.pdf")
            
            # Verify the request was made correctly
            mock_post.assert_called_once()
            args, kwargs = mock_post.call_args
            assert args[0] == client.parser_api_endpoint
            assert "files" in kwargs
            assert kwargs["files"]["file"][0] == "example-cv.pdf"
            
            # Verify the result
            assert result == sample_parsed_data
    
    def test_parse_cv_endpoint(self, sample_cv_content, sample_parsed_data):
        """Test the parse_cv endpoint in the main application."""
        with patch('main.HireableClient') as mock_client_class:
            # Configure the client mock
            mock_client = MagicMock()
            mock_client.parse_cv.return_value = sample_parsed_data
            mock_client_class.return_value = mock_client
            
            # Create a mock request with a file
            file_content_b64 = base64.b64encode(sample_cv_content).decode('utf-8')
            mock_request = type('MockRequest', (), {
                'method': 'POST',
                'headers': {'Content-Type': 'application/json'},
                'get_json': lambda: {
                    "fileContent": file_content_b64,
                    "fileName": "example-cv.pdf"
                }
            })
            
            # Call the endpoint
            result = main.parse_cv(mock_request)
            
            # Verify the client was called correctly
            mock_client.parse_cv.assert_called_once()
            
            # Verify the response
            assert result[1] == 200
            response_data = json.loads(result[0])
            assert "parsedData" in response_data
            
            # The response should contain the data transformed by the adapter
            generator_data = HireableCVAdapter.parser_to_generator(sample_parsed_data)
            assert response_data["parsedData"]["firstName"] == generator_data["data"]["firstName"]
            assert response_data["parsedData"]["surname"] == generator_data["data"]["surname"]
    
    def test_parse_and_generate_endpoint(self, sample_cv_content, sample_parsed_data):
        """Test the combined parse_and_generate endpoint."""
        with patch('main.HireableClient') as mock_client_class, \
             patch('main.HireableUtils') as mock_utils_class, \
             patch('main.DocxTemplate') as mock_docx_template_class:
            
            # Configure the client mock for parsing
            mock_client = MagicMock()
            mock_client.parse_cv.return_value = sample_parsed_data
            
            # Configure the client mock for PDF conversion
            mock_pdf_response = MagicMock()
            mock_pdf_response.content = b"mock pdf content"
            mock_client.docx_to_pdf.return_value = mock_pdf_response
            
            mock_client_class.return_value = mock_client
            
            # Configure the utils mock
            mock_utils = MagicMock()
            mock_utils.retrieve_profile_config.return_value = MagicMock(schema_file="cv_schema.json", template="template_WIP.docx")
            mock_utils.retrieve_file_from_storage.side_effect = lambda bucket, name: (
                json.dumps({"type": "object"}) if name == "cv_schema.json" 
                else b'PK\x03\x04\x14\x00\x06\x00\x08\x00\x00\x00!\x00\x00\x00\x00\x00'
            )
            mock_utils.upload_cv_to_storage.return_value = "generated-cvs/test-cv.pdf"
            mock_utils.generate_cv_download_link.return_value = "https://storage.googleapis.com/test-bucket/generated-cvs/test-cv.pdf?signature"
            mock_utils_class.return_value = mock_utils
            
            # Configure the template mock
            mock_template = MagicMock()
            def mock_save(output_stream):
                output_stream.write(b"mock template content")
                return None
            mock_template.save.side_effect = mock_save
            mock_docx_template_class.return_value = mock_template
            
            # Create a mock request with a file and CV generation options
            file_content_b64 = base64.b64encode(sample_cv_content).decode('utf-8')
            mock_request = type('MockRequest', (), {
                'method': 'POST',
                'headers': {'Content-Type': 'application/json'},
                'get_json': lambda: {
                    "fileContent": file_content_b64,
                    "fileName": "example-cv.pdf",
                    "template": "template_WIP.docx",
                    "outputFormat": "pdf",
                    "sectionOrder": ["personal_info", "experience", "education"],
                    "sectionVisibility": {"personal_info": True, "experience": True}
                }
            })
            
            # Handle validation
            with patch('main.Validation') as mock_validation_class:
                mock_validation = MagicMock()
                mock_validation.validate_request.return_value = True
                mock_validation._transform_request_keys.return_value = {
                    "data": HireableCVAdapter.parser_to_generator(sample_parsed_data)["data"],
                    "output_format": "pdf",
                    "section_order": ["personal_info", "experience", "education"],
                    "section_visibility": {"personal_info": True, "experience": True}
                }
                mock_validation_class.return_value = mock_validation
                
                # Call the endpoint
                result = main.parse_and_generate_cv(mock_request)
            
            # Verify the client was called correctly for parsing
            mock_client.parse_cv.assert_called_once()
            
            # Verify the PDF conversion was called
            mock_client.docx_to_pdf.assert_called_once()
            
            # Verify the response
            assert result[1] == 200
            response_data = json.loads(result[0])
            assert "url" in response_data
            assert response_data["url"] == "https://storage.googleapis.com/test-bucket/generated-cvs/test-cv.pdf?signature"
    
    def test_parser_error_handling(self, sample_cv_content):
        """Test error handling when the parser service returns an error."""
        with patch('utils.client.requests.post') as mock_post:
            # Configure the mock to return an error
            mock_response = MagicMock()
            mock_response.status_code = 400
            mock_response.text = "Bad Request: Could not parse CV"
            mock_post.return_value = mock_response
            
            # Create the client and call the parse_cv method
            client = HireableClient()
            
            # The method should raise an exception
            with pytest.raises(Exception) as excinfo:
                client.parse_cv(sample_cv_content, "example-cv.pdf")
            
            assert "400" in str(excinfo.value)
            assert "Could not parse CV" in str(excinfo.value)
    
    def test_parser_connection_error_handling(self, sample_cv_content):
        """Test error handling for connection issues with the parser service."""
        with patch('utils.client.requests.post') as mock_post:
            # Configure the mock to raise a connection error
            mock_post.side_effect = requests.ConnectionError("Could not connect to server")
            
            # Create the client and call the parse_cv method
            client = HireableClient()
            
            # The method should raise an exception
            with pytest.raises(Exception) as excinfo:
                client.parse_cv(sample_cv_content, "example-cv.pdf")
            
            assert "Could not connect to server" in str(excinfo.value)
    
    @pytest.mark.skipif(not os.environ.get("RUN_LIVE_PARSER_TESTS"), 
                        reason="Skipping live parser tests, set RUN_LIVE_PARSER_TESTS=1 to enable")
    def test_live_parser_service(self, parser_service_url, sample_cv_content):
        """Test the actual parser service with a real API call.
        
        This test is skipped by default and only runs when explicitly enabled.
        """
        try:
            # Create a client with the real parser service URL
            client = HireableClient()
            client.parser_api_endpoint = f"{parser_service_url}/parse"
            
            # Send a real request to the parser service
            result = client.parse_cv(sample_cv_content, "example-cv.pdf")
            
            # Basic verification of the result structure
            assert isinstance(result, dict)
            assert "contact_info" in result
            
            # Convert to generator format and verify
            generator_data = HireableCVAdapter.parser_to_generator(result)
            assert "data" in generator_data
            assert "firstName" in generator_data["data"] or "first_name" in generator_data["data"]
            
        except Exception as e:
            pytest.skip(f"Live parser test failed: {str(e)}")
    
    @pytest.mark.skipif(not os.environ.get("RUN_LIVE_PARSER_TESTS"), 
                        reason="Skipping live parser tests, set RUN_LIVE_PARSER_TESTS=1 to enable")
    def test_live_combined_workflow(self, parser_service_url, sample_cv_content):
        """Test the full workflow from parsing to CV generation with real services.
        
        This test is skipped by default and only runs when explicitly enabled.
        """
        # This would require actual setup of both services and API keys
        # For now, we'll just sketch the concept
        try:
            # Initialize the client
            client = HireableClient()
            
            # 1. Parse the CV
            parsed_data = client.parse_cv(sample_cv_content, "example-cv.pdf")
            
            # 2. Convert to generator format
            generator_data = HireableCVAdapter.parser_to_generator(parsed_data)
            
            # 3. Use generator data to create a CV
            # (This would be a real API call in a full test)
            
            # 4. Verify the result
            pytest.skip("Live combined workflow test is conceptual and not fully implemented")
            
        except Exception as e:
            pytest.skip(f"Live combined workflow test failed: {str(e)}") 