#!/bin/bash
# Script to automatically fetch recent blocks for backtesting
# Fetches blocks from the last N hours/days

set -e

cd "$(dirname "$0")"
source ~/.cargo/env

CONFIG="${RBUILDER_CONFIG_PATH:-config-mainnet-backtest.toml}"
HOURS_BACK="${1:-24}"  # Default: last 24 hours
BLOCKS_PER_HOUR=300    # ~12s per block = 300 blocks/hour

# Calculate block range
CURRENT_BLOCK=$(curl -s -X POST -H "Content-Type: application/json" \
    --data '{"jsonrpc":"2.0","method":"eth_blockNumber","params":[],"id":1}' \
    "$(grep -E "QUICK_NODE.*MAINNET.*HTTP|QUICK_NODE.*SPOLIA.*HTTP" .env | head -1 | cut -d'=' -f2- | tr -d ' ')" | \
    python3 -c "import sys, json; print(int(json.load(sys.stdin)['result'], 16))")

BLOCKS_TO_FETCH=$((HOURS_BACK * BLOCKS_PER_HOUR))
FROM_BLOCK=$((CURRENT_BLOCK - BLOCKS_TO_FETCH))
TO_BLOCK=$CURRENT_BLOCK

echo "Fetching blocks from $FROM_BLOCK to $TO_BLOCK (last $HOURS_BACK hours)"
echo "Using config: $CONFIG"
echo ""

export RBUILDER_CONFIG_PATH="$CONFIG"
./run-backtest.sh fetch "$FROM_BLOCK" "$TO_BLOCK"

