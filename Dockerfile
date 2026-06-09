# Use an official Python runtime as a parent image
FROM python:3.12-slim

WORKDIR /app
# Set the working directory

# Copy requirements first for better caching
COPY requirements.txt .
COPY .env .

RUN apt-get update

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY ./app ./app

# Expose the port FastAPI will run on
EXPOSE 8080

# Set Python path to include the current directory
ENV PYTHONPATH=/app

# Start the FastAPI server
CMD ["uvicorn", "app.app:app", "--host", "0.0.0.0", "--port", "8080", "--workers", "2", "--reload"]
