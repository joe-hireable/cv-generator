import os
import pytest
from unittest.mock import patch, MagicMock
from io import BytesIO
from utils.client import HireableClient

class TestHireableClient:
    """Test suite for the HireableClient class."""
    
    @pytest.fixture
    def sample_docx(self):
        """Sample DOCX content for testing."""
        return BytesIO(b"test docx content")
    
    @patch('utils.client.secretmanager.SecretManagerServiceClient')
    def test_init_with_api_key(self, mock_secret_client_class):
        """Test initialization with API key retrieval."""
        # Set environment variables
        os.environ["PROJECT_ID"] = "test-project"
        os.environ["PDF_API_KEY_SECRET"] = "test-pdf-api-key"
        
        # Configure the mock secret client
        mock_secret_client = MagicMock()
        mock_secret_response = MagicMock()
        mock_secret_response.payload.data.decode.return_value = "test-api-key"
        mock_secret_client.access_secret_version.return_value = mock_secret_response
        mock_secret_client_class.return_value = mock_secret_client
        
        # Create client instance
        client = HireableClient()
        
        # Check that the API key was retrieved correctly
        mock_secret_client.access_secret_version.assert_called_once_with(
            name="projects/test-project/secrets/test-pdf-api-key/versions/latest"
        )
        assert client.pdf_api_key == "test-api-key"
        
        # Clean up environment variables
        del os.environ["PROJECT_ID"]
        del os.environ["PDF_API_KEY_SECRET"]
    
    def test_init_without_api_key(self):
        """Test initialization without API key retrieval."""
        # Ensure environment variables are not set
        if "PROJECT_ID" in os.environ:
            del os.environ["PROJECT_ID"]
        if "PDF_API_KEY_SECRET" in os.environ:
            del os.environ["PDF_API_KEY_SECRET"]
        
        # Create client instance
        client = HireableClient()
        
        # Check that the API key was not set
        assert client.pdf_api_key is None
    
    @patch('utils.client.requests.post')
    def test_docx_to_pdf_success(self, mock_post, sample_docx):
        """Test successful DOCX to PDF conversion."""
        # Configure mock response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b"mock pdf content"
        mock_post.return_value = mock_response
        
        client = HireableClient()
        client.pdf_api_key = "test-api-key"
        
        # Call the method
        result = client.docx_to_pdf(sample_docx)
        
        # Check that the POST request was made correctly
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        assert args[0] == client.pdf_conversion_endpoint
        assert "files" in kwargs
        assert "headers" in kwargs
        assert kwargs["headers"] == {"API-Key": "test-api-key"}
        
        # Verify the result
        assert result == mock_response
        assert result.content == b"mock pdf content"
    
    @patch('utils.client.requests.post')
    def test_docx_to_pdf_error(self, mock_post, sample_docx):
        """Test error handling in DOCX to PDF conversion."""
        # Configure mock response
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = "Bad Request"
        mock_post.return_value = mock_response
        
        client = HireableClient()
        
        # The method should raise an exception for non-200 status code
        with pytest.raises(Exception) as excinfo:
            client.docx_to_pdf(sample_docx)
        
        # Check that the error message contains the status code
        assert "400" in str(excinfo.value)
    
    @patch('utils.client.requests.post')
    def test_docx_to_pdf_request_exception(self, mock_post, sample_docx):
        """Test handling of request exceptions in DOCX to PDF conversion."""
        # Configure the mock to raise an exception
        mock_post.side_effect = Exception("Connection error")
        
        client = HireableClient()
        
        # The method should re-raise the exception
        with pytest.raises(Exception) as excinfo:
            client.docx_to_pdf(sample_docx)
        
        # Check that the error message is preserved
        assert "Connection error" in str(excinfo.value)
    
    def test_send_notification(self):
        """Test the send_notification method (placeholder implementation)."""
        client = HireableClient()
        
        # Basic test for the placeholder implementation
        result = client.send_notification(
            to_email="test@example.com",
            subject="Test Subject",
            message="Test Message"
        )
        
        # Should return True for the placeholder implementation
        assert result is True 