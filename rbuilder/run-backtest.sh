#!/bin/bash
# Quick script to run backtests on Sepolia/Mainnet historical blocks
# Usage: ./run-backtest.sh <command> [args...]
#
# Commands:
#   fetch <from_block> <to_block>  - Fetch historical data for block range
#   test-greedy <block>            - Test greedy algorithm on a single block
#   test-range <from> <to>        - Test greedy algorithm on a range and store results
#   compare <from> <to>           - Compare custom algorithm vs stored greedy results

set -e

cd "$(dirname "$0")"
source ~/.cargo/env

CONFIG_DEFAULT="config-sepolia-backtest.toml"
CONFIG="${RBUILDER_CONFIG_PATH:-$CONFIG_DEFAULT}"

# Load .env file if it exists
if [ -f .env ]; then
    echo "Loading environment variables from .env file..."
    # Temporarily disable exit on error for .env loading (in case of blank lines)
    set +e
    set -a  # automatically export all variables
    # Source .env, ignoring errors from blank lines
    source .env 2>/dev/null || true
    set +a  # stop automatically exporting
    set -e  # re-enable exit on error
    
    # Resolve env: variables in config file by creating a temp config with resolved values
    if [ -f "$CONFIG" ]; then
        TEMP_CONFIG=$(mktemp)
        if python3 - "$CONFIG" <<'PY' > "$TEMP_CONFIG"; then
import os
import sys
import re
path = sys.argv[1]
text = open(path).read()
pattern = re.compile(r'env:([A-Z0-9_]+)')
def repl(match):
    var = match.group(1)
    if var not in os.environ:
        print(f"Warning: environment variable {var} not set, replacing with empty string", file=sys.stderr)
        return ""
    return os.environ[var]
print(pattern.sub(repl, text), end='')
PY
            CONFIG="$TEMP_CONFIG"
            trap 'rm -f "$TEMP_CONFIG"' EXIT
        else
            echo "Failed to resolve env vars in $CONFIG"
            rm -f "$TEMP_CONFIG"
            exit 1
        fi
    fi
fi

if [ ! -f "$CONFIG" ]; then
    echo "Error: $CONFIG not found!"
    exit 1
fi

case "$1" in
    fetch)
        if [ -z "$2" ] || [ -z "$3" ]; then
            echo "Usage: $0 fetch <from_block> <to_block>"
            echo "   Or: $0 fetch recent [hours]  # Fetch recent blocks (default: 24 hours)"
            exit 1
        fi
        if [ "$2" = "recent" ]; then
            HOURS="${3:-24}"
            echo "Fetching recent blocks (last $HOURS hours)..."
            ./fetch-recent-blocks.sh "$HOURS"
        else
            echo "Fetching historical data for blocks $2 to $3..."
            cargo run --release --bin backtest-fetch -- \
                --config "$CONFIG" \
                fetch --ignore-errors --range "$2" "$3"
        fi
        ;;
    test-greedy)
        if [ -z "$2" ]; then
            echo "Usage: $0 test-greedy <block_number>"
            exit 1
        fi
        echo "Testing greedy algorithm on block $2..."
        cargo run --release --bin backtest-build-block -- \
            --config "$CONFIG" \
            --builders greedy-mp-ordering \
            "$2"
        ;;
    test-range)
        if [ -z "$2" ] || [ -z "$3" ]; then
            echo "Usage: $0 test-range <from_block> <to_block>"
            exit 1
        fi
        echo "Testing greedy algorithm on blocks $2 to $3 (storing results)..."
        cargo run --release --bin backtest-build-range -- \
            --config "$CONFIG" \
            --store-backtest \
            --range \
            "$2" "$3"
        ;;
    compare)
        if [ -z "$2" ] || [ -z "$3" ]; then
            echo "Usage: $0 compare <from_block> <to_block>"
            echo "Note: Make sure to add your custom algorithm to backtest_builders in $CONFIG"
            exit 1
        fi
        echo "Comparing custom algorithm vs stored greedy results for blocks $2 to $3..."
        cargo run --release --bin backtest-build-range -- \
            --config "$CONFIG" \
            --compare-backtest \
            --range \
            "$2" "$3"
        ;;
    test-no-sim)
        if [ -z "$2" ]; then
            echo "Usage: $0 test-no-sim <block_number> [builder1] [builder2] ..."
            echo "Example: $0 test-no-sim 18920193 greedy-mp-ordering custom-algo"
            exit 1
        fi
        BLOCK="$2"
        shift 2
        BUILDERS="${@:-greedy-mp-ordering}"  # Default to greedy if none specified
        echo "Testing algorithms on block $BLOCK (no simulation, using historical data)..."
        cargo run --release -p rbuilder --bin backtest-build-block-no-sim -- \
            --config "$CONFIG" \
            $(for b in $BUILDERS; do echo "--builders $b"; done) \
            "$BLOCK"
        ;;
    *)
        echo "Usage: $0 <command> [args...]"
        echo ""
        echo "Commands:"
        echo "  fetch <from> <to>      - Fetch historical data for block range"
        echo "  test-greedy <block>   - Test greedy algorithm on a single block"
        echo "  test-range <from> <to> - Test greedy algorithm on a range and store results"
        echo "  compare <from> <to>   - Compare custom algorithm vs stored greedy results"
        echo "  test-no-sim <block> [builders...] - Test algorithms WITHOUT Reth (uses historical data)"
        exit 1
        ;;
esac

