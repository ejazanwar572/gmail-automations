#!/usr/bin/env bash
# Convenience runner for HDFC Diners Club Black Metal Control Center
set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
echo "🚀 Starting HDFC Diners Club Black Metal Dashboard on port 8502..."
streamlit run "$DIR/hdfc_dcbm_app.py" --server.port 8502 --server.headless false
