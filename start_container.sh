#!/bin/bash

# Set the image name
IMAGE_NAME="advanced_discord_bot:latest"

# Get the current directory
CURRENT_DIR=$(pwd)

# Build the Docker image from the current directory
docker build -t $IMAGE_NAME .

# Run the Docker container, mounting the current directory
docker run -d \
  --name advanced_discord_bot_container \
  -v $CURRENT_DIR:/app \
  $IMAGE_NAME

echo "Container started successfully!"
