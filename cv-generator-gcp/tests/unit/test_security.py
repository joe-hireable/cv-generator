import pytest
import os
import jwt
from unittest.mock import patch, MagicMock
from utils.security import SecurityUtils
from datetime import datetime, timedelta

class TestSecurityUtils:
    """Test suite for the SecurityUtils class."""
    
    @patch("utils.security.secretmanager.SecretManagerServiceClient")
    def test_init(self, mock_client):
        """Test initialization of SecurityUtils."""
        # Test with project_id provided
        security = SecurityUtils(project_id="test-project")
        assert security.project_id == "test-project"
        
        # Test with project_id from environment
        with patch.dict(os.environ, {"PROJECT_ID": "env-project"}):
            security = SecurityUtils()
            assert security.project_id == "env-project"
    
    @patch.dict(os.environ, {"SUPABASE_JWT_SECRET": "test-secret"})
    def test_validate_supabase_jwt_valid(self):
        """Test validation of a valid Supabase JWT token."""
        security = SecurityUtils(project_id="test-project")
        
        # Create a valid token
        payload = {
            "sub": "user-123",
            "email": "user@example.com",
            "aud": "authenticated",
            "exp": datetime.utcnow() + timedelta(hours=1)
        }
        token = jwt.encode(payload, "test-secret", algorithm="HS256")
        
        # Validate the token
        decoded = security.validate_supabase_jwt(token)
        
        assert decoded["sub"] == "user-123"
        assert decoded["email"] == "user@example.com"
    
    @patch.dict(os.environ, {"SUPABASE_JWT_SECRET": "test-secret"})
    def test_validate_supabase_jwt_expired(self):
        """Test validation of an expired JWT token."""
        security = SecurityUtils(project_id="test-project")
        
        # Create an expired token
        payload = {
            "sub": "user-123",
            "email": "user@example.com",
            "aud": "authenticated",
            "exp": datetime.utcnow() - timedelta(hours=1)
        }
        token = jwt.encode(payload, "test-secret", algorithm="HS256")
        
        # Validate the token
        with pytest.raises(ValueError, match="Authentication token has expired"):
            security.validate_supabase_jwt(token)
    
    @patch.dict(os.environ, {"SUPABASE_JWT_SECRET": "test-secret"})
    def test_validate_supabase_jwt_invalid(self):
        """Test validation of an invalid JWT token."""
        security = SecurityUtils(project_id="test-project")
        
        # Create a token with wrong signature
        payload = {
            "sub": "user-123",
            "email": "user@example.com",
            "aud": "authenticated",
            "exp": datetime.utcnow() + timedelta(hours=1)
        }
        token = jwt.encode(payload, "wrong-secret", algorithm="HS256")
        
        # Validate the token
        with pytest.raises(ValueError, match="Invalid authentication token"):
            security.validate_supabase_jwt(token)
    
    @patch.dict(os.environ, {"SUPABASE_JWT_SECRET": "test-secret"})
    def test_validate_supabase_jwt_missing_sub(self):
        """Test validation of a JWT token without sub claim."""
        security = SecurityUtils(project_id="test-project")
        
        # Create a token without sub claim
        payload = {
            "email": "user@example.com",
            "aud": "authenticated",
            "exp": datetime.utcnow() + timedelta(hours=1)
        }
        token = jwt.encode(payload, "test-secret", algorithm="HS256")
        
        # Validate the token
        with pytest.raises(ValueError, match="Token missing 'sub' claim"):
            security.validate_supabase_jwt(token)
    
    def test_extract_token_from_header(self):
        """Test extracting a token from the Authorization header."""
        security = SecurityUtils(project_id="test-project")
        
        # Valid token
        assert security.extract_token_from_header("Bearer token123") == "token123"
        
        # Invalid format
        assert security.extract_token_from_header("token123") is None
        assert security.extract_token_from_header("bearer token123") == "token123"  # Case-insensitive
        assert security.extract_token_from_header("Basic token123") is None
        
        # None or empty
        assert security.extract_token_from_header(None) is None
        assert security.extract_token_from_header("") is None
    
    @patch("utils.security.secretmanager.SecretManagerServiceClient")
    def test_get_secret(self, mock_client):
        """Test getting a secret from Secret Manager."""
        # Mock the response
        mock_response = MagicMock()
        mock_response.payload.data.decode.return_value = "secret-value"
        
        # Mock the client
        mock_instance = mock_client.return_value
        mock_instance.access_secret_version.return_value = mock_response
        
        # Test getting a secret
        security = SecurityUtils(project_id="test-project")
        result = security._get_secret("test-secret")
        
        assert result == "secret-value"
        mock_instance.access_secret_version.assert_called_once_with(
            name="projects/test-project/secrets/test-secret/versions/latest"
        ) 