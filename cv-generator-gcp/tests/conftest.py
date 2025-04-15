import os
import json
import pytest
from io import BytesIO
from unittest.mock import MagicMock, patch
from google.cloud import storage
from google.cloud import secretmanager
from docxtpl import DocxTemplate
from models.schema import CVGenerationRequest
from utils.validation import Validation
from utils.client import HireableClient
from utils.utils import HireableUtils
from utils.profile_dto import Profile
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

def pytest_configure(config):
    """Configure pytest with live testing marker."""
    config.addinivalue_line(
        "markers", "live: mark test as requiring live service connection"
    )
    # Set TESTING environment variable to true for all tests
    os.environ["TESTING"] = "true"

@pytest.fixture
def mock_env_vars():
    """Fixture to set environment variables for testing."""
    original_environ = os.environ.copy()
    os.environ["PROJECT_ID"] = "test-project"
    os.environ["STORAGE_BUCKET_NAME"] = "test-bucket"
    os.environ["PROFILE"] = "profile.json"
    yield
    os.environ.clear()
    os.environ.update(original_environ)

@pytest.fixture
def valid_cv_request():
    """Fixture with a valid CV generation request."""
    return {
        "template": "template_WIP.docx",
        "outputFormat": "pdf",
        "sectionOrder": [
            "personal_info",
            "profile_statement",
            "skills",
            "experience",
            "education"
        ],
        "sectionVisibility": {
            "personal_info": True,
            "profile_statement": True,
            "skills": True,
            "experience": True,
            "education": True,
            "certifications": False,
            "achievements": True
        },
        "isAnonymized": False,
        "recruiterProfile": {
            "firstName": "Jane",
            "lastName": "Smith",
            "email": "jane.smith@example.com",
            "phone": "+44 1234 567890",
            "agencyName": "Hireable Recruiting",
            "agencyLogo": "https://example.com/logo.png",
            "website": "https://example.com"
        },
        "data": {
            "firstName": "John",
            "surname": "Doe",
            "email": "john.doe@example.com",
            "phone": "+44 9876 543210",
            "address": "London, UK",
            "linkedin": "linkedin.com/in/johndoe",
            "profileStatement": "Experienced software engineer with 10+ years in full-stack development...",
            "skills": ["Python", "JavaScript", "Cloud Computing", "Agile Development"],
            "experience": [
                {
                    "role": "Senior Developer",
                    "company": "Tech Solutions Ltd",
                    "startDate": "2018-01",
                    "endDate": "2023-05",
                    "description": "Led development team in creating scalable applications..."
                }
            ],
            "education": [
                {
                    "institution": "University of Technology",
                    "degree": "BSc Computer Science",
                    "startDate": "2013",
                    "endDate": "2017",
                    "grade": "First Class Honours"
                }
            ]
        }
    }

@pytest.fixture
def invalid_cv_request():
    """Fixture with an invalid CV generation request (missing required fields)."""
    return {
        "template": "template_WIP.docx",
        "outputFormat": "pdf",
        "sectionVisibility": {
            "personal_info": True,
        },
        "data": {
            # Missing required 'surname' field
            "firstName": "John",
            "email": "john.doe@example.com"
        }
    }

@pytest.fixture
def profile_config():
    """Fixture with a mock profile configuration."""
    return Profile(
        schema_file="cv_schema.json",
        template="template_WIP.docx",
        agency_name="Test Agency",
        agency_logo="agency_logo.png"
    )

@pytest.fixture
def mock_storage_client():
    """Mock Google Cloud Storage client."""
    mock_client = MagicMock()
    mock_bucket = MagicMock()
    mock_blob = MagicMock()
    
    # Configure the mock download
    mock_blob.download_as_bytes.return_value = b"mock file content"
    
    # Configure the mock upload
    mock_blob.generate_signed_url.return_value = "https://storage.googleapis.com/test-bucket/generated-cvs/test-file.pdf?signature"
    
    # Configure the bucket and client
    mock_bucket.blob.return_value = mock_blob
    mock_client.bucket.return_value = mock_bucket
    
    return mock_client

@pytest.fixture
def mock_docx_template():
    """Mock DocxTemplate for rendering templates."""
    mock_template = MagicMock(spec=DocxTemplate)
    
    # Configure the render and save methods
    mock_template.render.return_value = None
    
    # Configure the save method to write dummy content to the BytesIO object
    def mock_save(output_stream):
        output_stream.write(b"mock rendered template")
        return None
    
    mock_template.save.side_effect = mock_save
    
    with patch('docxtpl.DocxTemplate', return_value=mock_template) as mock:
        yield mock

@pytest.fixture
def mock_pdf_converter():
    """Mock PDF conversion client."""
    mock_client = MagicMock(spec=HireableClient)
    
    # Configure the mock response for docx_to_pdf
    mock_response = MagicMock()
    mock_response.content = b"mock pdf content"
    mock_client.docx_to_pdf.return_value = mock_response
    
    return mock_client

