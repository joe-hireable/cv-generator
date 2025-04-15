# DOCX to PDF Conversion Function

This Google Cloud Function converts DOCX files to PDF format using LibreOffice.

## Prerequisites

- Google Cloud Platform account with billing enabled
- Google Cloud SDK installed
- Docker installed
- Appropriate permissions to deploy Cloud Functions
- Service account with necessary permissions

## Deployment

### Using the deployment script

1. Make sure you're logged in to Google Cloud:
   ```bash
   gcloud auth login
   ```

2. Set your project:
   ```bash
   gcloud config set project hireable-places
   ```

3. Run the deployment script:
   ```bash
   # For Linux/Mac
   ./deploy_pdf_function.sh
   
   # For Windows
   .\deploy_pdf_function.ps1
   ```

### Manual deployment

1. Build the Docker image:
   ```bash
   docker build -t gcr.io/hireable-places/docx-to-pdf ./docx_to_pdf_function
   ```

2. Push the Docker image to Google Container Registry:
   ```bash
   docker push gcr.io/hireable-places/docx-to-pdf
   ```

3. Deploy the Cloud Function:
   ```bash
   gcloud functions deploy docx-to-pdf \
     --gen2 \
     --runtime=python39 \
     --region=europe-west2 \
     --source=./docx_to_pdf_function \
     --entry-point=docx_to_pdf \
     --trigger-http \
     --service-account=hireable-pdf-converter@hireable-places.iam.gserviceaccount.com \
     --memory=1024MB \
     --timeout=540s
   ```

## Usage

The function requires service account authentication. The client must include a valid Bearer token in the Authorization header.

### Setting up service account authentication

1. Create a service account key:
   ```bash
   gcloud iam service-accounts keys create service-account-key.json \
     --iam-account=hireable-pdf-converter@hireable-places.iam.gserviceaccount.com
   ```

2. Set the environment variable to point to the key file:
   ```bash
   # For Linux/Mac
   export GOOGLE_APPLICATION_CREDENTIALS=./service-account-key.json
   
   # For Windows PowerShell
   $env:GOOGLE_APPLICATION_CREDENTIALS=".\service-account-key.json"
   ```

### Example using curl with authentication

```bash
# Get an access token
TOKEN=$(gcloud auth print-identity-token)

# Call the function with the token
curl -X POST \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@document.docx" \
  https://europe-west2-hireable-places.cloudfunctions.net/docx-to-pdf \
  --output document.pdf
```

## Environment Variables

- `FUNCTION_TARGET`: The name of the function to execute (default: docx_to_pdf)
- `GOOGLE_APPLICATION_CREDENTIALS`: Path to the service account key file

## Dependencies

- functions-framework
- docx2pdf
- google-cloud-storage
- LibreOffice (installed in the Docker container) 