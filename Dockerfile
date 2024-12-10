FROM python:3.12.1
WORKDIR /app

# Install the application dependencies
COPY ./requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

ENV MYSQL_ROOT_PASSWORD=root

# Copy in the source code
COPY ./frontend ./frontend
COPY ./config.py ./
COPY ./asyncMySQL.py ./
COPY ./med_app.py ./
COPY ./database/initial-up.sql ./docker-entrypoint-initdb.d/
COPY ./start.sh ./

EXPOSE 8000

RUN apt-get update && apt-get install -y default-mysql-client && rm -rf /var/lib/apt/lists/*

RUN chmod +x start.sh

# Command to run the startup script
CMD ["./start.sh"]