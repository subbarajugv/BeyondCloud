#!/bin/bash

# Development script for llama.cpp webui
# 
# This script starts the webui development server (Vite).
# Note: You need to start llama-server separately.
#
# Usage:
#   bash scripts/dev.sh
#   npm run dev

# Cleanup function
cleanup() {
    echo "🧹 Cleaning up..."
    exit
}

# Set up signal handlers
trap cleanup SIGINT SIGTERM

echo "🚀 Starting development server..."
echo "📝 Note: Make sure to start llama-server separately if needed"

# Start Vite dev server
vite dev --host 0.0.0.0
