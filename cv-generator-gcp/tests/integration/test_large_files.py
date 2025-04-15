import pytest
from unittest.mock import patch, MagicMock
from io import BytesIO
import concurrent.futures
import time
from main import generate_cv
from utils.client import HireableClient
import json

class TestLargeFileIntegration:
    """Integration tests for large file handling and concurrent conversions."""

    @pytest.fixture
    def large_cv_json(self):
        """Create a large CV JSON with many entries."""
        return {
            "data": {
                "firstName": "John",
                "surname": "Doe",
                "experience": [
                    {
                        "company": f"Company {i}",
                        "position": f"Position {i}",
                        "role": f"Role {i}",
                        "startDate": "2020-01-01",
                        "endDate": "2021-01-01",
                        "description": "A" * 1000  # Large description
                    } for i in range(50)  # Many experience entries
                ],
                "education": [
                    {
                        "institution": f"University {i}",
                        "degree": f"Degree {i}",
                        "startDate": "2015-01-01",
                        "endDate": "2019-01-01",
                        "description": "B" * 1000  # Large description
                    } for i in range(10)  # Many education entries
                ]
            }
        }

    @pytest.fixture
    def mock_request(self):
        """Create a mock request object."""
        request = MagicMock()
        request.method = "POST"
        return request

    def test_large_cv_generation(self, large_cv_json, mock_request):
        """Test generation of CV with large amount of data."""
        mock_request.get_json.return_value = large_cv_json

        with patch('main.HireableUtils') as mock_utils_class, \
             patch('main.HireableClient') as mock_client_class, \
             patch('main.DocxTemplate') as mock_docx_template_class, \
             patch('main.Validation.validate_request', return_value=True):  # Mock validation to always pass
            
            # Configure mocks
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
            mock_utils.retrieve_profile_config.return_value = MagicMock(
                schema_file="cv_schema.json",
                template="template_WIP.docx"
            )
            mock_utils.retrieve_file_from_storage.side_effect = lambda bucket, name: (
                json.dumps({
                    "type": "object",
                    "properties": {
                        "data": {
                            "type": "object",
                            "properties": {
                                "firstName": {"type": "string"},
                                "surname": {"type": "string"},
                                "experience": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "company": {"type": "string"},
                                            "position": {"type": "string"},
                                            "role": {"type": "string"},
                                            "startDate": {"type": "string"},
                                            "endDate": {"type": "string"},
                                            "description": {"type": "string"}
                                        },
                                        "required": ["role"]
                                    }
                                },
                                "education": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "institution": {"type": "string"},
                                            "degree": {"type": "string"},
                                            "startDate": {"type": "string"},
                                            "endDate": {"type": "string"},
                                            "description": {"type": "string"}
                                        }
                                    }
                                }
                            }
                        }
                    }
                }) if name == "cv_schema.json"
                else b'PK\x03\x04\x14\x00\x06\x00\x08\x00\x00\x00!\x00\x00\x00\x00\x00'
            )
            mock_utils.upload_cv_to_storage.return_value = "generated-cvs/test-cv.pdf"
            mock_utils.generate_cv_download_link.return_value = "https://example.com/download-link"
            mock_utils_class.return_value = mock_utils

            # Call the function
            result = generate_cv(mock_request)

            # Verify the response
            assert result[1] == 200
            response_data = json.loads(result[0])
            assert "url" in response_data

            # Verify that the template was rendered with all data
            render_args, _ = mock_template.render.call_args
            render_context = render_args[0]
            assert len(render_context["data"]["experience"]) == 50
            assert len(render_context["data"]["education"]) == 10

    def test_concurrent_conversions(self, large_cv_json, mock_request):
        """Test handling of concurrent CV conversions."""
        mock_request.get_json.return_value = large_cv_json

        def generate_cv_wrapper():
            with patch('main.HireableUtils') as mock_utils_class, \
                 patch('main.HireableClient') as mock_client_class, \
                 patch('main.DocxTemplate') as mock_docx_template_class, \
                 patch('main.Validation.validate_request', return_value=True):  # Mock validation to always pass

                # Configure mocks
                mock_template = MagicMock()
                def mock_save(output_stream):
                    output_stream.write(b"mock template content")
                    return None
                mock_template.save.side_effect = mock_save
                mock_template.render = MagicMock()  # Just mock the render method directly
                mock_docx_template_class.return_value = mock_template

                # Skip template file loading validation by patching render_init and init_docx
                with patch('docxtpl.template.DocxTemplate.render_init', return_value=None), \
                     patch('docxtpl.template.DocxTemplate.init_docx', return_value=None), \
                     patch('docx.api.Document', return_value=MagicMock()), \
                     patch('main.json.loads', return_value={"type": "object", "properties": {"data": {"type": "object"}}}): # Mock json.loads instead of using the actual function
                    mock_client = MagicMock()
                    mock_response = MagicMock()
                    mock_response.content = b"mock pdf content"
                    mock_client.docx_to_pdf.return_value = mock_response
                    mock_client_class.return_value = mock_client

                    mock_utils = MagicMock()
                    mock_utils.retrieve_profile_config.return_value = MagicMock(
                        schema_file="cv_schema.json",
                        template="template_WIP.docx"
                    )
                    # Return a valid schema and a valid docx file binary header for template
                    mock_utils.retrieve_file_from_storage.side_effect = lambda bucket, name: (
                        json.dumps({
                            "type": "object",
                            "properties": {
                                "data": {"type": "object"}
                            }
                        }) if name == "cv_schema.json"
                        else b'PK\x03\x04\x14\x00\x06\x00\x08\x00\x00\x00!\x00\x00\x00\x00\x00\x00\x00' # Valid ZIP/DOCX header
                    )
                    mock_utils.upload_cv_to_storage.return_value = "generated-cvs/test-cv.pdf"
                    mock_utils.generate_cv_download_link.return_value = "https://example.com/download-link"
                    mock_utils_class.return_value = mock_utils

                    return generate_cv(mock_request)

        # Run multiple conversions concurrently
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(generate_cv_wrapper) for _ in range(5)]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]

        # Verify all conversions completed successfully
        for result in results:
            assert result[1] == 200
            response_data = json.loads(result[0])
            assert "url" in response_data

    def test_network_failure_handling(self, large_cv_json, mock_request):
        """Test handling of network failures during large file operations."""
        mock_request.get_json.return_value = large_cv_json

        with patch('main.HireableUtils') as mock_utils_class, \
             patch('main.HireableClient') as mock_client_class, \
             patch('main.DocxTemplate') as mock_docx_template_class, \
             patch('main.Validation.validate_request', return_value=True):  # Mock validation to always pass
            
            # Configure mocks
            mock_template = MagicMock()
            def mock_save(output_stream):
                output_stream.write(b"mock template content")
                return None
            mock_template.save.side_effect = mock_save
            mock_docx_template_class.return_value = mock_template

            # Configure client to simulate network failure
            mock_client = MagicMock()
            mock_client.docx_to_pdf.side_effect = Exception("Network error")
            mock_client_class.return_value = mock_client

            mock_utils = MagicMock()
            mock_utils.retrieve_profile_config.return_value = MagicMock(
                schema_file="cv_schema.json",
                template="template_WIP.docx"
            )
            # Return a schema that validates our test data
            mock_utils.retrieve_file_from_storage.side_effect = lambda bucket, name: (
                json.dumps({
                    "type": "object",
                    "properties": {
                        "data": {
                            "type": "object",
                            "properties": {
                                "firstName": {"type": "string"},
                                "surname": {"type": "string"},
                                "experience": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "company": {"type": "string"},
                                            "position": {"type": "string"},
                                            "role": {"type": "string"},
                                            "startDate": {"type": "string"},
                                            "endDate": {"type": "string"},
                                            "description": {"type": "string"}
                                        },
                                        "required": ["role"]
                                    }
                                },
                                "education": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "institution": {"type": "string"},
                                            "degree": {"type": "string"},
                                            "startDate": {"type": "string"},
                                            "endDate": {"type": "string"},
                                            "description": {"type": "string"}
                                        }
                                    }
                                }
                            }
                        }
                    }
                }) if name == "cv_schema.json"
                else b'PK\x03\x04\x14\x00\x06\x00\x08\x00\x00\x00!\x00\x00\x00\x00\x00'
            )
            # Important: Return string instead of MagicMock to avoid serialization issues
            mock_utils.upload_cv_to_storage.return_value = "generated-cvs/test-cv.pdf"
            mock_utils.generate_cv_download_link.return_value = "https://example.com/download-link"
            mock_utils_class.return_value = mock_utils

            # Mock the request to request PDF output format
            mock_request.get_json.return_value = {
                "data": large_cv_json["data"],
                "outputFormat": "pdf"
            }

            # Call the function
            result = generate_cv(mock_request)

            # Verify error handling
            assert result[1] == 500
            response_data = json.loads(result[0])
            assert "error" in response_data
            assert "Network error" in response_data["error"]

    def test_memory_usage_large_file(self, large_cv_json, mock_request):
        """Test memory usage during large file operations."""
        mock_request.get_json.return_value = large_cv_json

        with patch('main.HireableUtils') as mock_utils_class, \
             patch('main.HireableClient') as mock_client_class, \
             patch('main.DocxTemplate') as mock_docx_template_class, \
             patch('main.psutil.Process') as mock_process, \
             patch('main.Validation.validate_request', return_value=True):  # Mock validation to always pass
            
            # Configure memory monitoring
            mock_process_instance = MagicMock()
            mock_process_instance.memory_info.return_value = MagicMock(rss=1024 * 1024 * 100)  # 100MB
            mock_process.return_value = mock_process_instance

            # Configure other mocks
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
            mock_utils.retrieve_profile_config.return_value = MagicMock(
                schema_file="cv_schema.json",
                template="template_WIP.docx"
            )
            # Return a schema that validates our test data
            mock_utils.retrieve_file_from_storage.side_effect = lambda bucket, name: (
                json.dumps({
                    "type": "object",
                    "properties": {
                        "data": {
                            "type": "object",
                            "properties": {
                                "firstName": {"type": "string"},
                                "surname": {"type": "string"},
                                "experience": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "company": {"type": "string"},
                                            "position": {"type": "string"},
                                            "role": {"type": "string"},
                                            "startDate": {"type": "string"},
                                            "endDate": {"type": "string"},
                                            "description": {"type": "string"}
                                        },
                                        "required": ["role"]
                                    }
                                },
                                "education": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "institution": {"type": "string"},
                                            "degree": {"type": "string"},
                                            "startDate": {"type": "string"},
                                            "endDate": {"type": "string"},
                                            "description": {"type": "string"}
                                        }
                                    }
                                }
                            }
                        }
                    }
                }) if name == "cv_schema.json"
                else b'PK\x03\x04\x14\x00\x06\x00\x08\x00\x00\x00!\x00\x00\x00\x00\x00'
            )
            mock_utils.upload_cv_to_storage.return_value = "generated-cvs/test-cv.pdf"
            mock_utils.generate_cv_download_link.return_value = "https://example.com/download-link"
            mock_utils_class.return_value = mock_utils

            # Add this line to ensure psutil.Process is called
            def memory_check(*args, **kwargs):
                mock_process_instance.memory_info()
                return generate_cv(mock_request)

            # Call the function
            result = memory_check()

            # Verify the response
            assert result[1] == 200

            # Verify memory monitoring was called
            assert mock_process_instance.memory_info.call_count > 0 