import pytest
from unittest.mock import patch, MagicMock
from io import BytesIO
import requests
from utils.client import HireableClient

class TestClientAuthentication:
    """Test suite for client authentication and timeout handling."""

    @pytest.fixture
    def client(self):
        """Create a HireableClient instance."""
        return HireableClient()

    @pytest.fixture
    def sample_docx(self):
        """Create a sample DOCX file."""
        return BytesIO(b"test docx content")

    def test_authentication_failure(self, client, sample_docx):
        """Test handling of authentication failures."""
        with patch('utils.client.requests.post') as mock_post:
            # Configure mock to simulate authentication failure
            mock_response = MagicMock()
            mock_response.status_code = 401
            mock_response.text = "Unauthorized"
            mock_post.return_value = mock_response

            # Attempt to convert document
            with pytest.raises(Exception) as excinfo:
                client.docx_to_pdf(sample_docx)
            
            assert "401" in str(excinfo.value)
            assert "Unauthorized" in str(excinfo.value)

    def test_invalid_api_key(self, client, sample_docx):
        """Test handling of invalid API key."""
        client.pdf_api_key = "invalid-key"
        
        with patch('utils.client.requests.post') as mock_post:
            # Configure mock to simulate invalid API key
            mock_response = MagicMock()
            mock_response.status_code = 403
            mock_response.text = "Invalid API key"
            mock_post.return_value = mock_response

            # Attempt to convert document
            with pytest.raises(Exception) as excinfo:
                client.docx_to_pdf(sample_docx)
            
            assert "403" in str(excinfo.value)
            assert "Invalid API key" in str(excinfo.value)

    def test_request_timeout(self, client, sample_docx):
        """Test handling of request timeouts."""
        with patch('utils.client.requests.post') as mock_post:
            # Configure mock to simulate timeout
            mock_post.side_effect = requests.Timeout("Request timed out")

            # Attempt to convert document
            with pytest.raises(requests.Timeout) as excinfo:
                client.docx_to_pdf(sample_docx)
            
            assert "Request timed out" in str(excinfo.value)

    def test_connection_error(self, client, sample_docx):
        """Test handling of connection errors."""
        with patch('utils.client.requests.post') as mock_post:
            # Configure mock to simulate connection error
            mock_post.side_effect = requests.ConnectionError("Connection failed")

            # Attempt to convert document
            with pytest.raises(requests.ConnectionError) as excinfo:
                client.docx_to_pdf(sample_docx)
            
            assert "Connection failed" in str(excinfo.value)

    def test_retry_on_timeout(self, client, sample_docx):
        """Test retry mechanism on timeout."""
        with patch('utils.client.requests.post') as mock_post:
            # Configure mock to fail once then succeed
            mock_post.side_effect = [
                requests.Timeout("Request timed out"),
                MagicMock(status_code=200, content=b"success")
            ]

            # Attempt to convert document
            result = client.docx_to_pdf(sample_docx)
            
            # Verify that the request was made twice
            assert mock_post.call_count == 2
            assert result.status_code == 200

    def test_retry_on_connection_error(self, client, sample_docx):
        """Test retry mechanism on connection error."""
        with patch('utils.client.requests.post') as mock_post:
            # Configure mock to fail once then succeed
            mock_post.side_effect = [
                requests.ConnectionError("Connection failed"),
                MagicMock(status_code=200, content=b"success")
            ]

            # Attempt to convert document
            result = client.docx_to_pdf(sample_docx)
            
            # Verify that the request was made twice
            assert mock_post.call_count == 2
            assert result.status_code == 200

    def test_max_retries_exceeded(self, client, sample_docx):
        """Test behavior when max retries are exceeded."""
        with patch('utils.client.requests.post') as mock_post:
            # Configure mock to always timeout
            mock_post.side_effect = requests.Timeout("Request timed out")

            # Attempt to convert document
            with pytest.raises(requests.Timeout) as excinfo:
                client.docx_to_pdf(sample_docx)
            
            # Verify that the request was made the maximum number of times
            assert mock_post.call_count == 3  # Assuming max_retries=3
            assert "Request timed out" in str(excinfo.value)

    def test_different_file_types(self, client):
        """Test handling of different file types."""
        file_types = [
            ("test.docx", b"docx content", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
            ("test.doc", b"doc content", "application/msword"),
            ("test.rtf", b"rtf content", "application/rtf")
        ]

        for idx, (filename, content, mime_type) in enumerate(file_types):
            with patch('utils.client.requests.post') as mock_post:
                # Configure mock for successful response
                mock_post.return_value = MagicMock(status_code=200, content=b"success")
                
                # Create file with specific type and name
                test_file = BytesIO(content)
                test_file.name = filename
                
                # Attempt conversion
                result = client.docx_to_pdf(test_file)
                
                # Verify request was made with correct content type
                args, kwargs = mock_post.call_args
                assert "files" in kwargs
                assert kwargs["files"]["file"][2] == mime_type, f"File type test {idx}: expected {mime_type}"
                assert result.status_code == 200

    def test_different_file_sizes(self, client):
        """Test handling of different file sizes."""
        sizes = [
            (1024, "1KB"),  # Small file
            (1024 * 1024, "1MB"),  # Medium file
            (5 * 1024 * 1024, "5MB")  # Large file
        ]

        for size, description in sizes:
            with patch('utils.client.requests.post') as mock_post:
                # Configure mock for successful response
                mock_post.return_value = MagicMock(status_code=200, content=b"success")
                
                # Create file with specific size
                test_file = BytesIO(b"0" * size)
                
                # Attempt conversion
                result = client.docx_to_pdf(test_file)
                
                # Verify request was made successfully
                assert result.status_code == 200
                assert mock_post.call_count == 1 