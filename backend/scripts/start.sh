#!/bin/bash

# Start the RQ worker in the background
echo "Starting RQ worker..."
rq worker validation --url $REDIS_URL &

# Start the FastAPI application
echo "Starting FastAPI on port $PORT..."
uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
