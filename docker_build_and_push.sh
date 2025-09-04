#!/bin/bash

# Docker Buildx multi-architecture build and push script
set -e

echo "Starting multi-architecture Docker build..."

# Environment variables
DOCKER_REPO="raelukang/mp3-extractor"
TAG="latest"
PLATFORMS="linux/amd64,linux/arm64"
BUILDER="arm-amd64-builder"

# 1. Buildx builder creation (if it already exists, use it)
echo "🔧 Setting up buildx builder..."
if ! docker buildx ls | grep -q $BUILDER; then
    docker buildx create --name $BUILDER --driver docker-container --bootstrap
fi

docker buildx use $BUILDER

# 2. Builder status check
echo "Builder info:"
docker buildx inspect --bootstrap

# 3. Multi-architecture build and push
echo "Building for platforms: $PLATFORMS"
docker buildx build \
    --platform $PLATFORMS \
    --tag $DOCKER_REPO:$TAG \
    --tag $DOCKER_REPO:$(date +%Y%m%d) \
    --push \
    --progress=plain \
    .

echo "Multi-architecture build and push completed!"
echo "Image: $DOCKER_REPO:$TAG"
echo "Platforms: $PLATFORMS"

# 4. Build result check
echo "Verifying pushed image..."
docker buildx imagetools inspect $DOCKER_REPO:$TAG