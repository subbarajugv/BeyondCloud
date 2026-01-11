# Python/FastAPI Backend

Implementation of the llama.cpp Authenticated WebUI backend using Python and FastAPI.

## Quick Start

```bash
cd backend-python
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your configuration
uvicorn main:app --reload --port 3000
```

## API Contract

This backend implements the exact same API as `backend-nodejs`.  
See [api-contract.md](../docs/api-contract.md) for complete specification.

## Project Structure

```
backend-python/
├── main.py                 # FastAPI app entry point
├── requirements.txt        # Python dependencies
├── .env.example           # Environment template
├── app/
│   ├── __init__.py
│   ├── config.py          # Settings & configuration
│   ├── database.py        # PostgreSQL connection
│   ├── models/            # SQLAlchemy models
│   │   ├── user.py
│   │   ├── conversation.py
│   │   ├── message.py
│   │   └── token.py
│   ├── schemas/           # Pydantic schemas
│   │   ├── auth.py
│   │   ├── conversation.py
│   │   └── message.py
│   ├── routers/           # API routes
│   │   ├── auth.py
│   │   ├── conversations.py
│   │   ├── messages.py
│   │   ├── chat.py
│   │   ├── settings.py
│   │   └── mcp.py         # Placeholder
│   ├── services/          # Business logic
│   │   ├── auth_service.py
│   │   ├── llm_router.py
│   │   └── mcp_service.py # Placeholder
│   └── utils/
│       ├── security.py    # JWT, password hashing
│       └── email.py       # Email sending
└── tests/
    └── ...
```

## Dependencies

- **FastAPI** - Web framework
- **SQLAlchemy** - ORM
- **Pydantic** - Validation
- **python-jose** - JWT handling
- **passlib** - Password hashing
- **httpx** - Async HTTP client (for LLM calls)
- **asyncpg** - PostgreSQL async driver

## Environment Variables

```env
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/llamacpp_chat
JWT_SECRET=your-secret-key
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USER=user@example.com
SMTP_PASSWORD=password
FRONTEND_URL=http://localhost:5173
```
