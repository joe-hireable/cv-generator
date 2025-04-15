import functions_framework
import logging
import json
import io
import html
from datetime import datetime
from docxtpl import DocxTemplate
from io import BytesIO
from google.cloud import storage
from google.cloud import secretmanager
import uuid
import os
from utils.validation import Validation
from utils.client import HireableClient
from utils.utils import HireableUtils
from utils.security import SecurityUtils
from utils.adapter import HireableCVAdapter
from models.schema import CVGenerationRequest
import copy

@functions_framework.http
def generate_cv(request):
    """
    Google Cloud Function that generates a CV from a template and uploads it to Google Cloud Storage.
    
    Args:
        request (flask.Request): HTTP request object.
        
    Returns:
        flask.Response: HTTP response with download URL.
    """
    # Initialize utilities
    validation, client, utils = Validation(), HireableClient(), HireableUtils()
    
    # Set up CORS headers
    if request.method == 'OPTIONS':
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'POST',
            'Access-Control-Allow-Headers': 'Content-Type, Authorization',
            'Access-Control-Max-Age': '3600'
        }
        return ('', 204, headers)
    
    # Set CORS headers for the main request
    headers = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'POST',
        'Content-Type': 'application/json'
    }

    logging.info('Processing CV Generation request')
    profile = utils.retrieve_profile_config()
    
    try:
        # Get JSON from request and escape ampersands
        req_json = escape_ampersands(request.get_json())
        
        # Validate request data (still using legacy CV schema for backward compatibility)
        if not validation.validate_request(req_json, json.loads(utils.retrieve_file_from_storage("cv-schemas", profile.schema_file))):
            raise ValueError("Request validation failed")
        
        # Create Pydantic model from the validated data
        req_model = CVGenerationRequest.model_validate(validation._transform_request_keys(req_json))
        logging.info(f'Request validated successfully')
    except ValueError as e:
        logging.error(f'Error parsing or validating JSON: {e}')
        return (json.dumps({"error": "Please pass a valid JSON object in the body"}), 400, headers)
    
    # Get template from request or profile
    template = req_json.get('template')
    if template:
        profile.template = template
    
    # Get output format
    output_format = req_model.output_format or req_json.get('outputFormat', 'docx')
    
    # Prepare context for template rendering (keeping original format for backward compatibility)
    template_context = prepare_template_context(
        req_json, 
        req_model.section_order, 
        req_model.section_visibility.model_dump() if req_model.section_visibility else None,
        req_model.is_anonymized
    )
    
    # Generate CV from template
    output_stream = generate_cv_from_template(template_context, utils.retrieve_file_from_storage("cv-generator", profile.template))

    if output_format == "pdf":
        output_stream = BytesIO(client.docx_to_pdf(output_stream).content)
        generated_cv_filename = generate_filename(req_json, output_format)
    else:
        generated_cv_filename = generate_filename(req_json)

    # Upload to Google Cloud Storage
    utils.upload_cv_to_storage(output_stream, generated_cv_filename)

    response = {
        "url": utils.generate_cv_download_link(generated_cv_filename)
    }
    logging.info(f"CV Download Link: {response}")

    return (json.dumps(response), 200, headers)

@functions_framework.http
def parse_cv(request):
    """
    Google Cloud Function that proxies CV parsing requests to the CV Parser service.
    
    Args:
        request (flask.Request): HTTP request object.
        
    Returns:
        flask.Response: HTTP response with parsed CV data.
    """
    # Initialize utilities
    validation, client, utils, security = Validation(), HireableClient(), HireableUtils(), SecurityUtils()
    
    # Handle CORS for preflight requests
    if request.method == 'OPTIONS':
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'POST',
            'Access-Control-Allow-Headers': 'Content-Type, Authorization',
            'Access-Control-Max-Age': '3600'
        }
        return ('', 204, headers)
    
    # Set CORS headers for the main request
    headers = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'POST',
        'Content-Type': 'application/json'
    }
    
    try:
        # Check authentication if enforced
        auth_required = os.environ.get("REQUIRE_AUTHENTICATION", "true").lower() == "true"
        
        if auth_required:
            auth_header = request.headers.get('Authorization')
            if not auth_header:
                return (json.dumps({"error": "Authentication required"}), 401, headers)
                
            # Extract and validate token
            token = security.extract_token_from_header(auth_header)
            if not token:
                return (json.dumps({"error": "Invalid authorization header format"}), 401, headers)
                
            try:
                security.validate_supabase_jwt(token)
            except ValueError as e:
                return (json.dumps({"error": str(e)}), 401, headers)
        
        # Check for CV file
        if 'file' not in request.files:
            return (json.dumps({"error": "No CV file provided"}), 400, headers)
        
        cv_file = request.files['file']
        
        # Get optional job description if provided
        job_description = None
        if 'jobDescription' in request.form:
            job_description = request.form['jobDescription']
        
        # Determine optimization task
        task = request.form.get('task', 'parsing')
        if task not in ['parsing', 'ps', 'cs', 'ka', 'role', 'scoring']:
            task = 'parsing'  # Default to parsing
        
        # Forward request to CV Parser service
        try:
            # Pass through the auth header to the parser service
            auth_header = request.headers.get('Authorization')
            
            # Parse the CV
            result = client.parse_cv(
                cv_file, 
                job_description, 
                task, 
                auth_header
            )
            
            if "error" in result:
                return (json.dumps(result), 400, headers)
                
            return (json.dumps(result), 200, headers)
            
        except Exception as e:
            logging.error(f"Error calling CV Parser service: {e}")
            return (json.dumps({"error": f"Error processing CV: {str(e)}"}), 500, headers)
            
    except Exception as e:
        logging.error(f"Error in parse_cv: {e}")
        return (json.dumps({"error": str(e)}), 500, headers)

