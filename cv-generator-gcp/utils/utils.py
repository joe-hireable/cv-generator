import os
import json
import uuid
import logging
from datetime import datetime, timedelta
from functools import lru_cache
from google.cloud import storage
from google.cloud import secretmanager
from google.api_core.exceptions import NotFound
from .profile_dto import Profile, map_to_dto

class HireableUtils:
    """
    Utility class for Google Cloud Storage operations and other GCP specific functionality.
    """
    
    def __init__(self):
        """
        Initialize the HireableUtils with necessary configuration.
        """
        self.project_id = os.environ.get("PROJECT_ID")
        self.bucket_name = os.environ.get("STORAGE_BUCKET_NAME")
        
        # Initialize Google Cloud Storage client
        self.storage_client = storage.Client()
        
        # Initialize Secret Manager client
        self.secret_client = secretmanager.SecretManagerServiceClient()
        
        # Set profile configuration path
        self.profile_path = os.environ.get("PROFILE_CONFIG_PATH", "cv-generator/profile.json")
    
    @lru_cache(maxsize=None)
    def retrieve_profile_config(self):
        """
        Retrieve and cache the profile configuration from Google Cloud Storage.
        
        Returns:
            Profile: The profile configuration.
        """
        profile_json = self.retrieve_file_from_storage("cv-generator", os.environ.get("PROFILE", "profile.json"))
        return map_to_dto(json.loads(profile_json))
    
    def retrieve_file_from_storage(self, folder_name, blob_name):
        """
        Retrieve a file from Google Cloud Storage.
        
        Args:
            folder_name (str): The folder name in the storage bucket.
            blob_name (str): The name of the blob to retrieve.
            
        Returns:
            bytes: The content of the retrieved file.
        """
        bucket = self.storage_client.bucket(self.bucket_name)
        blob_path = f"{folder_name}/{blob_name}"
        blob = bucket.blob(blob_path)
        
        try:
            return blob.download_as_bytes()
        except NotFound:
            logging.error(f"File not found in Google Cloud Storage: {blob_path}")
            raise
    
    def upload_cv_to_storage(self, output_stream, cv_file_path):
        """
        Upload a CV document to Google Cloud Storage.
        
        Args:
            output_stream (BytesIO): The document content as a byte stream.
            cv_file_path (str): The path where the file will be stored.
            
        Returns:
            str: The path to the uploaded file.
        """
        bucket = self.storage_client.bucket(self.bucket_name)
        blob_path = f"generated-cvs/{cv_file_path}"
        blob = bucket.blob(blob_path)
        
        content_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        if cv_file_path.endswith(".pdf"):
            content_type = "application/pdf"
            
        blob.upload_from_string(
            output_stream.getvalue(),
            content_type=content_type
        )
        
        logging.info(f"Uploaded CV to Google Cloud Storage: {blob_path}")
        return blob_path
    
    def generate_cv_download_link(self, cv_file_path):
        """
        Generate a signed URL for downloading a CV from Google Cloud Storage.
        
        Args:
            cv_file_path (str): The path to the CV file.
            
        Returns:
            str: The signed download URL.
        """
        bucket = self.storage_client.bucket(self.bucket_name)
        blob_path = f"generated-cvs/{cv_file_path}"
        blob = bucket.blob(blob_path)
        
        # Generate a signed URL that expires in 1 hour
        url = blob.generate_signed_url(
            version="v4",
            expiration=datetime.utcnow() + timedelta(hours=1),
            method="GET"
        )
        
        return url
    
    def issue_token(self):
        """
        Generate a unique token and a signed URL for file upload.
        
        Returns:
            tuple: (blob_name, signed_url) for uploading a file.
        """
        blob_name = f"cv-parser-result/{str(uuid.uuid4())}.json"
        bucket = self.storage_client.bucket(self.bucket_name)
        blob = bucket.blob(blob_name)
        
        # Generate a signed URL for uploading
        url = blob.generate_signed_url(
            version="v4",
            expiration=datetime.utcnow() + timedelta(hours=1),
            method="PUT",
            content_type="application/json",
        )
        
        return (blob_name, url)
    
    @lru_cache(maxsize=None)
    def get_secret(self, secret_name):
        """
        Retrieve a secret from Google Cloud Secret Manager.
        
        Args:
            secret_name (str): The name of the secret to retrieve.
            
        Returns:
            str: The secret value.
        """
        try:
            name = f"projects/{self.project_id}/secrets/{secret_name}/versions/latest"
            response = self.secret_client.access_secret_version(name=name)
            return response.payload.data.decode("UTF-8")
        except Exception as e:
            logging.error(f"Failed to retrieve secret {secret_name}: {e}")
            raise 