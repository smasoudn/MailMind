#!/bin/bash

# Ensure gcloud is installed
if ! command -v gcloud &> /dev/null
then
    echo "gcloud CLI could not be found. Please install it from https://cloud.google.com/sdk/docs/install first."
    exit 1
fi

echo "Deploying MailMind to Google Cloud Run..."

# Extract the API key from the .env file
if [ ! -f .env ]; then
    echo "ERROR: .env file not found! Please create one with OPENAI_API_KEY=your_key"
    exit 1
fi

OPENAI_KEY=$(grep '^OPENAI_API_KEY=' .env | cut -d '=' -f2- | tr -d '"' | tr -d "'")

if [ -z "$OPENAI_KEY" ]; then
    echo "ERROR: OPENAI_API_KEY not found in .env file!"
    exit 1
fi

# Deploy from source code natively using gcloud run deploy
gcloud run deploy mailmind \
  --source . \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars OPENAI_API_KEY="$OPENAI_KEY"

echo "Deployment complete! Your Streamlit app is live."
