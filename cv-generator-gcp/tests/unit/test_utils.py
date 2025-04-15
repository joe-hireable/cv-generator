import pytest
import json
import os
from unittest.mock import patch, MagicMock
from io import BytesIO
from datetime import datetime, timedelta
from google.api_core.exceptions import NotFound
from utils.utils import HireableUtils
from utils.profile_dto import Profile

class TestHireableUtils:
    """Test suite for the HireableUtils class."""
    
    @pytest.fixture
    def sample_profile_json(self):
        """Sample profile JSON for testing."""
        return json.dumps({
            "schema": "cv_schema.json",
            "template": "template_WIP.docx",
            "agency_name": "Test Agency",
            "agency_logo": "agency_logo.png"
        })
    
    def test_retrieve_profile_config(self, mock_utils, profile_config):
        """Test retrieving profile configuration."""
        # The mock_utils fixture already configures the return value for retrieve_profile_config
        result = mock_utils.retrieve_profile_config()
        
        # Check that the result matches the expected profile config
        assert isinstance(result, Profile)
        assert result.schema == profile_config.schema
        assert result.template == profile_config.template
        assert result.agency_name == profile_config.agency_name
    
    def test_retrieve_file_from_storage(self, mock_storage_client):
        """Test retrieving a file from Google Cloud Storage."""
        utils = HireableUtils()
        utils.storage_client = mock_storage_client
        utils.bucket_name = "test-bucket"
        
        # Call the method
        result = utils.retrieve_file_from_storage("cv-generator", "template.docx")
        
        # Check that the storage client was called correctly
        mock_storage_client.bucket.assert_called_once_with("test-bucket")
        mock_storage_client.bucket().blob.assert_called_once_with("cv-generator/template.docx")
        mock_storage_client.bucket().blob().download_as_bytes.assert_called_once()
        
        # Check the result
        assert result == b"mock file content"
    
    def test_retrieve_file_from_storage_not_found(self, mock_storage_client):
        """Test retrieving a non-existent file from Google Cloud Storage."""
        # Configure the mock to raise NotFound
        mock_storage_client.bucket().blob().download_as_bytes.side_effect = NotFound("File not found")
        
        utils = HireableUtils()
        utils.storage_client = mock_storage_client
        utils.bucket_name = "test-bucket"
        
        # The method should raise NotFound
        with pytest.raises(NotFound):
            utils.retrieve_file_from_storage("cv-generator", "nonexistent.docx")
    
    def test_upload_cv_to_storage(self, mock_storage_client):
        """Test uploading a CV to Google Cloud Storage."""
        utils = HireableUtils()
        utils.storage_client = mock_storage_client
        utils.bucket_name = "test-bucket"
        
        # Create a sample BytesIO stream
        output_stream = BytesIO(b"test document content")
        cv_file_path = "John Doe CV 2023-05-10.docx"
        
        # Call the method
        result = utils.upload_cv_to_storage(output_stream, cv_file_path)
        
        # Check that the storage client was called correctly
        mock_storage_client.bucket.assert_called_once_with("test-bucket")
        mock_storage_client.bucket().blob.assert_called_once_with(f"generated-cvs/{cv_file_path}")
        
        # Check upload was called with the right content type
        mock_storage_client.bucket().blob().upload_from_string.assert_called_once()
        args, kwargs = mock_storage_client.bucket().blob().upload_from_string.call_args
        assert kwargs["content_type"] == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        
        # For PDF file
        utils.storage_client.reset_mock()
        pdf_file_path = "John Doe CV 2023-05-10.pdf"
        result = utils.upload_cv_to_storage(output_stream, pdf_file_path)
        
        # Check that content type is PDF for PDF files
        args, kwargs = mock_storage_client.bucket().blob().upload_from_string.call_args
        assert kwargs["content_type"] == "application/pdf"
    
    def test_generate_cv_download_link(self, mock_storage_client):
        """Test generating a signed URL for downloading a CV."""
        utils = HireableUtils()
        utils.storage_client = mock_storage_client
        utils.bucket_name = "test-bucket"
        
        cv_file_path = "John Doe CV 2023-05-10.docx"
        
        # Call the method
        result = utils.generate_cv_download_link(cv_file_path)
        
        # Check that the storage client was called correctly
        mock_storage_client.bucket.assert_called_once_with("test-bucket")
        mock_storage_client.bucket().blob.assert_called_once_with(f"generated-cvs/{cv_file_path}")
        mock_storage_client.bucket().blob().generate_signed_url.assert_called_once()
        
        # Verify the result
        assert result == "https://storage.googleapis.com/test-bucket/generated-cvs/test-file.pdf?signature"
    
    def test_issue_token(self, mock_storage_client):
        """Test generating a token and signed URL for file upload."""
        # Reset mock to clear any previous calls
        mock_storage_client.reset_mock()
        
        utils = HireableUtils()
        utils.storage_client = mock_storage_client
        utils.bucket_name = "test-bucket"
        
        # Set up the mock bucket and blob
        mock_bucket = MagicMock()
        mock_blob = MagicMock()
        mock_bucket.blob.return_value = mock_blob
        mock_storage_client.bucket.return_value = mock_bucket
        mock_blob.generate_signed_url.return_value = "https://signed-url.example.com"
        
        # Call the method
        blob_name, url = utils.issue_token()
        
        # Check that the blob name starts with cv-parser-result
        assert blob_name.startswith("cv-parser-result/")
        
        # Check that the storage client was called correctly
        mock_storage_client.bucket.assert_called_once_with("test-bucket")
        mock_bucket.blob.assert_called_once()
        
        # Verify the URL
        assert url == "https://signed-url.example.com"
    
    @patch('utils.utils.secretmanager.SecretManagerServiceClient')
    def test_get_secret(self, mock_secret_client_class, mock_storage_client):
        """Test retrieving a secret from Secret Manager."""
        # Configure the mock secret client
        mock_secret_client = MagicMock()
        mock_secret_response = MagicMock()
        mock_secret_response.payload.data.decode.return_value = "test-secret-value"
        mock_secret_client.access_secret_version.return_value = mock_secret_response
        mock_secret_client_class.return_value = mock_secret_client
        
        utils = HireableUtils()
        utils.project_id = "test-project"
        utils.secret_client = mock_secret_client
        
        # Call the method
        result = utils.get_secret("test-secret")
        
        # Check that the secret client was called correctly
        mock_secret_client.access_secret_version.assert_called_once_with(
            name="projects/test-project/secrets/test-secret/versions/latest"
        )
        
        # Verify the result
        assert result == "test-secret-value" 