import requests
import logging
import os
import io
from google.cloud import secretmanager
from typing import Optional, Dict, Any, BinaryIO

class HireableClient:
    """
    Client for interacting with external services, primarily for DOCX to PDF conversion.
    """
    
    def __init__(self):
        """
        Initialize the HireableClient with necessary configuration.
        """
        # If PDF API key is stored in Secret Manager, retrieve it
        project_id = os.environ.get("PROJECT_ID")
        pdf_api_key_secret = os.environ.get("PDF_API_KEY_SECRET")
        
        self.pdf_api_key = None
        if project_id and pdf_api_key_secret:
            try:
                secret_client = secretmanager.SecretManagerServiceClient()
                secret_name = f"projects/{project_id}/secrets/{pdf_api_key_secret}/versions/latest"
                response = secret_client.access_secret_version(name=secret_name)
                self.pdf_api_key = response.payload.data.decode("UTF-8")
            except Exception as e:
                logging.error(f"Failed to retrieve PDF API Key: {e}")
        
        # Set the PDF conversion endpoint
        self.pdf_conversion_endpoint = os.environ.get("PDF_CONVERSION_ENDPOINT", "https://docx2pdf.tombrown.io/convert")
        
        # Set the CV Parser endpoint
        self.cv_parser_endpoint = os.environ.get("CV_PARSER_URL", "")
        
    def docx_to_pdf(self, docx_stream):
        """
        Convert a DOCX file to PDF using an external API.
        
        Args:
            docx_stream (BytesIO): The DOCX file as a byte stream.
            
        Returns:
            Response: The API response containing the PDF.
        """
        files = {
            'file': ("doc.docx", docx_stream, 'application/vnd.openxmlformats-officedocument.wordprocessingml.document')
        }
        
        headers = {}
        if self.pdf_api_key:
            headers['API-Key'] = self.pdf_api_key
            
        try:
            response = requests.post(
                self.pdf_conversion_endpoint, 
                files=files, 
                headers=headers,
                timeout=60
            )
            
            if response.status_code != 200:
                logging.error(f"PDF conversion failed: {response.status_code} - {response.text}")
                raise Exception(f"PDF conversion failed: {response.status_code}")
                
            return response
        except Exception as e:
            logging.error(f"Error converting DOCX to PDF: {e}")
            raise
    
    def forward_to_parser_service(self, url: str, form_data: Dict[str, Any], files: Dict[str, tuple], headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        Forward a request to the CV Parser service.
        
        Args:
            url (str): The URL to forward the request to.
            form_data (Dict[str, Any]): The form data to send.
            files (Dict[str, tuple]): The files to send.
            headers (Dict[str, str], optional): Additional headers.
            
        Returns:
            Dict[str, Any]: The response from the parser service.
            
        Raises:
            Exception: If the request fails.
        """
        try:
            # If URL not provided, use the default endpoint
            if not url and self.cv_parser_endpoint:
                url = self.cv_parser_endpoint
            
            if not url:
                raise ValueError("CV Parser URL not configured")
                
            # Prepare headers
            request_headers = {}
            if headers:
                request_headers.update(headers)
            
            # Send request to parser service
            response = requests.post(
                url,
                data=form_data,
                files=files,
                headers=request_headers,
                timeout=120  # Longer timeout for CV parsing which can take time
            )
            
            # Check response status
            if response.status_code != 200:
                logging.error(f"Parser service error: {response.status_code} - {response.text}")
                return {"error": f"Parser service error: {response.status_code}"}
                
            # Return JSON response
            return response.json()
        except Exception as e:
            logging.error(f"Error forwarding to parser service: {e}")
            raise
    
    def parse_cv(self, cv_file: BinaryIO, job_description: Optional[str] = None, task: str = "parsing", auth_header: Optional[str] = None) -> Dict[str, Any]:
        """
        Parse a CV using the CV Parser service.
        
        Args:
            cv_file (BinaryIO): The CV file to parse.
            job_description (str, optional): Optional job description for matching.
            task (str): The parsing task (default: "parsing").
            auth_header (str, optional): Optional authorization header.
            
        Returns:
            Dict[str, Any]: The parsed CV data.
            
        Raises:
            Exception: If the parsing fails.
        """
        # Prepare form data
        form_data = {"task": task}
        
        if job_description:
            form_data["jd"] = job_description
            
        # Prepare files
        filename = getattr(cv_file, 'name', 'cv.pdf')
        content_type = self._get_content_type(filename)
        
        files = {
            "cv_file": (filename, cv_file, content_type)
        }
        
        # Prepare headers
        headers = {}
        if auth_header:
            headers['Authorization'] = auth_header
            
        # Call parser service
        return self.forward_to_parser_service(self.cv_parser_endpoint, form_data, files, headers)
        
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
        logging.info(f"Notification would be sent to {to_email} with subject: {subject}")
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