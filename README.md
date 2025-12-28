# Dog Body Language Interpreter (Bedrock Edition)

A lightweight web app that lets you upload a dog image and get a plain-language interpretation of the dog's likely body language using AWS Bedrock (Llama 3.2 Vision).

## Folder Structure

- src/
  - backend/
    - server.py — FastAPI app, upload endpoint `/api/interpret`
    - config.py — env handling (AWS settings)
    - bedrock_client.py — AWS Bedrock integration, JSON parsing
  - frontend/
    - index.html — Single-page form + `fetch()` to backend
- tests/
  - test_bedrock_client.py — unit test for parser and client
- requirements.txt — Python dependencies
- .env.template — environment variables template
- Dockerfile — container build
- .dockerignore — container context ignores
- README.md — you are here

## Features

- Webcam Capture: Start the camera with "Open Camera", take a still with "Capture Photo", and analyze it like an uploaded file.
- AWS Bedrock Integration: Uses Llama 3.2 Vision for high-quality image analysis.
- Multi-camera selection: Choose among available webcams.

## Setup

1. Create `.env` from template and add your AWS credentials:

```bash
cp .env.template .env
# Edit .env and add your AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY
```

2. Install dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Running Locally

- Start the backend:

```bash
source .venv/bin/activate
uvicorn src.backend.server:app --host 0.0.0.0 --port 8000
```

- Open the frontend: http://localhost:8000/

## Testing

Run tests:
```bash
pytest
```

## Container

Build and Run:
```bash
docker compose up --build
```
