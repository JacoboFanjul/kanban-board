#!/usr/bin/env bash
set -e

mkdir -p data
docker-compose up --build -d
echo "Server started at http://localhost:8000"
