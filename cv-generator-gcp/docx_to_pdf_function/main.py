import functions_framework
import logging
import os
import io
import tempfile
from google.cloud import storage
from docx2pdf import convert
import uuid

@functions_framework.http
def docx_to_pdf(request):
    """
    Google Cloud Function that converts a DOCX file to PDF.
    
    Args:
        request (flask.Request): HTTP request object with a DOCX file.
        
    Returns:
        flask.Response: HTTP response with the PDF file.
    """
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
        'Content-Type': 'application/pdf'
    }
    
    # Check if the request has a file
    if 'file' not in request.files:
        return ('No file provided', 400, headers)
    
    # Get the file from the request
    file = request.files['file']
    
    # Check if the file is a DOCX file
    if not file.filename.endswith('.docx'):
        return ('File must be a DOCX file', 400, headers)
    
    try:
        # Create temporary files for DOCX and PDF
        with tempfile.NamedTemporaryFile(suffix='.docx', delete=False) as docx_temp:
            docx_path = docx_temp.name
            file.save(docx_path)
        
        pdf_path = docx_path.replace('.docx', '.pdf')
        
        # Convert DOCX to PDF
        convert(docx_path, pdf_path)
        
        # Read the PDF file
        with open(pdf_path, 'rb') as pdf_file:
            pdf_content = pdf_file.read()
        
        # Clean up temporary files
        os.unlink(docx_path)
        os.unlink(pdf_path)
        
        # Return the PDF file
        return (pdf_content, 200, headers)
    
    except Exception as e:
        logging.error(f"Error converting DOCX to PDF: {e}")
        return (f'Error converting DOCX to PDF: {str(e)}', 500, headers) 