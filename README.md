# Google Cloud Run Deployment Guide

## Prerequisites

1. Google Cloud SDK installed (`gcloud` CLI)
2. Docker installed
3. Google Cloud project with billing enabled

## Quick Deploy

```bash
# 1. Authenticate with Google Cloud
gcloud auth login
gcloud auth configure-docker

# 2. Set your project
gcloud config set project YOUR_PROJECT_ID

# 3. Deploy to Cloud Run
gcloud run deploy guitar-transcription \
  --source . \
  --memory 8Gi \
  --cpu 2 \
  --min-instances 0 \
  --max-instances 10 \
  --region us-central1 \
  --allow-unauthenticated
```

## Configuration Options

### Memory & CPU
- `--memory 8Gi`: 8GB RAM (minimum for PyTorch)
- `--cpu 2`: 2 vCPUs (balances cost and performance)

### Scaling
- `--min-instances 0`: Scale to zero when idle (saves cost)
- `--min-instances 1`: Always keep one instance warm (~$10/month, eliminates cold starts)
- `--max-instances 10`: Maximum concurrent instances

### Cost Optimization
```bash
# Cheapest option (scale to zero)
gcloud run deploy guitar-transcription \
  --source . \
  --memory 8Gi \
  --cpu 2 \
  --min-instances 0 \
  --region us-central1

# Always-warm option (no cold starts)
gcloud run deploy guitar-transcription \
  --source . \
  --memory 8Gi \
  --cpu 2 \
  --min-instances 1 \
  --region us-central1
```

## Testing

```bash
# Get the service URL
SERVICE_URL=$(gcloud run services describe guitar-transcription --region us-central1 --format='value(status.url)')

# Test health check
curl $SERVICE_URL/health

# Test transcription
curl -X POST $SERVICE_URL/transcribe \
  -F "file=@your_audio_file.mp3"
```

## Environment Variables

Set sensitive values via Google Cloud Secrets:

```bash
# Create a secret
echo -n "your-api-token" | gcloud secrets create api-token --data-file=-

# Grant access to the service
gcloud secrets add-iam-policy-binding api-token \
  --member="serviceAccount:YOUR_SERVICE_ACCOUNT" \
  --roles="roles/secretmanager.secretAccessor"

# Update the service to use the secret
gcloud run services update guitar-transcription \
  --update-secrets=CLOUD_RUN_API=api-token:latest
```

## Local Development

```bash
# Build and run locally
docker build -t guitar-transcription .
docker run -p 8080:8080 -e CLOUD_RUN_API=test guitar-transcription

# Test locally
curl http://localhost:8080/health
curl -X POST http://localhost:8080/transcribe -F "file=@test.mp3"
```

## Cost Estimation

| Requests/month | Cost (min-instances=0) | Cost (min-instances=1) |
|----------------|------------------------|------------------------|
| 1,000 | ~$1.20 | ~$11.20 |
| 10,000 | ~$24 | ~$34 |
| 50,000 | ~$84 | ~$94 |
| 100,000 | ~$164 | ~$174 |

## Advantages over Modal

- **No random 30-100s execution bugs** (Cloud Run uses block-level image streaming, not FUSE lazy loading)
- **Consistent 3-7s execution time**
- **15-minute warm grace period** (most requests hit warm instances)
- **Predictable pricing** (no surprises)
