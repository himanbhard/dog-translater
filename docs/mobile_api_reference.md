# Mobile App API Reference

Base URL: `<YOUR_CLOUD_RUN_URL>` (e.g., `https://dog-translator-service-xyz.run.app`)

## Authentication

### Login / Sign Up (Hybrid)
**POST** `/auth/login`

Authenticates an existing user or creates a new account if the email is not found.

**Request Body (JSON):**
```json
{
  "email": "user@example.com",
  "password": "yourpassword"
}
```

**Response (200 OK):**
```json
{
  "user": {
    "id": "uuid-string",
    "email": "user@example.com",
    "is_verified": true
  },
  "access_token": "eyJhbGciOi...",
  "token_type": "bearer"
}
```

---

## Interpretation

### Analyze Dog Image
**POST** `/api/v1/interpret`

Uploads an image for body language analysis.

**Headers:**
- `Authorization`: `Bearer <access_token>`
- `Content-Type`: `multipart/form-data`

**Form Data:**
- `image`: (File, required) JPEG or PNG image.
- `tone`: (String, optional) `playful`, `calm`, or `trainer`.
- `save`: (Boolean, optional) `true` to save to history.

**Response (200 OK):**
```json
{
  "status": "ok",
  "explanation": "The dog appears to be...",
  "confidence": 0.95,
  "has_pet": true,
  "source": "vertex_gemini",
  "share_id": "optional-uuid-if-saved"
}
```

---

## Features

### Explain Behavior
**GET** `/api/v1/explain`

Search for explanations of specific dog behaviors.

**Headers:**
- `Authorization`: `Bearer <access_token>`

**Query Parameters:**
- `behavior`: (String, required) E.g., "tail wagging to the left"

**Response (200 OK):**
```json
{
  "status": "ok",
  "behavior": "tail wagging to the left",
  "results": [
    {
      "title": "Why do dogs wag their tails?",
      "snippet": "...",
      "link": "https://..."
    }
  ]
}
```

### Get History
**GET** `/api/v1/history`

Retrieve the user's past interpretations.

**Headers:**
- `Authorization`: `Bearer <access_token>`

**Response (200 OK):**
```json
[
  {
    "id": "uuid-string",
    "explanation": "...",
    "confidence": 0.9,
    "created_at": "2023-10-27T10:00:00",
    "image_path": "..."
  }
]
```

### Get Shared Result
**GET** `/api/share/{share_id}`

Fetch a specific interpretation by ID (Public/Unauthenticated).

**Response (200 OK):**
```json
{
  "id": "uuid-string",
  "explanation": "...",
  "confidence": 0.85,
  "created_at": "..."
}
```

---

## System

### Health Check
**GET** `/healthz`

Checks valid database connection.

**Response (200 OK):**
```json
{
  "status": "ok",
  "db": "connected"
}
```
