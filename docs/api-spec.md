# SupportPilot AI — API Specification

**Base URL (Production):** `https://your-api.railway.app`
**Base URL (Development):** `http://localhost:8000`
**API Version Prefix:** `/api/v1`

All request bodies use `application/json`. All responses return `application/json`.

---

## Table of Contents

1. [Authentication](#authentication)
2. [Error Format](#error-format)
3. [Status Codes](#status-codes)
4. [Rate Limiting](#rate-limiting)
5. [Endpoints](#endpoints)
   - [Auth](#auth-endpoints)
   - [Conversations](#conversation-endpoints)
   - [Messages](#message-endpoints)
   - [Tickets](#ticket-endpoints)
   - [Support Form](#support-endpoint)
   - [Admin](#admin-endpoints)

---

## Authentication

All protected endpoints require a Bearer token in the `Authorization` header.

```
Authorization: Bearer <access_token>
```

Tokens are issued on login/signup and expire after `ACCESS_TOKEN_EXPIRE_MINUTES` (default: 10080 minutes / 7 days). Tokens use HS256 signing.

Endpoints marked **Public** do not require authentication.
Endpoints marked **Auth** require a valid token for any user.
Endpoints marked **Admin** require a valid token where `user.role == "admin"`.

---

## Error Format

All errors return a consistent JSON body:

```json
{
  "detail": "Human-readable error message"
}
```

For validation errors (422 Unprocessable Entity), the response follows FastAPI's standard format:

```json
{
  "detail": [
    {
      "loc": ["body", "email"],
      "msg": "value is not a valid email address",
      "type": "value_error.email"
    }
  ]
}
```

---

## Status Codes

| Code | Meaning |
|---|---|
| 200 | OK — Request succeeded |
| 201 | Created — Resource successfully created |
| 400 | Bad Request — Invalid input |
| 401 | Unauthorized — Missing or invalid token |
| 403 | Forbidden — Insufficient permissions |
| 404 | Not Found — Resource does not exist |
| 409 | Conflict — Resource already exists (e.g., duplicate email) |
| 422 | Unprocessable Entity — Request body validation failed |
| 500 | Internal Server Error — Unexpected server error |

---

## Rate Limiting

Rate limiting is not yet enforced at the application layer. For production deployments, configure rate limiting at the reverse proxy (Railway/Nginx) or via the `slowapi` middleware. Recommended limits:

- Auth endpoints: 10 requests / minute per IP
- AI-powered endpoints (`/messages`, `/support/submit`): 30 requests / minute per user
- Admin endpoints: 60 requests / minute per user

---

## Endpoints

---

## Auth Endpoints

### POST `/api/v1/auth/signup`

Register a new user account.

**Auth:** Public

**Request Body:**
```json
{
  "name": "Jane Smith",
  "email": "jane@example.com",
  "password": "SecurePass123!"
}
```

| Field | Type | Required | Constraints |
|---|---|---|---|
| `name` | string | Yes | 1–100 characters |
| `email` | string | Yes | Valid email format |
| `password` | string | Yes | Minimum 8 characters |

**Response `201`:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user": {
    "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "name": "Jane Smith",
    "email": "jane@example.com",
    "role": "customer",
    "is_active": true,
    "created_at": "2025-01-15T10:30:00Z"
  }
}
```

**Error Responses:**
- `409 Conflict` — Email already registered
- `422` — Validation error

---

### POST `/api/v1/auth/login`

Authenticate and receive a JWT token.

**Auth:** Public

**Request Body:**
```json
{
  "email": "jane@example.com",
  "password": "SecurePass123!"
}
```

**Response `200`:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user": {
    "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "name": "Jane Smith",
    "email": "jane@example.com",
    "role": "customer",
    "is_active": true,
    "created_at": "2025-01-15T10:30:00Z"
  }
}
```

**Error Responses:**
- `401 Unauthorized` — Invalid credentials
- `403 Forbidden` — Account deactivated

---

### GET `/api/v1/auth/me`

Get the currently authenticated user's profile.

**Auth:** Auth

**Response `200`:**
```json
{
  "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "name": "Jane Smith",
  "email": "jane@example.com",
  "role": "customer",
  "is_active": true,
  "created_at": "2025-01-15T10:30:00Z"
}
```

**Error Responses:**
- `401 Unauthorized` — Missing or expired token

---

## Conversation Endpoints

### GET `/api/v1/conversations`

List all conversations belonging to the current user.

**Auth:** Auth

**Query Parameters:**
| Parameter | Type | Default | Description |
|---|---|---|---|
| `skip` | integer | 0 | Pagination offset |
| `limit` | integer | 20 | Page size (max 100) |

**Response `200`:**
```json
[
  {
    "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "user_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "channel": "web_form",
    "status": "active",
    "subject": "Order not delivered",
    "created_at": "2025-01-15T10:30:00Z",
    "updated_at": "2025-01-15T10:35:00Z"
  }
]
```

---

### POST `/api/v1/conversations`

Create a new conversation.

**Auth:** Auth

**Request Body:**
```json
{
  "subject": "Billing inquiry",
  "channel": "web"
}
```

| Field | Type | Required | Values |
|---|---|---|---|
| `subject` | string | Yes | 1–200 characters |
| `channel` | string | No | `web`, `email`, `whatsapp`, `web_form` (default: `web`) |

**Response `201`:**
```json
{
  "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "user_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "channel": "web",
  "status": "active",
  "subject": "Billing inquiry",
  "created_at": "2025-01-15T10:30:00Z",
  "updated_at": "2025-01-15T10:30:00Z"
}
```

---

### GET `/api/v1/conversations/{id}`

Get a conversation and its full message history.

**Auth:** Auth

**Path Parameters:**
| Parameter | Type | Description |
|---|---|---|
| `id` | UUID | Conversation ID |

**Response `200`:**
```json
{
  "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "user_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "channel": "web",
  "status": "active",
  "subject": "Billing inquiry",
  "created_at": "2025-01-15T10:30:00Z",
  "updated_at": "2025-01-15T10:35:00Z",
  "messages": [
    {
      "id": "msg-uuid-1",
      "conversation_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
      "sender_type": "customer",
      "content": "I was charged twice this month.",
      "intent": null,
      "ai_confidence": null,
      "metadata": {},
      "created_at": "2025-01-15T10:30:00Z"
    },
    {
      "id": "msg-uuid-2",
      "conversation_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
      "sender_type": "ai",
      "content": "I'm sorry to hear about the duplicate charge. Let me look into this for you...",
      "intent": "billing",
      "ai_confidence": 0.94,
      "metadata": { "model": "gpt-4o-mini", "escalated": false },
      "created_at": "2025-01-15T10:30:02Z"
    }
  ]
}
```

**Error Responses:**
- `404 Not Found` — Conversation not found
- `403 Forbidden` — Conversation belongs to another user (non-admin)

---

## Message Endpoints

### POST `/api/v1/conversations/{id}/messages`

Send a message in a conversation. Triggers AI processing and returns both the customer message and the AI response.

**Auth:** Auth

**Path Parameters:**
| Parameter | Type | Description |
|---|---|---|
| `id` | UUID | Conversation ID |

**Request Body:**
```json
{
  "content": "I was charged twice for my subscription this month."
}
```

| Field | Type | Required | Constraints |
|---|---|---|---|
| `content` | string | Yes | 1–5000 characters |

**Response `201`:**
```json
{
  "customer_message": {
    "id": "msg-uuid-1",
    "conversation_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "sender_type": "customer",
    "content": "I was charged twice for my subscription this month.",
    "intent": null,
    "ai_confidence": null,
    "metadata": {},
    "created_at": "2025-01-15T10:30:00Z"
  },
  "ai_message": {
    "id": "msg-uuid-2",
    "conversation_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "sender_type": "ai",
    "content": "I understand how frustrating a double charge can be. I can see your account details and will process a refund for the duplicate charge within 3-5 business days. You'll receive a confirmation email shortly.",
    "intent": "billing",
    "ai_confidence": 0.96,
    "metadata": {
      "model": "gpt-4o-mini",
      "escalated": false,
      "escalation_reason": null
    },
    "created_at": "2025-01-15T10:30:02Z"
  }
}
```

**Error Responses:**
- `404 Not Found` — Conversation not found
- `403 Forbidden` — Access denied
- `400 Bad Request` — Conversation is closed

---

## Ticket Endpoints

### GET `/api/v1/tickets`

List all tickets for the current user.

**Auth:** Auth

**Query Parameters:**
| Parameter | Type | Default | Description |
|---|---|---|---|
| `skip` | integer | 0 | Pagination offset |
| `limit` | integer | 20 | Page size (max 100) |
| `status` | string | — | Filter by status |
| `priority` | string | — | Filter by priority |

**Response `200`:**
```json
[
  {
    "id": "ticket-uuid-1",
    "user_id": "user-uuid",
    "conversation_id": "conv-uuid",
    "title": "Double charge on subscription",
    "description": "I was charged twice for my Pro subscription in January.",
    "category": "billing",
    "priority": "high",
    "status": "open",
    "assigned_to": null,
    "created_at": "2025-01-15T10:30:00Z",
    "updated_at": "2025-01-15T10:30:00Z"
  }
]
```

---

### POST `/api/v1/tickets`

Create a new support ticket.

**Auth:** Auth

**Request Body:**
```json
{
  "title": "Cannot access my account",
  "description": "I reset my password but still cannot log in.",
  "category": "technical",
  "priority": "high",
  "conversation_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
}
```

| Field | Type | Required | Values |
|---|---|---|---|
| `title` | string | Yes | 1–200 characters |
| `description` | string | Yes | 1–5000 characters |
| `category` | string | No | `billing`, `technical`, `account`, `shipping`, `general` |
| `priority` | string | No | `low`, `medium`, `high`, `urgent` (default: `medium`) |
| `conversation_id` | UUID | No | Link to existing conversation |

**Response `201`:**
```json
{
  "id": "ticket-uuid-new",
  "user_id": "user-uuid",
  "conversation_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "title": "Cannot access my account",
  "description": "I reset my password but still cannot log in.",
  "category": "technical",
  "priority": "high",
  "status": "open",
  "assigned_to": null,
  "created_at": "2025-01-15T11:00:00Z",
  "updated_at": "2025-01-15T11:00:00Z"
}
```

---

### GET `/api/v1/tickets/{id}`

Get a single ticket by ID.

**Auth:** Auth

**Response `200`:** Full ticket object (same schema as above).

**Error Responses:**
- `404` — Ticket not found
- `403` — Ticket belongs to another user

---

### PATCH `/api/v1/tickets/{id}`

Update a ticket's status, priority, or assignment.

**Auth:** Auth (customers can update own tickets; admins can update any)

**Request Body (all fields optional):**
```json
{
  "status": "in_progress",
  "priority": "urgent",
  "assigned_to": "admin-user-uuid"
}
```

| Field | Type | Values |
|---|---|---|
| `status` | string | `open`, `in_progress`, `resolved`, `closed` |
| `priority` | string | `low`, `medium`, `high`, `urgent` |
| `assigned_to` | UUID or null | Admin user ID |
| `title` | string | 1–200 characters |
| `description` | string | 1–5000 characters |

**Response `200`:** Updated ticket object.

---

## Support Endpoint

### POST `/api/v1/support/submit`

Submit a support request via the web form. Creates a conversation, a message, generates an AI response, and opens a ticket — all in a single request.

**Auth:** Public (creates or matches a user by email)

**Request Body:**
```json
{
  "name": "John Doe",
  "email": "john@example.com",
  "subject": "Order hasn't arrived",
  "description": "I placed order #12345 two weeks ago and it still hasn't arrived.",
  "category": "shipping"
}
```

| Field | Type | Required | Constraints |
|---|---|---|---|
| `name` | string | Yes | 1–100 characters |
| `email` | string | Yes | Valid email |
| `subject` | string | Yes | 1–200 characters |
| `description` | string | Yes | 1–5000 characters |
| `category` | string | No | `billing`, `technical`, `account`, `shipping`, `general` |

**Response `201`:**
```json
{
  "conversation_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "ticket_id": "ticket-uuid-new",
  "ai_response": "Thank you for reaching out, John. I can see your concern about order #12345. Our records show it was shipped on January 10th via standard delivery. I've flagged this for our shipping team to investigate and you'll receive an update within 24 hours.",
  "message": "Your support request has been received. Reference ticket ID: ticket-uuid-new"
}
```

---

## Admin Endpoints

All admin endpoints require `role == "admin"`.

---

### GET `/api/v1/admin/stats`

Get platform-wide statistics for the admin dashboard.

**Auth:** Admin

**Response `200`:**
```json
{
  "total_users": 142,
  "total_tickets": 389,
  "open_tickets": 47,
  "in_progress_tickets": 23,
  "resolved_tickets": 289,
  "closed_tickets": 30,
  "total_conversations": 412,
  "active_conversations": 51,
  "tickets_today": 8,
  "avg_resolution_hours": 18.4
}
```

---

### GET `/api/v1/admin/tickets`

Get all tickets across all users.

**Auth:** Admin

**Query Parameters:**
| Parameter | Type | Default | Description |
|---|---|---|---|
| `skip` | integer | 0 | Pagination offset |
| `limit` | integer | 50 | Page size (max 200) |
| `status` | string | — | Filter by status |
| `priority` | string | — | Filter by priority |
| `category` | string | — | Filter by category |

**Response `200`:** Array of ticket objects (same schema as user tickets, includes user info).

---

### GET `/api/v1/admin/conversations`

Get all conversations across all users.

**Auth:** Admin

**Query Parameters:**
| Parameter | Type | Default | Description |
|---|---|---|---|
| `skip` | integer | 0 | Pagination offset |
| `limit` | integer | 50 | Page size (max 200) |
| `channel` | string | — | Filter by channel |
| `status` | string | — | Filter by status |

**Response `200`:** Array of conversation objects.

---

### GET `/api/v1/admin/users`

Get all registered users.

**Auth:** Admin

**Query Parameters:**
| Parameter | Type | Default | Description |
|---|---|---|---|
| `skip` | integer | 0 | Pagination offset |
| `limit` | integer | 50 | Page size (max 200) |
| `role` | string | — | Filter by role (`customer`, `admin`) |

**Response `200`:**
```json
[
  {
    "id": "user-uuid",
    "name": "Jane Smith",
    "email": "jane@example.com",
    "role": "customer",
    "is_active": true,
    "created_at": "2025-01-10T08:00:00Z",
    "ticket_count": 3,
    "conversation_count": 5
  }
]
```
