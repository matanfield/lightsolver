# Solution: Skip Execution for Knapsack Testing

## The Problem

You're right - for testing the **knapsack optimization algorithm** itself, you don't need to re-execute transactions. You just need:
1. List of orders/transactions
2. Their profits (from historical execution)
3. Gas costs (from historical execution)
4. Dependencies (can infer from nonces)

## Why Execution is Currently Required

The current `backtest-build-block` flow:
1. Loads orders from database ✅
2. **Re-simulates every transaction** (requires Reth state) ❌
3. Runs selection algorithm ✅

The simulation is needed to:
- Calculate gas usage
- Calculate profit (coinbase payments)
- Validate nonces and dependencies
- Check transaction validity

## The Solution: Use Pre-Computed Values

The codebase already has test helpers that create `SimulatedOrder` objects **without execution**:

```rust
// From rbuilder-primitives/src/lib.rs
SimValue::new_test(full_coinbase_profit, non_mempool_profit, gas_used)
SimValue::new_test_no_gas(coinbase_profit, mev_gas_price)

// From test_data_generator.rs
TestDataGenerator::create_sim_order(order, coinbase_profit, mev_gas_price)
```

## Implementation Options

### Option 1: Extract Historical Gas/Profit from Database

When blocks are fetched, we can extract:
- Gas used per transaction (from block receipts)
- Coinbase profit per transaction (from block execution)
- Store this in the database

Then create `SimulatedOrder` objects directly from this data.

### Option 2: Use Landed Block Data

The `restore_landed_orders` function already reconstructs orders from executed blocks:
- `ExecutedBlockTx` contains `coinbase_profit` and `success`
- We can use this to create `SimulatedOrder` objects

### Option 3: Create a New Binary

Create `backtest-build-block-no-sim` that:
1. Loads orders from database
2. Extracts gas/profit from historical block execution
3. Creates `SimulatedOrder` objects with `SimValue::new_test()`
4. Runs selection algorithm **without any state provider**

## Recommended Approach

**Option 3** is cleanest - create a new binary that:
- Doesn't require Reth at all
- Uses historical execution data
- Tests only the selection algorithm

## Next Steps

1. **Extract historical execution data** when fetching blocks:
   - Gas used per transaction
   - Coinbase profit per transaction
   - Store in database

2. **Create `backtest-build-block-no-sim` binary**:
   - Load orders + historical gas/profit
   - Create `SimulatedOrder` objects with pre-computed values
   - Run selection algorithm
   - Output selected transactions

3. **This gives you**:
   - ✅ No Reth required
   - ✅ Fast (no simulation)
   - ✅ Tests knapsack optimization algorithm
   - ✅ Uses real historical data

## Code Structure

```rust
// New function: create_simulated_orders_from_historical_data
fn create_simulated_orders_from_historical_data(
    orders: Vec<Order>,
    historical_gas_profit: HashMap<OrderId, (u64, U256)>, // gas, profit
) -> Vec<Arc<SimulatedOrder>> {
    orders.into_iter()
        .filter_map(|order| {
            let (gas, profit) = historical_gas_profit.get(&order.id())?;
            Some(Arc::new(SimulatedOrder {
                order,
                sim_value: SimValue::new_test(profit, profit, *gas),
                used_state_trace: None,
            }))
        })
        .collect()
}
```

Then run the selection algorithm on these pre-computed orders!

## Benefits

- **No Reth sync needed** (days + terabytes)
- **Fast iteration** on optimization algorithm
- **Real data** (historical gas/profit from actual execution)
- **Focus on what matters** (selection algorithm, not execution validation)

Would you like me to implement this solution?

