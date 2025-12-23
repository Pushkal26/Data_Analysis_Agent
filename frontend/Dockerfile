# ==============================
# Frontend Dockerfile (Streamlit)
# ==============================
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Copy frontend code
COPY . .

# Expose Streamlit port
EXPOSE 8501

# Set environment variables for Streamlit
ENV STREAMLIT_SERVER_HEADLESS=true \
    STREAMLIT_SERVER_PORT=8501 \
    STREAMLIT_SERVER_ENABLECORS=false \
    STREAMLIT_SERVER_FILEWATCHER_TYPE=none \
    BACKEND_URL=http://backend:8000

# Start Streamlit
CMD ["streamlit", "run", "app.py"]
