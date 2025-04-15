#!/bin/bash

# Set variables
PROJECT_ID="hireable-places"
SERVICE_ACCOUNT_NAME="cv-optimizer-sa"
SERVICE_ACCOUNT_EMAIL="${SERVICE_ACCOUNT_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"
KEY_FILE="cv-optimizer-key.json"
ENV_FILE=".env"

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo "Error: gcloud is not installed. Please install the Google Cloud SDK."
    exit 1
fi

# Check if user is logged in to gcloud
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" &> /dev/null; then
    echo "You are not logged in to gcloud. Please run 'gcloud auth login' first."
    exit 1
fi

# Set the current project
echo "Setting project to $PROJECT_ID..."
gcloud config set project $PROJECT_ID

# Verify service account exists
if ! gcloud iam service-accounts describe $SERVICE_ACCOUNT_EMAIL &> /dev/null; then
    echo "Error: Service account $SERVICE_ACCOUNT_EMAIL does not exist."
    exit 1
else
    echo "Using existing service account: $SERVICE_ACCOUNT_EMAIL"
fi

# Grant necessary roles if not already granted
echo "Ensuring service account has necessary roles..."
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$SERVICE_ACCOUNT_EMAIL" \
    --role="roles/cloudfunctions.invoker"

# Create a new key for the service account
echo "Creating service account key..."
gcloud iam service-accounts keys create $KEY_FILE \
    --iam-account=$SERVICE_ACCOUNT_EMAIL

# Get the absolute path to the key file
KEY_FILE_PATH=$(realpath $KEY_FILE)

# Update .env file
echo "Updating .env file with GOOGLE_APPLICATION_CREDENTIALS..."

# Check if GOOGLE_APPLICATION_CREDENTIALS already exists in .env
if grep -q "GOOGLE_APPLICATION_CREDENTIALS" $ENV_FILE; then
    # Replace the existing line
    sed -i "s|GOOGLE_APPLICATION_CREDENTIALS=.*|GOOGLE_APPLICATION_CREDENTIALS=$KEY_FILE_PATH|" $ENV_FILE
else
    # Add the new line
    echo "GOOGLE_APPLICATION_CREDENTIALS=$KEY_FILE_PATH" >> $ENV_FILE
fi

echo "Setup complete!"
echo "Service account key saved to: $KEY_FILE_PATH"
echo "GOOGLE_APPLICATION_CREDENTIALS has been added to your .env file."
echo ""
echo "IMPORTANT: Keep your service account key secure and never commit it to version control."
echo "Consider adding $KEY_FILE to your .gitignore file." 