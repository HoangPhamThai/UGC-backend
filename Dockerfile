# Official Playwright image (Ubuntu Noble = Python 3.12) with Chromium + all
# browser OS deps preinstalled. Avoids `playwright install --with-deps` failing
# on Debian (python:3.12-slim), which Playwright doesn't officially support.
# Keep this tag's version in lockstep with playwright in requirements.txt.
FROM mcr.microsoft.com/playwright/python:v1.49.0-noble

WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .
COPY .env .

# Install dependencies (playwright==1.49.0 matches the browsers baked into the image)
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY ./app ./app

# Expose the port FastAPI will run on
EXPOSE 8080

# Set Python path to include the current directory
ENV PYTHONPATH=/app

# Start the FastAPI server
CMD ["uvicorn", "app.app:app", "--host", "0.0.0.0", "--port", "8080", "--workers", "2", "--reload"]
