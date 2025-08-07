#!/bin/bash

# Zoho CRM to BigQuery Sync - Automated Google Cloud Deployment Script
# This script fully automates the deployment process to Google Cloud

set -e  # Exit on any error

# Configuration
PROJECT_ID="arboreal-logic-467306-k0"
REGION="us-central1"
SERVICE_NAME="zoho-bigquery-sync"
IMAGE_NAME="gcr.io/$PROJECT_ID/$SERVICE_NAME"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 Starting automated deployment to Google Cloud...${NC}"
echo -e "${BLUE}Project ID: $PROJECT_ID${NC}"
echo -e "${BLUE}Region: $REGION${NC}"
echo -e "${BLUE}Service Name: $SERVICE_NAME${NC}"
echo ""

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to create secret if it doesn't exist
create_secret_if_not_exists() {
    local secret_name=$1
    local secret_value=$2
    
    if gcloud secrets describe $secret_name >/dev/null 2>&1; then
        echo -e "${YELLOW}Secret $secret_name already exists, updating...${NC}"
        echo "$secret_value" | gcloud secrets versions add $secret_name --data-file=-
    else
        echo -e "${GREEN}Creating secret $secret_name...${NC}"
        echo "$secret_value" | gcloud secrets create $secret_name --data-file=-
    fi
}

# Check prerequisites
echo -e "${BLUE}📋 Checking prerequisites...${NC}"

if ! command_exists gcloud; then
    echo -e "${RED}❌ gcloud CLI is not installed. Please install it first.${NC}"
    echo "Download from: https://cloud.google.com/sdk/docs/install"
    exit 1
fi

if ! command_exists docker; then
    echo -e "${RED}❌ Docker is not installed. Please install it first.${NC}"
    echo "Download from: https://docs.docker.com/get-docker/"
    exit 1
fi

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo -e "${RED}❌ .env file not found. Please create it with your credentials.${NC}"
    exit 1
fi

# Load environment variables from .env file
echo -e "${BLUE}📄 Loading environment variables from .env file...${NC}"
export $(grep -v '^#' .env | xargs)

# Validate required environment variables
required_vars=("ZOHO_CLIENT_ID" "ZOHO_CLIENT_SECRET" "ZOHO_REFRESH_TOKEN" "GOOGLE_CLOUD_PROJECT_ID")
for var in "${required_vars[@]}"; do
    if [ -z "${!var}" ]; then
        echo -e "${RED}❌ Required environment variable $var is not set in .env file${NC}"
        exit 1
    fi
done

echo -e "${GREEN}✅ All prerequisites met${NC}"

# Set the project
echo -e "${BLUE}📋 Setting Google Cloud project...${NC}"
gcloud config set project $PROJECT_ID

# Enable required APIs
echo -e "${BLUE}🔧 Enabling required Google Cloud APIs...${NC}"
apis=(
    "cloudbuild.googleapis.com"
    "run.googleapis.com"
    "containerregistry.googleapis.com"
    "secretmanager.googleapis.com"
    "cloudscheduler.googleapis.com"
    "artifactregistry.googleapis.com"
)

for api in "${apis[@]}"; do
    echo "Enabling $api..."
    gcloud services enable $api
done

echo -e "${GREEN}✅ APIs enabled${NC}"

# Create secrets in Secret Manager automatically
echo -e "${BLUE}🔐 Creating/updating secrets in Secret Manager...${NC}"

create_secret_if_not_exists "zoho-client-id" "$ZOHO_CLIENT_ID"
create_secret_if_not_exists "zoho-client-secret" "$ZOHO_CLIENT_SECRET"
create_secret_if_not_exists "zoho-refresh-token" "$ZOHO_REFRESH_TOKEN"

# Upload BigQuery credentials if file exists
if [ -f "credentials/arboreal-logic-467306-k0-4a5ff4fe08b5.json" ]; then
    if gcloud secrets describe bigquery-credentials >/dev/null 2>&1; then
        echo -e "${YELLOW}BigQuery credentials secret already exists, updating...${NC}"
        gcloud secrets versions add bigquery-credentials --data-file=credentials/arboreal-logic-467306-k0-4a5ff4fe08b5.json
    else
        echo -e "${GREEN}Creating BigQuery credentials secret...${NC}"
        gcloud secrets create bigquery-credentials --data-file=credentials/arboreal-logic-467306-k0-4a5ff4fe08b5.json
    fi
else
    echo -e "${RED}❌ BigQuery credentials file not found at credentials/arboreal-logic-467306-k0-4a5ff4fe08b5.json${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Secrets created/updated${NC}"

# Build and deploy using Cloud Build
echo -e "${BLUE}🏗️ Building and deploying with Cloud Build...${NC}"
gcloud builds submit --config cloudbuild.yaml

