#!/bin/bash
cd "$(dirname "$0")"
source .venv/bin/activate
while true; do
  python client.py
  sleep 1
done
