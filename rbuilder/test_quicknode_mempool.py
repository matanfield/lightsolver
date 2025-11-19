#!/usr/bin/env python3
"""
Test script to connect to QuickNode WebSocket and stream live mempool transactions.
"""
import asyncio
import json
import os
import sys
import time
from datetime import datetime

try:
    from websockets import connect
    from websockets.exceptions import ConnectionClosed
except ImportError:
    print("❌ Error: websockets module not installed")
    print("Install it with: pip3 install websockets")
    sys.exit(1)

def wei_to_eth(wei_hex):
    """Convert wei (hex) to ETH"""
    try:
        wei = int(wei_hex, 16)
        return wei / 1e18
    except:
        return 0

def gwei_to_eth(gwei_hex):
    """Convert gwei (hex) to ETH"""
    try:
        gwei = int(gwei_hex, 16) / 1e9
        return gwei
    except:
        return 0

async def fetch_and_print_tx(ws, tx_hash, count, start_time, req_id, pending_requests):
    """Fetch transaction details and print them"""
    # Create a future to wait for the response
    future = asyncio.Future()
    pending_requests[req_id] = lambda resp: future.set_result(resp)
    
    try:
        # Request transaction details
        tx_request = {
            "jsonrpc": "2.0",
            "id": req_id,
            "method": "eth_getTransactionByHash",
            "params": [tx_hash]
        }
        await ws.send(json.dumps(tx_request))
        
        # Wait for response (with timeout)
        tx_data = await asyncio.wait_for(future, timeout=5.0)
        
        elapsed = time.time() - start_time
        rate = count / elapsed if elapsed > 0 else 0
        
        if "result" in tx_data and tx_data["result"]:
            tx = tx_data["result"]
            from_addr = tx.get("from", "N/A")
            to_addr = tx.get("to") or "Contract Creation"
            value_hex = tx.get("value", "0x0")
            gas_price_hex = tx.get("gasPrice", "0x0")
            gas_limit_hex = tx.get("gas", "0x0")
            
            value_eth = wei_to_eth(value_hex)
            gas_price_gwei = gwei_to_eth(gas_price_hex)
            gas_limit = int(gas_limit_hex, 16) if gas_limit_hex.startswith("0x") else 0
            
            timestamp = datetime.now().strftime("%H:%M:%S")
            
            print(f"[#{count:6}] {timestamp}")
            print(f"         Hash:    {tx_hash}")
            print(f"         From:    {from_addr}")
            print(f"         To:      {to_addr}")
            print(f"         Value:   {value_eth:.6f} ETH")
            print(f"         Gas:     {gas_price_gwei:.2f} Gwei (limit: {gas_limit:,})")
            print(f"         Rate:    {rate:.2f} tx/s")
            print("-" * 80, flush=True)
        else:
            # Only print failure if verbose or specific error
            # print(f"[#{count:6}] Hash: {tx_hash} (details not available)", flush=True)
            pass

    except asyncio.TimeoutError:
        # print(f"[#{count:6}] Hash: {tx_hash} (timeout fetching details)", flush=True)
        pass
    except Exception as e:
        print(f"⚠️  Error fetching tx {tx_hash}: {e}", flush=True)
    finally:
        if req_id in pending_requests:
            del pending_requests[req_id]

async def stream_mempool(ws_url):
    """Stream mempool transactions from QuickNode"""
    print("🔌 Connecting to QuickNode WebSocket...")
    print(f"📡 URL: {ws_url[:50]}...")
    print(flush=True)
    
    try:
        async with connect(ws_url) as ws:
            print("✅ Connected successfully!", flush=True)
            
            # Subscribe to pending transactions
            subscribe_msg = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "eth_subscribe",
                "params": ["newPendingTransactions"]
            }
            
            print("🔄 Subscribing to newPendingTransactions...", flush=True)
            await ws.send(json.dumps(subscribe_msg))
            
            # Get subscription confirmation
            response = await ws.recv()
            sub_response = json.loads(response)
            
            if "error" in sub_response:
                error_msg = sub_response['error'].get('message', 'Unknown error')
                print(f"❌ Subscription error: {error_msg}", flush=True)
                return
            
            subscription_id = sub_response.get("result")
            if not subscription_id:
                print("❌ Failed to get subscription ID", flush=True)
                return
                
            print(f"✅ Subscribed! Subscription ID: {subscription_id}")
            print()
            print("⏳ Waiting for pending transactions...")
            print("Press Ctrl+C to stop")
            print("=" * 80)
            print(flush=True)
            
            count = 0
            start_time = time.time()
            pending_requests = {}  # Track pending requests by ID
            request_id_counter = 100
            
            # Reader loop
            async for message in ws:
                try:
                    data = json.loads(message)
                    
                    # 1. Handle Responses
                    if "id" in data:
                        req_id = data["id"]
                        if req_id in pending_requests:
                            # Resolve the future for the waiting task
                            pending_requests[req_id](data)
                            continue
                    
                    # 2. Handle Subscription Notifications
                    if "method" in data and data["method"] == "eth_subscription":
                        params = data.get("params", {})
                        if params.get("subscription") == subscription_id:
                            tx_hash = params.get("result")
                            
                            if tx_hash:
                                count += 1
                                req_id = request_id_counter
                                request_id_counter += 1
                                
                                # Spawn a background task to fetch details
                                # This prevents blocking the reader loop
                                asyncio.create_task(
                                    fetch_and_print_tx(
                                        ws, 
                                        tx_hash, 
                                        count, 
                                        start_time, 
                                        req_id, 
                                        pending_requests
                                    )
                                )
                
                except json.JSONDecodeError:
                    pass
                except Exception as e:
                    print(f"⚠️  Error processing message: {e}", flush=True)
                    
    except ConnectionClosed:
        print("\n❌ Connection closed", flush=True)
    except KeyboardInterrupt:
        elapsed = time.time() - start_time
        rate = count / elapsed if elapsed > 0 else 0
        print(f"\n\n📊 Total transactions received: {count}")
        print(f"⏱️  Duration: {elapsed:.2f} seconds")
        print(f"📈 Average rate: {rate:.2f} tx/s", flush=True)
    except Exception as e:
        print(f"❌ Error: {e}", flush=True)
        sys.exit(1)

def main():
    # Get WebSocket URL from environment
    ws_url = os.getenv("QUICK_NODE_ETH_MAINNET_API_URL_WSS")
    
    if not ws_url:
        print("❌ Error: QUICK_NODE_ETH_MAINNET_API_URL_WSS environment variable not set")
        sys.exit(1)
    
    print("🚀 QuickNode Mempool Stream Test")
    print("=" * 80)
    print(flush=True)
    
    try:
        asyncio.run(stream_mempool(ws_url))
    except KeyboardInterrupt:
        print("\n👋 Stopped by user", flush=True)

if __name__ == "__main__":
    main()