echo -e "${GREEN}✅ Build and deployment completed${NC}"

# Wait for service to be ready
echo -e "${BLUE}⏳ Waiting for service to be ready...${NC}"
sleep 30

# Update Cloud Run service with secrets
echo -e "${BLUE}🔄 Updating Cloud Run service with secrets...${NC}"
gcloud run services update $SERVICE_NAME \
    --region=$REGION \
    --update-secrets=ZOHO_CLIENT_ID=zoho-client-id:latest \
    --update-secrets=ZOHO_CLIENT_SECRET=zoho-client-secret:latest \
    --update-secrets=ZOHO_REFRESH_TOKEN=zoho-refresh-token:latest \
    --update-secrets=GOOGLE_APPLICATION_CREDENTIALS=/secrets/bigquery-credentials=bigquery-credentials:latest \
    --set-env-vars=GOOGLE_CLOUD_PROJECT_ID=$PROJECT_ID,BIGQUERY_PROJECT_ID=$PROJECT_ID,BIGQUERY_DATASET_ID=zoho_crm,BIGQUERY_TABLE_ID=zoho_leads,ZOHO_DOMAIN=com.au

echo -e "${GREEN}✅ Service updated with secrets${NC}"

# Get service URL
SERVICE_URL=$(gcloud run services describe $SERVICE_NAME --region=$REGION --format='value(status.url)')

# Test the deployment
echo -e "${BLUE}🧪 Testing deployment...${NC}"
if curl -s -f "$SERVICE_URL/health" > /dev/null; then
    echo -e "${GREEN}✅ Health check passed${NC}"
else
    echo -e "${YELLOW}⚠️ Health check failed, but service might still be starting...${NC}"
fi

# Create or update Cloud Scheduler job for automated sync
echo -e "${BLUE}⏰ Setting up Cloud Scheduler job...${NC}"

# Delete existing job if it exists
if gcloud scheduler jobs describe zoho-sync-hourly --location=$REGION >/dev/null 2>&1; then
    echo "Deleting existing scheduler job..."
    gcloud scheduler jobs delete zoho-sync-hourly --location=$REGION --quiet
fi

# Create new scheduler job
gcloud scheduler jobs create http zoho-sync-hourly \
    --location=$REGION \
    --schedule="0 */1 * * *" \
    --uri="$SERVICE_URL/sync" \
    --http-method=POST \
    --headers="Content-Type=application/json" \
    --message-body='{"mode": "once"}' \
    --time-zone="UTC" \
    --description="Automated Zoho CRM to BigQuery sync - runs every hour"

echo -e "${GREEN}✅ Scheduler job created${NC}"

# Create IAM bindings for Cloud Scheduler
echo -e "${BLUE}🔐 Setting up IAM permissions for Cloud Scheduler...${NC}"
PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format="value(projectNumber)")
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:service-$PROJECT_NUMBER@gcp-sa-cloudscheduler.iam.gserviceaccount.com" \
    --role="roles/run.invoker" || true

echo -e "${GREEN}✅ IAM permissions configured${NC}"

# Final summary
echo ""
echo -e "${GREEN}🎉 Deployment completed successfully!${NC}"
echo ""
echo -e "${BLUE}📊 Deployment Summary:${NC}"
echo -e "🌐 Service URL: $SERVICE_URL"
echo -e "📊 Cloud Console: https://console.cloud.google.com/run/detail/$REGION/$SERVICE_NAME/metrics?project=$PROJECT_ID"
echo -e "📅 Scheduler: https://console.cloud.google.com/cloudscheduler?project=$PROJECT_ID"
echo -e "🔐 Secrets: https://console.cloud.google.com/security/secret-manager?project=$PROJECT_ID"
echo -e "📋 Logs: https://console.cloud.google.com/logs/query;query=resource.type%3D%22cloud_run_revision%22%0Aresource.labels.service_name%3D%22$SERVICE_NAME%22?project=$PROJECT_ID"
echo ""
echo -e "${BLUE}🧪 Test Commands:${NC}"
echo "Health Check: curl $SERVICE_URL/health"
echo "Manual Sync: curl -X POST $SERVICE_URL/sync -H 'Content-Type: application/json' -d '{\"mode\": \"once\"}'"
echo "Check Status: curl -X POST $SERVICE_URL/sync -H 'Content-Type: application/json' -d '{\"mode\": \"status\"}'"
echo ""
echo -e "${BLUE}📈 Monitoring:${NC}"
echo "View logs: gcloud logs read --service=$SERVICE_NAME --region=$REGION"
echo "Real-time logs: gcloud logs tail --service=$SERVICE_NAME --region=$REGION"
echo ""
echo -e "${GREEN}✅ Your Zoho CRM to BigQuery sync service is now running automatically every hour!${NC}"