@functions_framework.http
def parse_and_generate_cv(request):
    """
    Google Cloud Function that combines CV parsing and document generation.
    First parses a CV file using the CV Parser service, then generates a document.
    
    Args:
        request (flask.Request): HTTP request object.
        
    Returns:
        flask.Response: HTTP response with parsed CV data and generated document URL.
    """
    # Initialize utilities
    validation, client, utils, security = Validation(), HireableClient(), HireableUtils(), SecurityUtils()
    adapter = HireableCVAdapter()
    
    # Handle CORS for preflight requests
    if request.method == 'OPTIONS':
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'POST',
            'Access-Control-Allow-Headers': 'Content-Type, Authorization',
            'Access-Control-Max-Age': '3600'
        }
        return ('', 204, headers)
    
    # Set CORS headers for the main request
    headers = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'POST',
        'Content-Type': 'application/json'
    }
    
    try:
        # Check authentication if enforced
        auth_required = os.environ.get("REQUIRE_AUTHENTICATION", "true").lower() == "true"
        
        if auth_required:
            auth_header = request.headers.get('Authorization')
            if not auth_header:
                return (json.dumps({"error": "Authentication required"}), 401, headers)
                
            # Extract and validate token
            token = security.extract_token_from_header(auth_header)
            if not token:
                return (json.dumps({"error": "Invalid authorization header format"}), 401, headers)
                
            try:
                security.validate_supabase_jwt(token)
            except ValueError as e:
                return (json.dumps({"error": str(e)}), 401, headers)
        
        # Check for CV file
        if 'file' not in request.files:
            return (json.dumps({"error": "No CV file provided"}), 400, headers)
        
        cv_file = request.files['file']
        
        # Get options from request
        job_description = request.form.get('jobDescription')
        template = request.form.get('template')
        output_format = request.form.get('outputFormat', 'docx')
        
        if output_format not in ['docx', 'pdf']:
            output_format = 'docx'
        
        # 1. Parse the CV
        logging.info("Parsing CV file")
        auth_header = request.headers.get('Authorization')
        
        cv_file.seek(0)  # Ensure file is at start position
        parse_result = client.parse_cv(
            cv_file, 
            job_description, 
            "parsing", 
            auth_header
        )
        
        if "error" in parse_result:
            return (json.dumps(parse_result), 400, headers)
            
        cv_data = parse_result.get("cv_data", {})
        
        # 2. Convert parsed data to CV Generator format
        logging.info("Converting parsed data to CV Generator format")
        generator_data = adapter.parser_to_generator(cv_data)
        
        # Add recruiter profile if provided
        if 'recruiterProfile' in request.form:
            try:
                recruiter_profile = json.loads(request.form['recruiterProfile'])
                generator_data['recruiterProfile'] = recruiter_profile
            except Exception as e:
                logging.warning(f"Error parsing recruiter profile: {e}")
                
        # Add template if provided
        if template:
            generator_data['template'] = template
            
        # Add output format
        generator_data['outputFormat'] = output_format
        
        # 3. Generate the CV document
        profile = utils.retrieve_profile_config()
        
        # Validate request data
        if not validation.validate_request(generator_data, json.loads(utils.retrieve_file_from_storage("cv-schemas", profile.schema_file))):
            return (json.dumps({"error": "Converted CV data validation failed"}), 400, headers)
        
        # Create Pydantic model from the validated data
        req_model = CVGenerationRequest.model_validate(validation._transform_request_keys(generator_data))
        
        # Get template from request or profile
        if template:
            profile.template = template
            
        # Prepare context for template rendering
        template_context = prepare_template_context(
            generator_data, 
            req_model.section_order, 
            req_model.section_visibility.model_dump() if req_model.section_visibility else None,
            req_model.is_anonymized
        )
        
        # Generate CV from template
        output_stream = generate_cv_from_template(template_context, utils.retrieve_file_from_storage("cv-generator", profile.template))
    
        if output_format == "pdf":
            output_stream = BytesIO(client.docx_to_pdf(output_stream).content)
            generated_cv_filename = generate_filename(generator_data, output_format)
        else:
            generated_cv_filename = generate_filename(generator_data)
    
        # Upload to Google Cloud Storage
        utils.upload_cv_to_storage(output_stream, generated_cv_filename)
    
        # 4. Prepare the combined response
        response = {
            "parsed_data": cv_data,
            "document_url": utils.generate_cv_download_link(generated_cv_filename)
        }
        
        # Include any optimization scores if available
        if "scores" in parse_result:
            response["scores"] = parse_result["scores"]
        
        return (json.dumps(response), 200, headers)
            
    except Exception as e:
        logging.error(f"Error in parse_and_generate_cv: {e}")
        return (json.dumps({"error": str(e)}), 500, headers)

