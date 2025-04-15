import azure.functions as func
import logging, json, io, html
from datetime import datetime
from azure.monitor.opentelemetry import configure_azure_monitor
from opentelemetry import trace
from docxtpl import DocxTemplate
from io import BytesIO
from Validation import Validation
from HireableClient import HireableClient
from HireableUtils import HireableUtils

app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)

@app.route(route="generate_cv")
def generate_cv(req: func.HttpRequest) -> func.HttpResponse:
    validation, client, utils = Validation(), HireableClient(), HireableUtils()

    logging.info('Processing CV Generation request')
    profile = utils.retrieve_profile_config()
    try:
        req_body = escape_ampersands(req.get_json())
        if not validation.validate_request(req_body, json.loads(utils.retrieve_file_from_blob("cv-schemas", profile.schema))):
            raise ValueError("Request validation failed")
        logging.info(f'Request body: {req_body}')
    except ValueError as e:
        logging.error(f'Error parsing JSON: {e}')
        return func.HttpResponse(
            "Please pass a valid JSON object in the body",
            status_code=400
        )
    
    template, output_format = req_body.get('template'), req_body.get('outputFormat')

    # If template is specified in request override template
    if template:
        profile.template = template

    output_stream = generate_cv_from_template(req_body, utils.retrieve_file_from_blob("cv-generator", profile.template))

    if output_format == "pdf":
        output_stream = BytesIO(client.docx_to_pdf(output_stream).content)
        generated_cv_filename = generate_filename(req_body, output_format)
    else:
        generated_cv_filename = generate_filename(req_body)

    utils.upload_cv_to_blob(output_stream, generated_cv_filename)

    response =  {
        "url": utils.generate_cv_download_link(generated_cv_filename)
    }
    logging.info("CV Download Link: %s", response)

    return func.HttpResponse(
            json.dumps(response),
            status_code=200,
            headers={"Content-Type": "application/json"}
    )

def escape_ampersands(data):
    if isinstance(data, dict):
        return {k: escape_ampersands(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [escape_ampersands(item) for item in data]
    elif isinstance(data, str):
        return html.escape(data)  # Converts "&" to "&amp;"
    return data

def generate_filename(request, filetype="docx"):
    return f"{request['data']['firstName']} {request['data']['surname']} CV {datetime.now().strftime('%Y-%m-%d-%H-%M-%S')}.{filetype}"

def generate_cv_from_template(request, template):
    # Load docx template
    template = DocxTemplate(io.BytesIO(template))
    template.render(request)

    # Save the document in memory
    output_stream = BytesIO()
    template.save(output_stream)

    # Seek to the beginning of the stream (required for reading)
    output_stream.seek(0)

    return output_stream