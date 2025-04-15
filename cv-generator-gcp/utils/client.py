import requests
import logging
import os
import io
import json
from google.cloud import secretmanager
from typing import Optional, Dict, Any, BinaryIO
from google.cloud import storage
from google.auth import default
from google.auth.transport.requests import Request
from google.oauth2 import service_account

class HireableClient:
    """
    Client for interacting with external services, primarily for DOCX to PDF conversion.
    """
    
    def __init__(self):
        """
        Initialize the HireableClient with necessary configuration.
        """
        # Configure logging first
        self.logger = logging.getLogger(__name__)
        
        # Initialize configuration
        self.project_id = os.getenv("PROJECT_ID")
        self.storage_bucket_name = os.getenv("STORAGE_BUCKET_NAME")
        self.pdf_conversion_endpoint = os.getenv("PDF_CONVERSION_ENDPOINT")
        self.parser_api_endpoint = os.getenv("CV_PARSER_URL")
        
        # Initialize storage client
        self.storage_client = storage.Client()
        
        # Get API key from secret manager
        self.pdf_api_key = self._get_api_key()
        
    def _get_api_key(self) -> Optional[str]:
        """Get API key from Secret Manager."""
        try:
            if not self.project_id:
                self.logger.warning("Project ID not configured")
                return None
                
            secret_id = os.getenv("PDF_API_KEY_SECRET")
            if not secret_id:
                self.logger.warning("PDF API key secret not configured")
                return None

            client = secretmanager.SecretManagerServiceClient()
            name = f"projects/{self.project_id}/secrets/{secret_id}/versions/latest"
            response = client.access_secret_version(name=name)
            return response.payload.data.decode("UTF-8")
        except Exception as e:
            self.logger.error(f"Error retrieving API key: {str(e)}")
            return None
        
    def docx_to_pdf(self, file: BinaryIO, max_retries: int = 3) -> requests.Response:
        """Convert DOCX file to PDF using Cloud Function."""
        if not file:
            raise ValueError("No file provided")

        # Validate file type
        if not hasattr(file, 'name'):
            # For BytesIO objects in tests, provide a default name
            file.name = "document.docx"
            
        file_ext = os.path.splitext(file.name.lower())[1]
        if file_ext not in ['.docx', '.doc', '.rtf']:
            raise ValueError(f"Invalid file type: {file_ext}. Must be .docx, .doc, or .rtf")

        # Check file size (10MB limit)
        file.seek(0, 2)  # Seek to end
        size = file.tell()
        file.seek(0)  # Reset to beginning
        
        if size > 10 * 1024 * 1024:  # 10MB
            raise ValueError("File too large. Maximum size is 10MB")

        headers = {}
        if self.pdf_api_key:
            headers["API-Key"] = self.pdf_api_key

        # Determine correct content type based on file extension
        content_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        if file_ext == '.doc':
            content_type = "application/msword"
        elif file_ext == '.rtf':
            content_type = "application/rtf"

        retry_count = 0
        last_error = None
        should_close_file = True  # For backwards compatibility with tests

        try:
            while retry_count < max_retries:
                try:
                    file_name = getattr(file, 'name', 'document.docx')
                    # Update content type based on actual file name for tests
                    if file_name.lower().endswith('.doc'):
                        content_type = "application/msword"
                    elif file_name.lower().endswith('.rtf'):
                        content_type = "application/rtf"
                        
                    response = requests.post(
                        self.pdf_conversion_endpoint,
                        files={"file": (file_name, file, content_type)},
                        headers=headers,
                        timeout=60
                    )

                    if response.status_code == 200:
                        return response

                    error_msg = f"PDF conversion failed: {response.status_code}"
                    if response.text:
                        error_msg += f" - {response.text}"
                    self.logger.error(error_msg)
                    raise Exception(error_msg)

                except (requests.Timeout, requests.ConnectionError) as e:
                    last_error = e
                    retry_count += 1
                    if retry_count < max_retries:
                        self.logger.warning(f"Retry {retry_count}/{max_retries} after error: {str(e)}")
                        # Reopen the file for retry if it was closed
                        if file.closed:
                            file.seek(0)
                        continue
                    break
                except Exception as e:
                    self.logger.error(f"Error converting DOCX to PDF: {str(e)}")
                    raise
        finally:
            # Close the file if it should be closed and is not already closed
            if should_close_file and not file.closed:
                file.close()

        if last_error:
            self.logger.error(f"Error converting DOCX to PDF: {str(last_error)}")
            raise last_error
        else:
            raise Exception("PDF conversion failed after all retries")
    
    def parse_cv(self, file_content=None, file_name=None, cv_file=None, job_description=None, task="parsing", auth_header=None) -> Dict[str, Any]:
        """Parse CV content using the parser service.
        
        Args:
            file_content: The CV content as bytes (legacy mode)
            file_name: The CV filename (legacy mode)
            cv_file: A file-like object containing the CV (preferred)
            job_description: Optional job description for matching
            task: The parsing task (parsing, scoring, etc.)
            auth_header: Optional authorization header
            
        Returns:
            Dict containing the parsed CV data
        """
        try:
            headers = {}
            if auth_header:
                headers["Authorization"] = auth_header
                
            if cv_file:
                # New method: use multipart/form-data with file
                files = {"cv_file": (getattr(cv_file, 'name', 'cv.pdf'), cv_file)}
                data = {}
                
                if job_description:
                    data["jobDescription"] = job_description
                if task:
                    data["task"] = task
                    
                response = requests.post(
                    self.parser_api_endpoint,
                    files=files,
                    data=data,
                    headers=headers,
                    timeout=60
                )
            else:
                # Legacy method: use JSON with file content
                payload = {
                    "fileContent": file_content if isinstance(file_content, str) else file_content.decode('utf-8', errors='ignore'),
                    "fileName": file_name
                }
                
                if job_description:
                    payload["jobDescription"] = job_description
                if task:
                    payload["task"] = task
                    
                response = requests.post(
                    self.parser_api_endpoint,
                    json=payload,
                    headers=headers,
                    timeout=60
                )

            if response.status_code != 200:
                error_msg = f"Parser service error: {response.status_code}"
                if response.text:
                    error_msg += f" - {response.text}"
                self.logger.error(error_msg)
                raise Exception(error_msg)

            return response.json()

        except Exception as e:
            self.logger.error(f"Error parsing CV: {str(e)}")
            raise
    
    def send_notification(self, to_email: str, subject: str, message: str, attachment: Optional[io.BytesIO] = None, attachment_name: Optional[str] = None):
        """
        Send an email notification with optional attachment.
        This is a placeholder for future implementation.
        
        Args:
            to_email (str): Recipient email address.
            subject (str): Email subject.
            message (str): Email message body.
            attachment (BytesIO, optional): Optional file attachment.
            attachment_name (str, optional): Name for the attachment.
            
        Returns:
            bool: True if the notification was sent successfully, False otherwise.
        """
        # This is a placeholder for email notification functionality
        # Implementation would depend on your preferred email service
        self.logger.info(f"Notification would be sent to {to_email} with subject: {subject}")
        return True
        
    def _get_content_type(self, filename: str) -> str:
        """
        Get the content type for a file based on its extension.
        
        Args:
            filename (str): The filename.
            
        Returns:
            str: The content type.
        """
        if filename.lower().endswith('.pdf'):
            return 'application/pdf'
        elif filename.lower().endswith('.docx'):
            return 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        elif filename.lower().endswith('.doc'):
            return 'application/msword'
        elif filename.lower().endswith('.txt'):
            return 'text/plain'
        else:
            return 'application/octet-stream' 