# Docker Setup for Voice CRM Agent

## Prerequisites

- Docker (version 20.10 or higher)
- Docker Compose (version 2.0 or higher)
- A `.env` file with required credentials (see `.env.example`)

## Quick Start

### 1. Setup Environment Variables

Copy the example environment file and fill in your credentials:

```bash
cp .env.example .env
# Edit .env with your actual API keys and tokens
```

### 2. Start the Application

**Start all services (app + Redis):**
```bash
docker-compose up -d
```

**View logs:**
```bash
docker-compose logs -f
```

**View app logs only:**
```bash
docker-compose logs -f app
```

### 3. Stop the Application

```bash
docker-compose down
```

**To also remove volumes (Redis data):**
```bash
docker-compose down -v
```

## Docker Compose Services

### 1. **Redis** (`redis`)
- Caching service for call prompts and metadata
- Port: `6379`
- Data persisted in Docker volume `redis_data`

### 2. **Voice CRM Agent** (`app`)
- Main application service
- Port: `8080`
- Depends on Redis

## Development vs Production

### Development Mode (Current Setup)

The `docker-compose.yml` includes volume mounts for hot-reloading:

```yaml
volumes:
  - ./app.py:/app/app.py
  - ./bot.py:/app/bot.py
  - ./utils:/app/utils
```

This allows you to edit code locally and see changes reflected in the container.

### Production Mode

For production deployment:

1. Remove the volume mounts from `docker-compose.yml`
2. Use environment variables properly
3. Consider using Docker secrets for sensitive data
4. Build and push image to a registry:

```bash
docker build -t voice-crm-agent:latest .
docker push your-registry/voice-crm-agent:latest
```

## Useful Commands

### Rebuild after code changes:
```bash
docker-compose up -d --build
```

### Check service status:
```bash
docker-compose ps
```

### Execute commands in running container:
```bash
docker-compose exec app bash
```

### View Redis data:
```bash
docker-compose exec redis redis-cli
```

### Restart a specific service:
```bash
docker-compose restart app
```

## Troubleshooting

### Redis connection issues:

Check Redis is running:
```bash
docker-compose ps redis
docker-compose logs redis
```

Test Redis connection:
```bash
docker-compose exec redis redis-cli ping
# Should return: PONG
```

### Application won't start:

Check logs:
```bash
docker-compose logs app
```

Verify environment variables:
```bash
docker-compose exec app env | grep -E "(REDIS|TWILIO|OPENAI|CARTESIA|ELEVENLABS)"
```

### Port conflicts:

If ports 8080 or 6379 are already in use, edit `docker-compose.yml`:

```yaml
ports:
  - "8081:8080"  # Change host port (left side)
```

## Endpoints

Once running, the application is available at:

- **Health check**: http://localhost:8080/
- **TwiML endpoint**: http://localhost:8080/agent (POST)
- **WebSocket**: ws://localhost:8080/ws

## Network Architecture

```
┌─────────────────────────────────────────┐
│          Docker Network                 │
│                                         │
│  ┌─────────────┐    ┌───────────────┐ │
│  │   Redis     │◄───│  Voice CRM    │ │
│  │   :6379     │    │  Agent :8080  │ │
│  └─────────────┘    └───────┬───────┘ │
│                              │          │
└──────────────────────────────┼──────────┘
                               │
                    External Services:
                    • Twilio
                    • OpenAI
                    • Cartesia
                    • ElevenLabs
```

## Environment Variables Reference

| Variable | Required | Description |
|----------|----------|-------------|
| `REDIS_URL` | Yes | Redis connection URL |
| `TWILIO_AUTH_TOKEN` | Yes | Twilio authentication token |
| `OPENAI_API_KEY` | Yes | OpenAI API key for LLM |
| `CARTESIA_API_KEY` | Yes | Cartesia API key for STT |
| `ELEVENLABS_API_KEY` | Yes | ElevenLabs API key for TTS |
| `DEEPGRAM_API_KEY` | No | Alternative STT service |
| `GCP_STORAGE_BUCKET_NAME` | No | Google Cloud Storage bucket |

## Notes

- Redis data persists in a Docker volume even after stopping containers
- For production, use a managed Redis service (AWS ElastiCache, Redis Cloud, etc.)
- The application uses WebSockets - ensure your reverse proxy (nginx, etc.) supports them
- For cloud deployment (AWS, GCP, Azure), consider using their container services

