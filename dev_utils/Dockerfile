FROM python:3.10-slim

WORKDIR /sawe

# Install git
RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

# Copy project files
COPY configuration /sawe/configuration
COPY commons /sawe/commons
COPY engine /sawe/engine
COPY poller.py /sawe/poller.py
COPY web.py /sawe/web.py
COPY requirements.txt /sawe/requirements.txt
COPY init.sh /sawe/init.sh

#mock server
COPY mock_md_server.py /sawe/mock_md_server.py

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Make init script executable
RUN chmod +x /sawe/init.sh

EXPOSE 8080

CMD ["sh", "/sawe/init.sh"]
