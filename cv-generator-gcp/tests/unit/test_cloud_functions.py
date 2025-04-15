import pytest
from unittest.mock import patch, MagicMock
from io import BytesIO
import requests
from utils.client import HireableClient
import os

class TestDocxToPdfCloudFunction:
    """Test suite for the docx_to_pdf Cloud Function."""

    @pytest.fixture
    def sample_docx_file(self):
        """Create a sample DOCX file content."""
        file = BytesIO(b"PK\x03\x04\x14\x00\x06\x00\x08\x00\x00\x00!\x00\x00\x00\x00\x00")
        file.name = "test.docx"
        return file

    @pytest.fixture
    def mock_secret_manager(self):
        """Mock the Secret Manager client."""
        with patch('utils.client.secretmanager.SecretManagerServiceClient') as mock:
            mock_instance = MagicMock()
            mock_instance.access_secret_version.return_value = MagicMock(
                payload=MagicMock(data=b"test-api-key")
            )
            mock.return_value = mock_instance
            yield mock

    def test_successful_conversion(self, sample_docx_file, mock_secret_manager):
        """Test successful DOCX to PDF conversion."""
        with patch('utils.client.requests.post') as mock_post:
            # Configure mock response
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.content = b"mock pdf content"
            mock_post.return_value = mock_response

            # Set environment variables
            os.environ["PROJECT_ID"] = "test-project"
            os.environ["PDF_API_KEY_SECRET"] = "test-pdf-api-key"
            os.environ["PDF_CONVERSION_ENDPOINT"] = "https://example.com/convert"

            # Create client instance
            client = HireableClient()

            # Call the conversion
            result = client.docx_to_pdf(sample_docx_file)

            # Verify response
            assert result.content == b"mock pdf content"
            assert result.status_code == 200

            # Verify request was made correctly
            mock_post.assert_called_once()
            args, kwargs = mock_post.call_args
            assert args[0] == "https://example.com/convert"
            assert "files" in kwargs
            assert "headers" in kwargs
            assert kwargs["headers"] == {"API-Key": "test-api-key"}

            # Clean up environment variables
            del os.environ["PROJECT_ID"]
            del os.environ["PDF_API_KEY_SECRET"]
            del os.environ["PDF_CONVERSION_ENDPOINT"]

    def test_authentication_failure(self, sample_docx_file, mock_secret_manager):
        """Test handling of authentication failures."""
        with patch('utils.client.requests.post') as mock_post:
            # Configure mock to simulate auth failure
            mock_response = MagicMock()
            mock_response.status_code = 401
            mock_response.text = "Unauthorized"
            mock_post.return_value = mock_response

            # Set environment variables
            os.environ["PROJECT_ID"] = "test-project"
            os.environ["PDF_API_KEY_SECRET"] = "test-pdf-api-key"
            os.environ["PDF_CONVERSION_ENDPOINT"] = "https://example.com/convert"

            # Create client instance
            client = HireableClient()

            # Attempt conversion
            with pytest.raises(Exception) as excinfo:
                client.docx_to_pdf(sample_docx_file)

            assert "401" in str(excinfo.value)
            assert "Unauthorized" in str(excinfo.value)

            # Clean up environment variables
            del os.environ["PROJECT_ID"]
            del os.environ["PDF_API_KEY_SECRET"]
            del os.environ["PDF_CONVERSION_ENDPOINT"]

    def test_invalid_file_type(self):
        """Test handling of invalid file type."""
        # Create invalid file
        invalid_file = BytesIO(b"invalid content")
        invalid_file.name = "test.txt"

        # Set environment variables
        os.environ["PROJECT_ID"] = "test-project"
        os.environ["PDF_API_KEY_SECRET"] = "test-pdf-api-key"
        os.environ["PDF_CONVERSION_ENDPOINT"] = "https://example.com/convert"

        # Create client instance
        client = HireableClient()

        # Attempt conversion
        with pytest.raises(ValueError) as excinfo:
            client.docx_to_pdf(invalid_file)

        assert "Invalid file type" in str(excinfo.value)

        # Clean up environment variables
        del os.environ["PROJECT_ID"]
        del os.environ["PDF_API_KEY_SECRET"]
        del os.environ["PDF_CONVERSION_ENDPOINT"]

    def test_missing_file(self):
        """Test handling of missing file."""
        # Set environment variables
        os.environ["PROJECT_ID"] = "test-project"
        os.environ["PDF_API_KEY_SECRET"] = "test-pdf-api-key"
        os.environ["PDF_CONVERSION_ENDPOINT"] = "https://example.com/convert"

        # Create client instance
        client = HireableClient()

        # Attempt conversion with None
        with pytest.raises(ValueError) as excinfo:
            client.docx_to_pdf(None)

        assert "No file provided" in str(excinfo.value)

        # Clean up environment variables
        del os.environ["PROJECT_ID"]
        del os.environ["PDF_API_KEY_SECRET"]
        del os.environ["PDF_CONVERSION_ENDPOINT"]

    def test_large_file_handling(self):
        """Test handling of large files."""
        # Create large file (11MB)
        large_file = BytesIO(b"0" * (11 * 1024 * 1024))
        large_file.name = "large.docx"

        # Set environment variables
        os.environ["PROJECT_ID"] = "test-project"
        os.environ["PDF_API_KEY_SECRET"] = "test-pdf-api-key"
        os.environ["PDF_CONVERSION_ENDPOINT"] = "https://example.com/convert"

        # Create client instance
        client = HireableClient()

        # Attempt conversion
        with pytest.raises(ValueError) as excinfo:
            client.docx_to_pdf(large_file)

        assert "File too large" in str(excinfo.value)

        # Clean up environment variables
        del os.environ["PROJECT_ID"]
        del os.environ["PDF_API_KEY_SECRET"]
        del os.environ["PDF_CONVERSION_ENDPOINT"]

    def test_conversion_error(self, sample_docx_file, mock_secret_manager):
        """Test handling of conversion errors."""
        with patch('utils.client.requests.post') as mock_post:
            # Configure mock to simulate conversion error
            mock_response = MagicMock()
            mock_response.status_code = 500
            mock_response.text = "Conversion failed"
            mock_post.return_value = mock_response

            # Set environment variables
            os.environ["PROJECT_ID"] = "test-project"
            os.environ["PDF_API_KEY_SECRET"] = "test-pdf-api-key"
            os.environ["PDF_CONVERSION_ENDPOINT"] = "https://example.com/convert"

            # Create client instance
            client = HireableClient()

            # Attempt conversion
            with pytest.raises(Exception) as excinfo:
                client.docx_to_pdf(sample_docx_file)

            assert "500" in str(excinfo.value)
            assert "Conversion failed" in str(excinfo.value)

            # Clean up environment variables
            del os.environ["PROJECT_ID"]
            del os.environ["PDF_API_KEY_SECRET"]
            del os.environ["PDF_CONVERSION_ENDPOINT"]

    def test_request_timeout(self, sample_docx_file, mock_secret_manager):
        """Test handling of request timeouts."""
        with patch('utils.client.requests.post') as mock_post:
            # Configure mock to raise timeout
            mock_post.side_effect = requests.Timeout("Request timed out")

            # Set environment variables
            os.environ["PROJECT_ID"] = "test-project"
            os.environ["PDF_API_KEY_SECRET"] = "test-pdf-api-key"
            os.environ["PDF_CONVERSION_ENDPOINT"] = "https://example.com/convert"

            # Create client instance
            client = HireableClient()

            # Attempt conversion
            with pytest.raises(requests.Timeout) as excinfo:
                client.docx_to_pdf(sample_docx_file)

            assert "Request timed out" in str(excinfo.value)

            # Clean up environment variables
            del os.environ["PROJECT_ID"]
            del os.environ["PDF_API_KEY_SECRET"]
            del os.environ["PDF_CONVERSION_ENDPOINT"]

    def test_memory_cleanup(self, sample_docx_file, mock_secret_manager):
        """Test memory cleanup after conversion."""
        with patch('utils.client.requests.post') as mock_post:
            # Configure mock response
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.content = b"mock pdf content"
            mock_post.return_value = mock_response

            # Set environment variables
            os.environ["PROJECT_ID"] = "test-project"
            os.environ["PDF_API_KEY_SECRET"] = "test-pdf-api-key"
            os.environ["PDF_CONVERSION_ENDPOINT"] = "https://example.com/convert"

            # Create client instance
            client = HireableClient()

            # Call the conversion
            result = client.docx_to_pdf(sample_docx_file)

            # Verify response
            assert result.content == b"mock pdf content"

            # Verify file was closed
            assert sample_docx_file.closed

            # Clean up environment variables
            del os.environ["PROJECT_ID"]
            del os.environ["PDF_API_KEY_SECRET"]
            del os.environ["PDF_CONVERSION_ENDPOINT"] 