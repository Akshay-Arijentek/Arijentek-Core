#!/bin/bash

# Exit on error
set -e

# Configuration
IMAGE_NAME="arijentek/hrms"
TAG="v16-latest"
DOCKER_FILE_DIR="$(dirname "$0")/../docker"

echo "Building Docker image: $IMAGE_NAME:$TAG..."

# Build the image using the Dockerfile in the docker directory
# Set context to the app root directory (parent of scripts/)
APP_ROOT="$(dirname "$0")/.."
echo "Context: $APP_ROOT"

# Pass the relative path to Dockerfile
docker build -f "$DOCKER_FILE_DIR/Dockerfile" -t $IMAGE_NAME:$TAG "$APP_ROOT"

echo "Build complete."

# Tagging for push (user requested akshayarijentek/arijentek-core)
TARGET_IMAGE="akshayarijentek/arijentek-core:$TAG"
echo "Tagging as $TARGET_IMAGE..."
docker tag $IMAGE_NAME:$TAG $TARGET_IMAGE

echo "Pushing to registry..."
# docker push $TARGET_IMAGE
echo "Push command commented out for safety. Run 'docker push $TARGET_IMAGE' to push."
