#!/usr/bin/env bash
# wait-for-it.sh

HOST=$1
PORT=$2

shift 2

echo "⏳ Waiting for $HOST:$PORT..."

while ! nc -z $HOST $PORT; do
  sleep 1
done

echo "✅ $HOST:$PORT is available. Launching app..."
exec "$@"
