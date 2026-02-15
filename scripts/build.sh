#!/bin/bash

# Exit on error
set -e

# Configuration
IMAGE_NAME="arijentek/hrms"
# Use a timestamp-based tag to ensure Docker/Registry pulling always gets the latest
TIMESTAMP=$(date +%Y%m%d%H%M)
TAG="v16-$TIMESTAMP"
DOCKER_FILE_DIR="$(dirname "$0")/../docker"

echo "----------------------------------"
echo "Building Docker image: $IMAGE_NAME:$TAG"
echo "----------------------------------"

APP_ROOT="$(dirname "$0")/.."
docker build --no-cache -f "$DOCKER_FILE_DIR/Dockerfile" -t $IMAGE_NAME:$TAG "$APP_ROOT"

echo "----------------------------------"
echo "VERIFYING IMAGE CONTENT LOCALLY"
echo "----------------------------------"
# Verify that insights is truly gone
echo "Installed apps in the new image:"
docker run --rm $IMAGE_NAME:$TAG ls /home/frappe/frappe-bench/apps

echo "----------------------------------"
echo "Build complete."
echo "----------------------------------"

# Tagging for push
TARGET_IMAGE="akshayarijentek/arijentek-core:$TAG"
LATEST_IMAGE="akshayarijentek/arijentek-core:v16-latest"

echo "Tagging as $TARGET_IMAGE and $LATEST_IMAGE..."
docker tag $IMAGE_NAME:$TAG $TARGET_IMAGE
docker tag $IMAGE_NAME:$TAG $LATEST_IMAGE

echo "----------------------------------"
echo "READY TO PUSH"
echo "----------------------------------"
echo "Run these commands to finish:"
echo "docker push $TARGET_IMAGE"
echo "docker push $LATEST_IMAGE"
