#!/bin/bash
# Script to download mempool-dumpster data for backtesting
# This provides transaction data even when relays don't have payload traces

set -e

cd "$(dirname "$0")"
source ~/.cargo/env

NETWORK="${1:-mainnet}"  # mainnet or sepolia
MEMPOOL_DIR="${HOME}/.rbuilder/mempool-data/${NETWORK}"

echo "Setting up mempool-dumpster data for $NETWORK"
echo "Data will be stored in: $MEMPOOL_DIR"
echo ""

# Create directory structure
mkdir -p "$MEMPOOL_DIR/transactions"
mkdir -p "$MEMPOOL_DIR/bundles"

# Download mempool-dumpster data
# Note: mempool-dumpster provides historical mempool transactions
# You can download specific dates or let rbuilder fetch them automatically

echo "Mempool-dumpster data directory created at: $MEMPOOL_DIR"
echo ""
echo "The backtest-fetch tool will automatically download mempool data from:"
echo "https://mempool-dumpster.flashbots.net/"
echo ""
echo "To manually download specific dates, you can use:"
echo "  wget -P $MEMPOOL_DIR/transactions/ https://mempool-dumpster.flashbots.net/mainnet/transactions/YYYY-MM-DD_transactions.parquet"
echo ""
echo "Or let rbuilder fetch it automatically when running backtests."

