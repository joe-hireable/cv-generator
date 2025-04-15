import jwt
import os
import logging
from google.cloud import secretmanager
from typing import Dict, Any, Optional

class SecurityUtils:
    """
    Security utility class for handling authentication and authorization.
    """
    
    def __init__(self, project_id=None):
        """
        Initialize the security utils with the project ID.
        
        Args:
            project_id (str, optional): The Google Cloud project ID.
        """
        self.project_id = project_id or os.environ.get("PROJECT_ID")
        self.secret_client = secretmanager.SecretManagerServiceClient()
    
    def validate_supabase_jwt(self, token: str) -> Dict[str, Any]:
        """
        Validate a Supabase JWT token.
        
        Args:
            token (str): The JWT token to validate.
            
        Returns:
            Dict[str, Any]: The decoded token payload if valid.
            
        Raises:
            ValueError: If the token is invalid or expired.
        """
        try:
            # Get JWT secret from environment or Secret Manager
            jwt_secret = os.environ.get("SUPABASE_JWT_SECRET")
            if not jwt_secret:
                jwt_secret = self._get_secret("SUPABASE_JWT_SECRET")
                
            # Decode and validate the token
            decoded_token = jwt.decode(
                token, 
                jwt_secret, 
                algorithms=["HS256"],
                audience="authenticated"
            )
            
            # Validate that token contains expected claims
            if not decoded_token.get("sub"):
                raise ValueError("Token missing 'sub' claim")
                
            return decoded_token
        except jwt.ExpiredSignatureError:
            logging.error("Token has expired")
            raise ValueError("Authentication token has expired")
        except jwt.InvalidTokenError as e:
            logging.error(f"Invalid token: {str(e)}")
            raise ValueError(f"Invalid authentication token: {str(e)}")
        except Exception as e:
            logging.error(f"Token validation error: {str(e)}")
            raise ValueError(f"Token validation failed: {str(e)}")
    
    def extract_token_from_header(self, auth_header: Optional[str]) -> Optional[str]:
        """
        Extract JWT token from the Authorization header.
        
        Args:
            auth_header (str, optional): The Authorization header value.
            
        Returns:
            str, optional: The extracted token or None if not found.
        """
        if not auth_header:
            return None
            
        parts = auth_header.split()
        if len(parts) != 2 or parts[0].lower() != "bearer":
            return None
            
        return parts[1]
    
    def _get_secret(self, secret_name: str) -> str:
        """
        Get a secret from Secret Manager.
        
        Args:
            secret_name (str): The name of the secret.
            
        Returns:
            str: The secret value.
            
        Raises:
            Exception: If the secret cannot be retrieved.
        """
        try:
            name = f"projects/{self.project_id}/secrets/{secret_name}/versions/latest"
            response = self.secret_client.access_secret_version(name=name)
            return response.payload.data.decode("UTF-8")
        except Exception as e:
            logging.error(f"Failed to retrieve secret {secret_name}: {e}")
            raise 