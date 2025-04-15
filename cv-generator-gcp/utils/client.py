import requests
import logging
import os
import io
from google.cloud import secretmanager
from typing import Optional

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