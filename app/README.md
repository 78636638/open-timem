# TiMem API Service

FastAPI-based REST API service for TiMem temporal memory system.

## 🚀 Quick Start

### Prerequisites

- Python 3.10+
- PostgreSQL database
- Qdrant vector database (optional)
- Redis cache (optional)

### Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Copy and configure environment variables
cp .env.example .env
# Edit .env with your settings

# Start databases (using Docker)
cd migration && docker-compose up -d

# Run the API server
python -m app.main
```

### Using Docker

```bash
# Build and run all services
docker-compose up -d

# View logs
docker-compose logs -f api

# Stop services
docker-compose down
```

## 📚 API Documentation

Once running, access the API documentation:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/openapi.json

## 🔌 API Endpoints

### Health & System

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/health` | Basic health check |
| GET | `/api/v1/health/ready` | Readiness probe |
| GET | `/api/v1/health/live` | Liveness probe |
| GET | `/api/v1/health/metrics` | System metrics |
| GET | `/api/v1/health/services` | Service status |

### Memory Operations

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/memory/add` | Add new memory |
| POST | `/api/v1/memory/search` | Search memories |
| GET | `/api/v1/memory/{memory_id}` | Get memory by ID |
| PUT | `/api/v1/memory/{memory_id}` | Update memory |
| DELETE | `/api/v1/memory/{memory_id}` | Delete memory |
| GET | `/api/v1/memory/stats/user/{user_id}` | Get user memory stats |

### Session Management

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/sessions/create` | Create session |
| GET | `/api/v1/sessions/user/{user_id}` | Get user sessions |
| GET | `/api/v1/sessions/{session_id}` | Get session details |
| GET | `/api/v1/sessions/{session_id}/dialogues` | Get session dialogues |
| DELETE | `/api/v1/sessions/{session_id}` | Delete session |

### User Management

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/users/register` | Register user |
| POST | `/api/v1/users/auth/login` | User login |
| GET | `/api/v1/users/{user_id}` | Get user info |
| POST | `/api/v1/users/characters` | Create character |
| GET | `/api/v1/users/characters/{character_id}` | Get character |
| DELETE | `/api/v1/users/characters/{character_id}` | Delete character |

## 📝 Example Usage

### Add Memory

```bash
curl -X POST http://localhost:8000/api/v1/memory/add \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {"role": "user", "content": "Hello, my name is Zhang Ming"},
      {"role": "assistant", "content": "Hello Zhang Ming!"}
    ],
    "user_id": "user_001",
    "character_id": "assistant",
    "session_id": "session_001"
  }'
```

### Search Memory

```bash
curl -X POST http://localhost:8000/api/v1/memory/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "user'\''s name",
    "user_id": "user_001",
    "limit": 5
  }'
```

### Health Check

```bash
curl http://localhost:8000/api/v1/health
```

## ⚙️ Configuration

Configuration is loaded from `config/settings.yaml` with environment variable overrides.

Key settings:

```yaml
app:
  host: 0.0.0.0
  port: 8000
  debug: false
  workers: 1
```

## 🔒 Authentication

The API currently supports simple username/password authentication for cloud service.

For production, consider adding:
- JWT token authentication
- API key authentication
- Rate limiting

## 📊 Monitoring

### Prometheus Metrics

Access metrics at `/api/v1/health/metrics` for monitoring integration.

### Health Checks

Kubernetes-compatible health check endpoints:
- `/api/v1/health/live` - Liveness probe
- `/api/v1/health/ready` - Readiness probe

## 🛠️ Development

### Run with Auto-reload

```bash
python -m app.main --reload
```

### Run Tests

```bash
pytest tests/api/
```

## 📦 Project Structure

```
app/
├── __init__.py
├── main.py              # FastAPI application entry point
api/
├── __init__.py
├── routes/
│   ├── __init__.py
│   ├── memory.py        # Memory operations
│   ├── session.py       # Session management
│   ├── user.py          # User management
│   └── health.py        # Health checks
```

## 🔗 Related Documentation

- [Main README](../README.md)
- [Cloud Service SDK](../cloud-service/README.md)
- [Configuration Guide](../docs/configuration.md)