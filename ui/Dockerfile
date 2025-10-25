FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all files
COPY . .

# Expose the port Streamlit will run on
EXPOSE 8501

# Run Streamlit
CMD ["streamlit", "run", "app.py", "--server.port=80", "--server.address=0.0.0.0"]
