#!/bin/bash
# Build itasca-mcp:dev and immediately reclaim space from layers orphaned by
# the rebuild. Without this, every iteration on the Dockerfile leaves the
# previous engine layer (~12 GB extracted) hanging around as a dangling
# image, eventually filling Docker's VM disk.
#
# Usage:  ./docker/build.sh              # full build + cleanup
#         ./docker/build.sh --no-prune   # skip the cleanup step
#
# Run from the repo root.

set -e

PLATFORM=linux/amd64
TAG=itasca-mcp:dev
DEB_DIR="${ITASCA_DEB_DIR:-$HOME/Downloads}"
DEB_FILE="$DEB_DIR/itascasoftware.latest.deb"

if [ ! -f "$DEB_FILE" ]; then
    echo "ERROR: Itasca .deb not found at $DEB_FILE" >&2
    echo "Download it once with:" >&2
    echo "  curl -C - -L -o \"$DEB_FILE\" https://itasca-software.s3.amazonaws.com/itasca-software/9.subscription/itascasoftware.latest.deb" >&2
    exit 1
fi

echo "[build.sh] Disk before:"
df -h /System/Volumes/Data 2>/dev/null | tail -1 || df -h / | tail -1

docker build \
    --progress=plain \
    --platform="$PLATFORM" \
    --build-context "itasca-deb=$DEB_DIR" \
    -t "$TAG" \
    -f docker/Dockerfile \
    .

if [ "${1:-}" != "--no-prune" ]; then
    echo ""
    echo "[build.sh] Pruning dangling images orphaned by this build..."
    docker image prune -f
fi

echo ""
echo "[build.sh] Disk after:"
df -h /System/Volumes/Data 2>/dev/null | tail -1 || df -h / | tail -1

echo ""
echo "[build.sh] Done. Run with:"
echo "  docker run --rm -it --platform=$PLATFORM -p 9001:9001 -p 6080:6080 $TAG"
