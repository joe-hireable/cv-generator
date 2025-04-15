FROM python:3.9-slim

# Install LibreOffice
RUN apt-get update && apt-get install -y \
    libreoffice \
    libreoffice-writer \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy function code
COPY main.py .

# Set environment variables
ENV FUNCTION_TARGET=docx_to_pdf

# Run the function
CMD ["functions-framework", "--target=docx_to_pdf", "--port=8080"] 