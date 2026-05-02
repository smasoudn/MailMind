# Use a lightweight python image
FROM python:3.11-slim

# Set the working directory
WORKDIR /app

# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Cloud Run injects the PORT environment variable. We default it to 8080.
ENV PORT=8080

# Expose the port
EXPOSE $PORT

# Command to run the application using the PORT env var
CMD streamlit run app.py --server.port $PORT --server.address 0.0.0.0
