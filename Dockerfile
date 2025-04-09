# FROM python:3.11-slim

# # Install system dependencies
# RUN apt-get update && apt-get install -y \
#     gcc \
#     libgomp1 \
#     libc6 \
#     nodejs\
#     npm \
#     nginx \
#     && apt-get clean

# # Add memory optimization
# ENV PYTHONUNBUFFERED=1 \
#     PYTHONDONTWRITEBYTECODE=1 \
#     PIP_NO_CACHE_DIR=1 \
#     PIP_DISABLE_PIP_VERSION_CHECK=1
# # Set the working directory
# WORKDIR /app

# # Copy the application code
# COPY . .

# # Copy nginx config
# COPY nginx/nginx.conf /etc/nginx/nginx.conf

# RUN npm install kill-port --save-dev

# # Install Python dependencies
# RUN pip install --no-cache-dir -r requirements.txt

# # Collect static files
# RUN python manage.py collectstatic --noinput

# # Apply database migrations
# RUN python manage.py migrate

# # Expose the port the app runs on
# EXPOSE 8000

# # Start the application
# CMD ["gunicorn", "VisAutoML.wsgi:application", "--bind", "0.0.0.0:8000"]

FROM python:3.11-slim

# System dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    build-essential \
    libgomp1 \
    libc6 \
    nodejs \
    npm \
    nginx \
    curl \
    gettext \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Python env
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Copy application code
COPY . .

# Copy nginx config
COPY nginx.conf /etc/nginx/nginx.conf

# Install Node dependency
RUN npm install kill-port --save-dev

# ✅ Fix: install wheel before requirements
RUN pip install --upgrade pip setuptools wheel
RUN pip install --no-cache-dir -r requirements.txt

# Django setup
RUN python manage.py collectstatic --noinput
RUN python manage.py migrate

EXPOSE 80

# Final command
CMD bash -c "\
    service nginx start && \
    gunicorn VisAutoML.wsgi:application --bind 0.0.0.0:8000"