def escape_ampersands(data):
    """
    Recursively escapes ampersands in string values within nested data structures.
    
    Args:
        data: The data to escape ampersands in.
        
    Returns:
        The data with escaped ampersands.
    """
    if isinstance(data, dict):
        return {k: escape_ampersands(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [escape_ampersands(item) for item in data]
    elif isinstance(data, str):
        return html.escape(data)  # Converts "&" to "&amp;"
    return data

def generate_filename(request, filetype="docx"):
    """
    Generates a filename for the CV based on the request data.
    
    Args:
        request: The request data.
        filetype: The file type extension.
        
    Returns:
        The generated filename.
    """
    return f"{request['data']['firstName']} {request['data']['surname']} CV {datetime.now().strftime('%Y-%m-%d-%H-%M-%S')}.{filetype}"

def generate_cv_from_template(context, template_bytes):
    """
    Generates a CV from a template.
    
    Args:
        context: The context to render the template with.
        template_bytes: The template file content.
        
    Returns:
        BytesIO: The generated CV document.
    """
    # Load docx template - handle both string and bytes input
    if isinstance(template_bytes, str):
        # Convert string to bytes if needed
        template_bytes = template_bytes.encode('utf-8')
    elif not isinstance(template_bytes, bytes):
        # Handle other types
        template_bytes = bytes(template_bytes)
        
    template = DocxTemplate(io.BytesIO(template_bytes))
    template.render(context)

    # Save the document in memory
    output_stream = BytesIO()
    template.save(output_stream)

    # Seek to the beginning of the stream (required for reading)
    output_stream.seek(0)

    return output_stream

def prepare_template_context(req_body, section_order=None, section_visibility=None, is_anonymized=False):
    """
    Prepares the context for template rendering, handling section ordering, visibility, and anonymization.
    
    Args:
        req_body: The request body.
        section_order: Optional ordering of sections.
        section_visibility: Optional visibility of sections.
        is_anonymized: Whether to anonymize the CV.
        
    Returns:
        The prepared context.
    """
    # Create a copy of the request body to avoid modifying the original
    context = req_body.copy()
    
    # Add section order if provided
    if section_order:
        context['sectionOrder'] = section_order
    
    # Add section visibility if provided
    if section_visibility:
        context['sectionVisibility'] = section_visibility
    
    # Apply anonymization if requested
    if is_anonymized:
        context = anonymize_cv_data(context)
    
    # Add recruiter information if available
    if 'recruiterProfile' in req_body:
        context['recruiterProfile'] = req_body['recruiterProfile']
    
    return context

def anonymize_cv_data(data):
    """
    Anonymizes personal data in the CV.
    
    Args:
        data: The CV data to anonymize.
        
    Returns:
        The anonymized CV data.
    """
    # Create a deep copy of the data to avoid modifying the original
    anonymized = copy.deepcopy(data)
    
    # Anonymize personal information if present in the data structure
    if 'data' in anonymized:
        personal_data = anonymized['data']
        
        # Replace name with initials
        if 'firstName' in personal_data and 'surname' in personal_data:
            first_initial = personal_data['firstName'][0] if personal_data['firstName'] else 'A'
            surname_initial = personal_data['surname'][0] if personal_data['surname'] else 'B'
            personal_data['firstName'] = f"{first_initial}."
            personal_data['surname'] = f"{surname_initial}."
        
        # Anonymize contact information
        if 'email' in personal_data:
            personal_data['email'] = "candidate@example.com"
        
        if 'phone' in personal_data:
            personal_data['phone'] = "+44 XXX XXX XXXX"
        
        if 'address' in personal_data:
            personal_data['address'] = "United Kingdom"
        
        # Anonymize other personal identifiers
        if 'linkedin' in personal_data:
            personal_data['linkedin'] = "linkedin.com/in/candidate"
        
        anonymized['data'] = personal_data
    
    return anonymized 