@pytest.fixture
def mock_validation():
    """Mock validation with predetermined responses."""
    mock_validator = MagicMock(spec=Validation)
    
    # Configure the validate_request method
    def validate_mock(request, schema):
        # Valid if it has a 'data' field with 'firstName' and 'surname'
        if 'data' in request and 'firstName' in request['data'] and 'surname' in request['data']:
            return True
        return False
    
    mock_validator.validate_request.side_effect = validate_mock
    
    # Add the transform keys method for compatibility
    mock_validator._transform_request_keys.side_effect = lambda x: x
    
    return mock_validator

@pytest.fixture
def mock_utils(mock_storage_client, profile_config):
    """Mock HireableUtils with predetermined responses."""
    mock_util = MagicMock(spec=HireableUtils)
    
    # Configure the retrieve_profile_config method
    mock_util.retrieve_profile_config.return_value = profile_config
    
    # Configure the retrieve_file_from_storage method
    mock_util.retrieve_file_from_storage.return_value = b"mock file content"
    
    # Configure the upload_cv_to_storage method
    mock_util.upload_cv_to_storage.return_value = "generated-cvs/test-file.docx"
    
    # Configure the generate_cv_download_link method
    mock_util.generate_cv_download_link.return_value = "https://storage.googleapis.com/test-bucket/generated-cvs/test-file.docx?signature"
    
    # Set the storage client
    mock_util.storage_client = mock_storage_client
    
    return mock_util

@pytest.fixture
def mock_request(valid_cv_request):
    """Mock Flask request object with JSON data."""
    mock_req = MagicMock()
    mock_req.method = "POST"
    mock_req.get_json.return_value = valid_cv_request
    return mock_req

@pytest.fixture
def mock_invalid_request(invalid_cv_request):
    """Mock Flask request object with invalid JSON data."""
    mock_req = MagicMock()
    mock_req.method = "POST"
    mock_req.get_json.return_value = invalid_cv_request
    return mock_req

@pytest.fixture
def sample_docx_template():
    """Create a simple DOCX template for testing."""
    # Instead of trying to create a real template, return a mock docx file bytes
    # The PK\x03\x04 is the ZIP file signature that DocxTemplate expects
    return b'PK\x03\x04\x14\x00\x06\x00\x08\x00\x00\x00!\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x0b\x00\x00\x00_rels/.rels\xad\x92\xcf\x8e\x9b0\x10\xc5\xef\x91\xf2\x0e\x96\xd7j\x13\x98\xddF\x91\x12\x92n\xabVj\x1fca\x06,\xfd\xa3\x8c\x99$\xbbM\xdf\xbe\x86\x84V\xbb\xd9C\xb7\xbd\xb0\xc6\xbf\xdf\x8c\xe7\xcc\x81\xd3\xdd.\x96\xf8\x82\xc9F\x8c\xa2\x13\x18\xe7\xca\xe3\x83\x9b\x86vwO\xabA\x14\xa5\x0fJ\xa0\x1a\xb9\x87\xc18\xda\xc5\xdf\xee\x9fv\xa7h\x80\xde\xe9\x07\xb6\x11\x1bI\xd9\x90"\xd0\xb8\xc6\'E1K\xc6\xd5\xe3\xf8\xc8\xe4\xb0/D\x9b\x0c0\x14\x07\xfb\xe2\x1aI\x9a\xa2\xb0\xc4\xb0W\xe7\x05U\x99\xe9\x19\xbb\x9e\xb9\x15\xfa\xca\xfb\x19\xeb\xe6\x85\x98\xbaH\xb0\x91\x14\xb3^Go\xb5\xdc\xa3\xdck\x09z\x11<\xd3\xb0\x95iq\xbd\xa4\x98\xa7e\x91\xbd\xc2\x9d\xa4(2z\x8d\xf9\xbe:\x82\xea9\xc2\x8f\x0f\xf0\xe3\x12\xaeo\xa5\x90\xba\xf6\xa5\xea\x80\xcb\xf8\x8c\xc2t\xca)\xe3\x89\x91\xa9\x8b\x8aM\xd0\x98\xc6\xd0\x859\x8ch\x18\xee\xef\xc2\xfdc\xb8\x9f-\xe1\xc3\xe7\xf0\xe9\xf3\xb2bsO\x1f\xeb}\xc4\xe4\xff\x1c\x13\xfa\x06\x00\x00\x00\xff\xff\x03\x00PK\x01\x02\x14\x00\x14\x00\x06\x00\x08\x00\x00\x00!\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x0b\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00_rels/.relsPK\x05\x06\x00\x00\x00\x00\x01\x00\x01\x00<\x00\x00\x00\xd6\x00\x00\x00\x00\x00'

