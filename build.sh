#!/bin/sh
# Build the immich-gpt single-container image.
#
# Works on any Docker version — does NOT require buildx or BuildKit.
# The frontend is built using a temporary Node container, then the
# Python image is built with plain docker build.
#
# Usage:
#   ./build.sh                                   # tags as ghcr.io/titatom/immich-gpt:latest
#   ./build.sh immich-gpt:local                  # custom tag
#   IMMICH_GPT_IMAGE=immich-gpt:local docker compose up -d
set -e

DEFAULT_TAG="ghcr.io/titatom/immich-gpt:latest"
TAG="${1:-$DEFAULT_TAG}"
FRONTEND_BUILDER="immich-gpt-node-build:tmp"

echo "==> [1/3] Building React frontend (Node container)..."
docker build \
  --target frontend-builder \
  -f Dockerfile.unraid \
  -t "$FRONTEND_BUILDER" \
  .

echo "==> [2/3] Copying built assets out of the Node container..."
CID=$(docker create "$FRONTEND_BUILDER")
rm -rf ./backend/static
docker cp "$CID:/build/backend/static" ./backend/static
docker rm "$CID"
docker rmi "$FRONTEND_BUILDER" 2>/dev/null || true

echo "==> [3/3] Building Python/FastAPI image..."
docker build \
  -f Dockerfile.unraid.local \
  -t "$TAG" \
  .

echo ""
echo "Build complete. Image: $TAG"
echo ""
echo "Start with:"
if [ "$TAG" = "$DEFAULT_TAG" ]; then
  echo "  docker compose up -d"
else
  echo "  IMMICH_GPT_IMAGE=$TAG docker compose up -d"
fi
