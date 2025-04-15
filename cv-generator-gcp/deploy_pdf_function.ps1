# Set variables
$PROJECT_ID = "hireable-places"
$REGION = "europe-west2"
$FUNCTION_NAME = "docx-to-pdf"
$SERVICE_ACCOUNT = "cv-optimizer-sa@hireable-places.iam.gserviceaccount.com"

# Build the Docker image
Write-Host "Building Docker image..."
docker build -t gcr.io/$PROJECT_ID/$FUNCTION_NAME ./docx_to_pdf_function

# Push the Docker image to Google Container Registry
Write-Host "Pushing Docker image to Google Container Registry..."
docker push gcr.io/$PROJECT_ID/$FUNCTION_NAME

# Deploy the Cloud Function
Write-Host "Deploying Cloud Function..."
gcloud functions deploy $FUNCTION_NAME `
  --gen2 `
  --runtime=python39 `
  --region=$REGION `
  --source=./docx_to_pdf_function `
  --entry-point=docx_to_pdf `
  --trigger-http `
  --service-account=$SERVICE_ACCOUNT `
  --memory=1024MB `
  --timeout=540s

Write-Host "Deployment complete!" 