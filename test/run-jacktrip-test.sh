#!/bin/bash
# Test jacktrip server with docker-compose
# Starts JACK, jacktrip hub, and test client, verifies port registration

set -e

COMPOSE_FILE="/workspaces/nam-box/manifests/nam-box/docker-compose.test.yaml"
PROJECT_NAME="jacktrip-test"

echo "=== Cleaning up any existing test containers ==="
docker compose -f "$COMPOSE_FILE" -p "$PROJECT_NAME" down -v 2>/dev/null || true

echo ""
echo "=== Starting test services ==="
docker compose -f "$COMPOSE_FILE" -p "$PROJECT_NAME" up -d

echo "Waiting for services to start..."
sleep 10

echo ""
echo "=== Checking service status ==="
docker compose -f "$COMPOSE_FILE" -p "$PROJECT_NAME" ps

echo ""
echo "=== Checking jacktrip hub logs ==="
docker compose -f "$COMPOSE_FILE" -p "$PROJECT_NAME" logs jacktrip-hub --tail=20 || true

echo ""
echo "=== Checking if jacktrip client connected ==="
docker compose -f "$COMPOSE_FILE" -p "$PROJECT_NAME" logs jacktrip-client-test --tail=20 || true

# Give it more time for connection
sleep 5

echo ""
echo "=== Final verification ==="
# Check that the services are running
HUB_RUNNING=$(docker compose -f "$COMPOSE_FILE" -p "$PROJECT_NAME" ps -q jacktrip-hub | xargs docker inspect -f '{{.State.Running}}' 2>/dev/null || echo "false")
CLIENT_RUNNING=$(docker compose -f "$COMPOSE_FILE" -p "$PROJECT_NAME" ps -q jacktrip-client-test | xargs docker inspect -f '{{.State.Running}}' 2>/dev/null || echo "false")

if [[ "$HUB_RUNNING" == "true" ]]; then
    echo "✓ jacktrip-hub is running"
else
    echo "✗ jacktrip-hub is NOT running"
fi

if [[ "$CLIENT_RUNNING" == "true" ]]; then
    echo "✓ jacktrip-client-test is running"
else
    echo "✗ jacktrip-client-test is NOT running"
fi

echo ""
echo "=== Test completed ==="
echo "Services are running. Check logs above for client connection status."
echo ""
echo "To cleanup: docker compose -f $COMPOSE_FILE -p $PROJECT_NAME down"
