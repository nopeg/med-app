#!/bin/bash

# Wait for the MySQL database to be ready
until mysqladmin ping -h mysql --silent; do
    echo "Waiting for MySQL..."
    sleep 2
done

# Now run the FastAPI application
exec python3 med_app.py