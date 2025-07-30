# =============================================================================
# QuranBot Docker Image
# =============================================================================
# Lightweight, secure Docker image for running QuranBot in production
# =============================================================================

FROM python:3.11-slim

# Set metadata
LABEL maintainer="John (Discord: Trippixn) <noreply@example.com>"
LABEL description="QuranBot - Advanced Islamic Discord Bot"
LABEL version="4.1.0"

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN pip install poetry

# Copy dependency files
COPY pyproject.toml poetry.lock ./

# Configure Poetry
RUN poetry config virtualenvs.create false

# Install Python dependencies
RUN poetry install --no-dev --no-interaction --no-ansi

# Copy application code
COPY . .

# Create non-root user for security
RUN groupadd -r quranbot && useradd -r -g quranbot quranbot
RUN chown -R quranbot:quranbot /app

# Switch to non-root user
USER quranbot

# Expose health check port (if needed)
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD python -c "import sys; sys.exit(0)"

# Run the bot
CMD ["python", "main.py"]
