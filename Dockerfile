# Base image
FROM python:3.10

# Accept build-time argument
ARG DEVELOPMENT

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONPATH="/code"

# Set working directory
WORKDIR /code/ssmixtools

# Copy only requirements first (for Docker cache efficiency)
COPY requirements.txt /code/ssmixtools/

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the project
COPY . /code/ssmixtools

# Install ssmixtools (editable if DEVELOPMENT=true)
RUN if [ "$DEVELOPMENT" = "true" ]; then \
        pip install -e .; \
    else \
        pip install .; \
    fi
