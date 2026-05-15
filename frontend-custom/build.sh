#!/bin/bash
# =====================================================
# Script de build - Excalidraw Frontend Custom
# =====================================================

set -e

echo "🔨 Building Excalidraw custom frontend..."
echo ""
echo "ℹ️  Les URLs sont configurées dans le Dockerfile"
echo "   - GET:  https://exca-api.agnisolution.fr/api/v2/"
echo "   - POST: https://exca-api.agnisolution.fr/api/v2/post/"
echo ""

# Variables
IMAGE_NAME="excalidraw-opepartner"
IMAGE_TAG="latest"

# Build de l'image Docker (les URLs sont dans le Dockerfile)
docker build -t "${IMAGE_NAME}:${IMAGE_TAG}" .

echo ""
echo "✅ Build terminé : ${IMAGE_NAME}:${IMAGE_TAG}"
echo ""
echo "Pour tester localement :"
echo "  docker run -p 8080:80 ${IMAGE_NAME}:${IMAGE_TAG}"
echo ""
echo "Pour pusher sur Docker Hub (optionnel) :"
echo "  docker tag ${IMAGE_NAME}:${IMAGE_TAG} YOUR_DOCKERHUB_USERNAME/${IMAGE_NAME}:${IMAGE_TAG}"
echo "  docker push YOUR_DOCKERHUB_USERNAME/${IMAGE_NAME}:${IMAGE_TAG}"
