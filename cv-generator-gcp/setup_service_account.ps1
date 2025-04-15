# Set variables
$PROJECT_ID = "hireable-places"
$SERVICE_ACCOUNT_NAME = "cv-optimizer-sa"
$SERVICE_ACCOUNT_EMAIL = "${SERVICE_ACCOUNT_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"
$KEY_FILE = "cv-optimizer-key.json"
$ENV_FILE = ".env"

# Check if gcloud is installed
try {
    $gcloudVersion = gcloud --version
    Write-Host "gcloud is installed."
} catch {
    Write-Host "Error: gcloud is not installed. Please install the Google Cloud SDK."
    exit 1
}

# Check if user is logged in to gcloud
try {
    $activeAccount = gcloud auth list --filter=status:ACTIVE --format="value(account)"
    if (-not $activeAccount) {
        Write-Host "You are not logged in to gcloud. Please run 'gcloud auth login' first."
        exit 1
    }
    Write-Host "Logged in as: $activeAccount"
} catch {
    Write-Host "Error checking gcloud authentication: $_"
    exit 1
}

# Set the current project
Write-Host "Setting project to $PROJECT_ID..."
gcloud config set project $PROJECT_ID

# Verify service account exists
try {
    $serviceAccountExists = gcloud iam service-accounts describe $SERVICE_ACCOUNT_EMAIL 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Error: Service account $SERVICE_ACCOUNT_EMAIL does not exist."
        exit 1
    }
    Write-Host "Using existing service account: $SERVICE_ACCOUNT_EMAIL"
    
    # Grant necessary roles if not already granted
    Write-Host "Ensuring service account has necessary roles..."
    gcloud projects add-iam-policy-binding $PROJECT_ID --member="serviceAccount:$SERVICE_ACCOUNT_EMAIL" --role="roles/cloudfunctions.invoker"
} catch {
    Write-Host "Error checking service account: $_"
    exit 1
}

# Create a new key for the service account
Write-Host "Creating service account key..."
gcloud iam service-accounts keys create $KEY_FILE --iam-account=$SERVICE_ACCOUNT_EMAIL

# Get the absolute path to the key file
$KEY_FILE_PATH = (Get-Item $KEY_FILE).FullName

# Update .env file
Write-Host "Updating .env file with GOOGLE_APPLICATION_CREDENTIALS..."

# Check if GOOGLE_APPLICATION_CREDENTIALS already exists in .env
$envContent = Get-Content $ENV_FILE -ErrorAction SilentlyContinue
$credentialsLine = $envContent | Where-Object { $_ -match "GOOGLE_APPLICATION_CREDENTIALS=" }

if ($credentialsLine) {
    # Replace the existing line
    $newContent = $envContent -replace "GOOGLE_APPLICATION_CREDENTIALS=.*", "GOOGLE_APPLICATION_CREDENTIALS=$KEY_FILE_PATH"
    $newContent | Set-Content $ENV_FILE
} else {
    # Add the new line
    Add-Content -Path $ENV_FILE -Value "GOOGLE_APPLICATION_CREDENTIALS=$KEY_FILE_PATH"
}

Write-Host "Setup complete!"
Write-Host "Service account key saved to: $KEY_FILE_PATH"
Write-Host "GOOGLE_APPLICATION_CREDENTIALS has been added to your .env file."
Write-Host ""
Write-Host "IMPORTANT: Keep your service account key secure and never commit it to version control."
Write-Host "Consider adding $KEY_FILE to your .gitignore file." 