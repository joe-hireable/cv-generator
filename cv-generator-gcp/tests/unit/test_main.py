import json
import pytest
import os
from unittest.mock import patch, MagicMock
from io import BytesIO
import main
from models.schema import CVGenerationRequest

class TestMainFunction:
    """Test suite for the main Cloud Function."""
    
    @patch('main.Validation')
    @patch('main.HireableClient')
    @patch('main.HireableUtils')
    def test_generate_cv_success(self, mock_utils_class, mock_client_class, mock_validation_class, mock_request, mock_docx_template):
        """Test successful CV generation."""
        # Set up mocks
        mock_validation = MagicMock()
        mock_validation.validate_request.return_value = True
        mock_validation._transform_request_keys.return_value = {
            "data": {
                "first_name": "John",
                "surname": "Doe",
                "experience": []
            }
        }
        mock_validation_class.return_value = mock_validation
        
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.content = b"mock pdf content"
        mock_client.docx_to_pdf.return_value = mock_response
        mock_client_class.return_value = mock_client
        
        mock_utils = MagicMock()
        mock_utils.retrieve_profile_config.return_value = MagicMock(schema_file="cv_schema.json", template="template_WIP.docx")
        # Return a proper template file and schema
        mock_utils.retrieve_file_from_storage.side_effect = lambda bucket, name: (
            json.dumps({"type": "object"}) if name == "cv_schema.json" 
            else b'PK\x03\x04\x14\x00\x06\x00\x08\x00\x00\x00!\x00\x00\x00\x00\x00'
        )
        mock_utils.generate_cv_download_link.return_value = "https://example.com/download-link"
        mock_utils_class.return_value = mock_utils
        
        # Setup request mock with valid data
        request_data = {
            "data": {
                "firstName": "John",
                "surname": "Doe"
            }
        }
        mock_request.get_json.return_value = request_data
        
        # Mock DocxTemplate and its methods
        with patch('main.DocxTemplate') as mock_docx:
            mock_template = MagicMock()
            # Mock the save method to write some data to the BytesIO
            def mock_save(output_stream):
                output_stream.write(b"mock template content")
                return None
            mock_template.save.side_effect = mock_save
            mock_docx.return_value = mock_template
            
            # Call the function
            result = main.generate_cv(mock_request)
            
            # Check the result
            assert result[1] == 200
            response_data = json.loads(result[0])
            assert "url" in response_data
            assert response_data["url"] == "https://example.com/download-link"
    
    @patch('main.Validation')
    @patch('main.HireableClient')
    @patch('main.HireableUtils')
    def test_generate_cv_validation_failure(self, mock_utils_class, mock_client_class, mock_validation_class, mock_invalid_request):
        """Test validation failure in CV generation."""
        # Set up mocks
        mock_validation = MagicMock()
        mock_validation.validate_request.return_value = False
        mock_validation_class.return_value = mock_validation
        
        mock_utils = MagicMock()
        mock_utils.retrieve_profile_config.return_value = MagicMock(schema_file="cv_schema.json", template="template_WIP.docx")
        mock_utils.retrieve_file_from_storage.return_value = json.dumps({"type": "object"})
        mock_utils_class.return_value = mock_utils
        
        # Call the function
        result = main.generate_cv(mock_invalid_request)
        
        # The function should return an error response
        assert result[1] == 400
        response_data = json.loads(result[0])
        assert "error" in response_data
    
    @patch('main.Validation')
    @patch('main.HireableClient')
    @patch('main.HireableUtils')
    def test_generate_cv_pdf_output(self, mock_utils_class, mock_client_class, mock_validation_class, mock_request, mock_docx_template):
        """Test CV generation with PDF output."""
        # Set up mocks
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
        
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.content = b"mock pdf content"
        mock_client.docx_to_pdf.return_value = mock_response
        mock_client_class.return_value = mock_client
        
        mock_utils = MagicMock()
        mock_utils.retrieve_profile_config.return_value = MagicMock(schema_file="cv_schema.json", template="template_WIP.docx")
        # Return a proper binary string to simulate a template file for both schema and template
        mock_utils.retrieve_file_from_storage.side_effect = lambda bucket, name: (
            json.dumps({"type": "object"}) if name == "cv_schema.json" 
            else b'PK\x03\x04\x14\x00\x06\x00\x08\x00\x00\x00!\x00\x00\x00\x00\x00'
        )
        mock_utils.generate_cv_download_link.return_value = "https://example.com/download-link"
        mock_utils_class.return_value = mock_utils
        
        # Setup request mock with PDF output format
        request_data = {
            "data": {
                "firstName": "John",
                "surname": "Doe"
            },
            "outputFormat": "pdf"
        }
        mock_request.get_json.return_value = request_data
        
        # Mock DocxTemplate and its methods
        with patch('main.DocxTemplate') as mock_docx:
            mock_template = MagicMock()
            # Mock the save method to write some data to the BytesIO
            def mock_save(output_stream):
                output_stream.write(b"mock template content")
                return None
            mock_template.save.side_effect = mock_save
            mock_docx.return_value = mock_template
            
            # Call the function
            result = main.generate_cv(mock_request)
            
            # Check the result
            assert result[1] == 200
            
            # Check that PDF conversion was called
            mock_client.docx_to_pdf.assert_called_once()
    
    @patch('main.Validation')
    @patch('main.HireableClient')
    @patch('main.HireableUtils')
    def test_generate_cv_anonymized(self, mock_utils_class, mock_client_class, mock_validation_class, mock_request, mock_docx_template):
        """Test CV generation with anonymization."""
        # Set up mocks
        mock_validation = MagicMock()
        mock_validation.validate_request.return_value = True
        mock_validation._transform_request_keys.return_value = {
            "data": {
                "first_name": "John",
                "surname": "Doe",
                "experience": []
            },
            "is_anonymized": True
        }
        mock_validation_class.return_value = mock_validation
        
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        
        mock_utils = MagicMock()
        mock_utils.retrieve_profile_config.return_value = MagicMock(schema_file="cv_schema.json", template="template_WIP.docx")
        # Return a proper template file and schema
        mock_utils.retrieve_file_from_storage.side_effect = lambda bucket, name: (
            json.dumps({"type": "object"}) if name == "cv_schema.json" 
            else b'PK\x03\x04\x14\x00\x06\x00\x08\x00\x00\x00!\x00\x00\x00\x00\x00'
        )
        mock_utils.generate_cv_download_link.return_value = "https://example.com/download-link"
        mock_utils_class.return_value = mock_utils
        
        # Setup request mock with anonymization
        request_data = {
            "data": {
                "firstName": "John",
                "surname": "Doe"
            },
            "isAnonymized": True
        }
        mock_request.get_json.return_value = request_data
        
        # Mock DocxTemplate and its methods
        with patch('main.DocxTemplate') as mock_docx:
            mock_template = MagicMock()
            # Mock the save method to write some data to the BytesIO
            def mock_save(output_stream):
                output_stream.write(b"mock template content")
                return None
            mock_template.save.side_effect = mock_save
            mock_docx.return_value = mock_template
            
            # Call the function
            result = main.generate_cv(mock_request)
            
            # Check the result
            assert result[1] == 200
    
    def test_escape_ampersands(self):
        """Test the escape_ampersands function."""
        # Test with a string
        assert main.escape_ampersands("Test & Example") == "Test &amp; Example"
        
        # Test with a nested dictionary
        input_data = {
            "text": "A & B",
            "nested": {
                "text": "C & D"
            },
            "list": ["E & F", "G & H"]
        }
        
        result = main.escape_ampersands(input_data)
        
        assert result["text"] == "A &amp; B"
        assert result["nested"]["text"] == "C &amp; D"
        assert result["list"][0] == "E &amp; F"
        assert result["list"][1] == "G &amp; H"
    
    def test_generate_filename(self):
        """Test the generate_filename function."""
        request = {
            "data": {
                "firstName": "John",
                "surname": "Doe"
            }
        }
        
        # Test with default filetype (docx)
        filename = main.generate_filename(request)
        assert filename.startswith("John Doe CV ")
        assert filename.endswith(".docx")
        
        # Test with specified filetype (pdf)
        filename = main.generate_filename(request, "pdf")
        assert filename.startswith("John Doe CV ")
        assert filename.endswith(".pdf")
    
    @patch('main.DocxTemplate')
    def test_generate_cv_from_template(self, mock_docx_template_class, sample_docx_template):
        """Test the generate_cv_from_template function."""
        # Set up mock
        mock_template = MagicMock()
        # Mock the save method to add content to the BytesIO
        def mock_save(output_stream):
            output_stream.write(b"mock rendered template")
            return None
        mock_template.save.side_effect = mock_save
        mock_docx_template_class.return_value = mock_template
        
        # Create test data
        context = {"data": {"firstName": "John", "surname": "Doe"}}
        
        # Call the function
        result = main.generate_cv_from_template(context, sample_docx_template)
        
        # Check that the template was rendered and saved
        mock_template.render.assert_called_once_with(context)
        mock_template.save.assert_called_once()
        
        # Result should be a BytesIO object
        assert isinstance(result, BytesIO)
        # Check content was written
        result.seek(0)
        assert result.read() == b"mock rendered template"
    
    def test_prepare_template_context(self):
        """Test the prepare_template_context function."""
        # Basic request
        request = {
            "data": {
                "firstName": "John",
                "surname": "Doe"
            }
        }
        
        # Test with default parameters
        result = main.prepare_template_context(request)
        assert result == request
        
        # Test with section order
        section_order = ["personal_info", "skills", "experience"]
        result = main.prepare_template_context(request, section_order)
        assert result["sectionOrder"] == section_order
        
        # Test with section visibility
        section_visibility = {"personal_info": True, "skills": False}
        result = main.prepare_template_context(request, None, section_visibility)
        assert result["sectionVisibility"] == section_visibility
        
        # Test with anonymization
        result = main.prepare_template_context(request, None, None, True)
        # Verify it calls anonymize_cv_data by checking specific fields were anonymized
        assert result["data"]["firstName"] == "J."
        assert result["data"]["surname"] == "D."
        assert result != request
    
    def test_anonymize_cv_data(self):
        """Test the anonymize_cv_data function."""
        # Create test data with personal information
        data = {
            "data": {
                "firstName": "John",
                "surname": "Doe",
                "email": "john.doe@example.com",
                "phone": "+44 1234 567890",
                "address": "123 Main St, London",
                "linkedin": "linkedin.com/in/johndoe"
            }
        }
        
        # Anonymize the data
        result = main.anonymize_cv_data(data)
        
        # Check that personal information is anonymized
        assert result["data"]["firstName"] == "J."
        assert result["data"]["surname"] == "D."
        assert result["data"]["email"] == "candidate@example.com"
        assert result["data"]["phone"] == "+44 XXX XXX XXXX"
        assert result["data"]["address"] == "United Kingdom"
        assert result["data"]["linkedin"] == "linkedin.com/in/candidate" 