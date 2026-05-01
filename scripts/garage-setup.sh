#!/bin/bash
set -e

echo "Waiting for Garage RPC on garage:3901..."
while ! nc -z garage 3901; do sleep 1; done

echo "Waiting for Garage Admin API on garage:3903..."
while ! nc -z garage 3903; do sleep 1; done

GARAGE_CONF="-c /etc/garage.toml"

echo "Fetching Node ID..."
NODE_ID=$(garage $GARAGE_CONF status 2>&1 | grep -oE '[0-9a-f]{16,}' | head -n1)

if [ -z "$NODE_ID" ]; then
  echo "Error: Could not retrieve Node ID."
  garage $GARAGE_CONF status 2>&1
  exit 1
fi

echo "Node ID found: $NODE_ID"

# Only assign layout if node has no role yet
if garage $GARAGE_CONF status 2>&1 | grep -q "NO ROLE ASSIGNED"; then
  echo "Assigning layout..."
  garage $GARAGE_CONF layout assign "$NODE_ID" -z zone1 -c 1
  garage $GARAGE_CONF layout apply --version 1
else
  echo "Layout already assigned, skipping."
fi

echo "Setting up admin key..."
EXISTING_KEY_ID=$(garage $GARAGE_CONF key list 2>&1 | grep "admin" | awk '{print $1}')

if [ -n "$EXISTING_KEY_ID" ]; then
  echo "Key 'admin' already exists with ID: $EXISTING_KEY_ID"
  AWS_KEY_ID="$EXISTING_KEY_ID"
else
  echo "Creating new admin key..."
  KEY_OUTPUT=$(garage $GARAGE_CONF key new --name admin)
  AWS_KEY_ID=$(echo "$KEY_OUTPUT" | grep "Key ID:" | awk '{print $NF}')
  AWS_SECRET_KEY=$(echo "$KEY_OUTPUT" | grep "Secret key:" | awk '{print $NF}')
  
  echo "Updating .env file with new credentials..."
  grep -v '^AWS_ACCESS_KEY_ID=' /app/.env > /tmp/env.tmp
  grep -v '^AWS_SECRET_ACCESS_KEY=' /tmp/env.tmp > /tmp/env_final.tmp
  echo "AWS_ACCESS_KEY_ID=$AWS_KEY_ID" >> /tmp/env_final.tmp
  echo "AWS_SECRET_ACCESS_KEY=$AWS_SECRET_KEY" >> /tmp/env_final.tmp
  cat /tmp/env_final.tmp > /app/.env
  rm -f /tmp/env.tmp /tmp/env_final.tmp
  
  echo "Key ID: $AWS_KEY_ID"
  echo "Secret Key: $AWS_SECRET_KEY"
fi

echo "Ensuring mlflow bucket exists..."
garage $GARAGE_CONF bucket create mlflow 2>&1 || true

echo "Granting bucket access..."
garage $GARAGE_CONF bucket allow --read --write --owner \
  --key "$AWS_KEY_ID" mlflow

echo "Garage initialization complete."