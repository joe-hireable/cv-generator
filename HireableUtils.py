import uuid, os, json
from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient, generate_blob_sas, BlobSasPermissions, ContentSettings
from azure.keyvault.secrets import SecretClient
from datetime import datetime, timedelta
from functools import lru_cache
from ProfileDto import map_to_dto

class HireableUtils:
    def __init__(self):
        self._connection_string_secret_name = os.getenv("CONNECTION_STRING_SECRET_NAME")
        self._secret_client = SecretClient(vault_url=os.getenv("KEY_VAULT_ENDPOINT"), credential=DefaultAzureCredential())

    @lru_cache(maxsize=None)
    def retrieve_profile_config(self):
        profile = self.retrieve_file_from_blob("cv-generator", os.getenv("PROFILE"))
        return map_to_dto(json.loads(profile))

    def retrieve_file_from_blob(self, container_name, blob_name):
        connection_string = self.get_secret_from_vault(self._connection_string_secret_name)
        blob_client = BlobServiceClient.from_connection_string(connection_string).get_blob_client(container=container_name, blob=blob_name)
        return blob_client.download_blob().readall()
    
    def issue_token(self):
        blob_name = str(uuid.uuid4()) + ".json"
        connection_string = self.get_secret_from_vault(self._connection_string_secret_name)
        blob_service_client = BlobServiceClient.from_connection_string(connection_string)
        container_name = "cv-parser-result"

        # Generate SAS token
        sas_token = generate_blob_sas(
            account_name=blob_service_client.account_name,
            container_name=container_name,
            blob_name=blob_name,
            account_key=blob_service_client.credential.account_key,
            permission=BlobSasPermissions(read=True),
            expiry=datetime.utcnow() + timedelta(hours=1)  # Token expires in 1 hour
        )
        # Construct the download link with SAS token
        return (blob_name, sas_token)

    # Function to upload the CV document to Blob Storage
    def upload_cv_to_blob(self, output_stream, cv_file_path):
        connection_string = self.get_secret_from_vault(self._connection_string_secret_name)
        blob_service_client = BlobServiceClient.from_connection_string(connection_string)
        
        container_client = blob_service_client.get_container_client("generated-cvs")
        
        blob_client = container_client.get_blob_client(cv_file_path)
        
        # Upload the CV file to Blob Storage
        blob_client.upload_blob(
        data=output_stream.getvalue(),  # Provide the byte content of the document
        overwrite=True,
        content_settings=ContentSettings(content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document'))

    def generate_cv_download_link(self, cv_file_path):
        connection_string = self.get_secret_from_vault(self._connection_string_secret_name)
        blob_service_client = BlobServiceClient.from_connection_string(connection_string)

        container_name = "generated-cvs"
        blob_client = blob_service_client.get_blob_client(container=container_name, blob=cv_file_path)

        # Generate SAS token
        sas_token = generate_blob_sas(
            account_name=blob_service_client.account_name,
            container_name=container_name,
            blob_name=cv_file_path,
            account_key=blob_service_client.credential.account_key,
            permission=BlobSasPermissions(read=True),
            expiry=datetime.utcnow() + timedelta(hours=1)  # Token expires in 1 hour
        )

        # Construct the download link with SAS token
        download_link = f"{blob_client.url}?{sas_token}"
        return download_link

    @lru_cache(maxsize=None)
    def get_secret_from_vault(self, secret_name):
        return self._secret_client.get_secret(secret_name).value