@pytest.fixture
def cv_schema():
    """Sample CV schema for validation testing."""
    return {
        "type": "object",
        "properties": {
            "data": {
                "type": "object",
                "properties": {
                    "firstName": {"type": "string"},
                    "surname": {"type": "string"},
                    "email": {"type": "string"},
                    "phone": {"type": "string"},
                    "profileStatement": {"type": "string"},
                    "skills": {
                        "type": "array",
                        "items": {"type": "string"}
                    }
                },
                "required": ["firstName", "surname"]
            }
        },
        "required": ["data"]
    }

# Integration test fixtures

@pytest.fixture
def sample_cv_file():
    """Sample CV file content for parser integration tests."""
    return b"This is a sample CV with some formatted content for parsing tests."

@pytest.fixture
def sample_parsed_data():
    """Sample parsed data returned by the parser service."""
    return {
        "contact_info": {
            "first_name": "John",
            "last_name": "Doe",
            "email": "john.doe@example.com",
            "phone": "+44 9876 543210",
            "location": "London, UK"
        },
        "personal_statement": "Experienced software engineer with 10+ years in full-stack development...",
        "skills": ["Python", "JavaScript", "Cloud Computing", "Agile Development"],
        "links": ["linkedin.com/in/johndoe"],
        "experience": [
            {
                "title": "Senior Developer",
                "company": "Tech Solutions Ltd",
                "start_date": "2018-01",
                "end_date": "2023-05",
                "description": "Led development team in creating scalable applications..."
            }
        ],
        "education": [
            {
                "institution": "University of Technology",
                "degree": "BSc Computer Science",
                "start_date": "2013",
                "end_date": "2017",
                "grade": "First Class Honours"
            }
        ]
    }

@pytest.fixture
def supabase_test_config():
    """Supabase configuration for integration tests."""
    return {
        "url": os.environ.get("TEST_SUPABASE_URL", "https://example.supabase.co"),
        "anon_key": os.environ.get("TEST_SUPABASE_ANON_KEY", "test-anon-key"),
        "jwt_secret": os.environ.get("TEST_SUPABASE_JWT_SECRET", "test-jwt-secret"),
        "project_ref": os.environ.get("TEST_SUPABASE_PROJECT_REF", "test-project-ref"),
        "test_user_email": os.environ.get("TEST_SUPABASE_USER_EMAIL", "test@example.com"),
        "test_user_password": os.environ.get("TEST_SUPABASE_USER_PASSWORD", "test-password"),
    }

@pytest.fixture
def mock_parser_client():
    """Mock client for CV Parser service."""
    mock_client = MagicMock(spec=HireableClient)
    
    # Configure the mock for parsing CVs
    mock_client.parse_cv.return_value = {
        "contact_info": {
            "first_name": "John",
            "last_name": "Doe",
            "email": "john.doe@example.com",
            "phone": "+44 9876 543210",
            "location": "London, UK"
        },
        "personal_statement": "Experienced software engineer with 10+ years in full-stack development...",
        "skills": ["Python", "JavaScript", "Cloud Computing", "Agile Development"],
        "links": ["linkedin.com/in/johndoe"]
    }
    
    return mock_client

@pytest.fixture
def api_base_url():
    """The base URL for API testing."""
    return os.environ.get("TEST_API_BASE_URL", "http://localhost:8080")

@pytest.fixture
def parser_service_url():
    """The URL of the parser service."""
    return os.environ.get("PARSER_SERVICE_URL", "https://parser-api.example.com")

@pytest.fixture(scope="session")
def live_parser_client():
    """Fixture for live parser client testing."""
    parser_url = os.getenv("CV_PARSER_URL")
    if not parser_url:
        # Use a default value if environment variable isn't set
        parser_url = "https://test-parser-api.example.com"
    client = HireableClient()
    client.parser_api_endpoint = f"{parser_url}/parse"
    return client

@pytest.fixture(autouse=True)
def mock_google_cloud(monkeypatch):
    """Mock Google Cloud services for testing."""
    from unittest.mock import MagicMock
    
    # Create mock classes
    mock_storage_client = MagicMock()
    mock_bucket = MagicMock()
    mock_blob = MagicMock()
    mock_secret_client = MagicMock()
    mock_secret_version = MagicMock()
    
    # Configure mocks
    mock_storage_client.bucket.return_value = mock_bucket
    mock_bucket.blob.return_value = mock_blob
    mock_blob.download_as_bytes.return_value = b"Mock file content"
    mock_secret_version.payload.data.decode.return_value = "test-secret-value"
    mock_secret_client.access_secret_version.return_value = mock_secret_version
    
    # Apply patches
    monkeypatch.setattr('google.cloud.storage.Client', lambda *args, **kwargs: mock_storage_client)
    monkeypatch.setattr('google.cloud.secretmanager.SecretManagerServiceClient', lambda *args, **kwargs: mock_secret_client)
    
    return {
        'storage_client': mock_storage_client,
        'secret_client': mock_secret_client
    } 