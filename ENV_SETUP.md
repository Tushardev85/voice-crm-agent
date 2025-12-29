# Environment Variables Setup

Create a `.env` file in the root directory with the following variables:

```bash
# Redis Configuration
REDIS_URL=redis://redis:6379/0

# Twilio Configuration
TWILIO_AUTH_TOKEN=your_twilio_auth_token_here

# OpenAI Configuration
OPENAI_API_KEY=your_openai_api_key_here

# Cartesia Configuration (Speech-to-Text)
CARTESIA_API_KEY=your_cartesia_api_key_here

# ElevenLabs Configuration (Text-to-Speech)
ELEVENLABS_API_KEY=your_elevenlabs_api_key_here

# Optional: Deepgram (if switching STT service)
# DEEPGRAM_API_KEY=your_deepgram_api_key_here

# Optional: Google Cloud Storage (if using transcription storage)
# GCP_STORAGE_BUCKET_NAME=your_bucket_name
# GOOGLE_APPLICATION_CREDENTIALS=/path/to/credentials.json

# Optional: Analysis OpenAI (if re-enabling analysis features)
# ANALYSIS_OPENAI_API_KEY=your_analysis_openai_key
# ANALYSIS_OPENAI_MODEL=gpt-4o-mini
```

## Quick Setup

```bash
# Create .env file
cat > .env << 'EOF'
REDIS_URL=redis://redis:6379/0
TWILIO_AUTH_TOKEN=your_actual_token
OPENAI_API_KEY=your_actual_key
CARTESIA_API_KEY=your_actual_key
ELEVENLABS_API_KEY=your_actual_key
EOF

# Edit with your actual credentials
nano .env
```

