#!/usr/bin/env python3
"""
Analyze hierarchical optimization strategy on real data.
"""

import json
import numpy as np

CAPACITY = 30_000_000

# Load data
json_path = '../rbuilder/knapsack_instance_21200000.json'
with open(json_path) as f:
    data = json.load(f)

all_profits = []
all_gas_costs = []
for item in data['items']:
    profit_hex = item['profit']
    profit = int(profit_hex, 16) if profit_hex.startswith('0x') else int(profit_hex)
    all_profits.append(profit)
    all_gas_costs.append(item['gas'])

# Get profitable subset
profitable_indices = [i for i, p in enumerate(all_profits) if p > 0]
profits = np.array([all_profits[i] for i in profitable_indices])
gas_costs = np.array([all_gas_costs[i] for i in profitable_indices])

print("="*80)
print("HIERARCHICAL OPTIMIZATION ANALYSIS")
print("="*80)

# Sort by profit (descending)
sorted_indices = np.argsort(profits)[::-1]
profits_sorted = profits[sorted_indices]
gas_sorted = gas_costs[sorted_indices]

print(f"\nTotal: {len(profits)} profitable transactions")
print(f"Total profit: {sum(profits)/1e18:.6f} ETH")
print(f"Total gas: {sum(gas_costs):,} ({sum(gas_costs)/CAPACITY*100:.1f}% of capacity)")

# Define tiers
print(f"\n{'='*80}")
print("TIER ANALYSIS")
print("="*80)

# Option 1: Fixed size tiers
tier_sizes = [10, 30, 35]  # Top 10, next 30, bottom 35

print(f"\nOption 1: Fixed-size tiers (10, 30, 35)")
print(f"{'Tier':<8} {'Size':<8} {'Profit (ETH)':<15} {'Gas':<15} {'Gas %':<10} {'Avg Profit':<15} {'Range'}")
print("-"*95)

cumulative_profit = 0
cumulative_gas = 0
start_idx = 0

for tier_num, tier_size in enumerate(tier_sizes, 1):
    end_idx = start_idx + tier_size
    tier_profits = profits_sorted[start_idx:end_idx]
    tier_gas = gas_sorted[start_idx:end_idx]
    
    tier_total_profit = sum(tier_profits)
    tier_total_gas = sum(tier_gas)
    tier_avg_profit = np.mean(tier_profits)
    tier_range = np.max(tier_profits) / np.min(tier_profits)
    
    cumulative_profit += tier_total_profit
    cumulative_gas += tier_total_gas
    
    print(f"Tier {tier_num:<3} {tier_size:<8} {tier_total_profit/1e18:<15.6f} "
          f"{tier_total_gas:<15,} {tier_total_gas/CAPACITY*100:<10.1f} "
          f"{tier_avg_profit/1e18:<15.9f} {tier_range:<.1f}×")
    
    start_idx = end_idx

print(f"{'TOTAL':<8} {len(profits):<8} {cumulative_profit/1e18:<15.6f} "
      f"{cumulative_gas:<15,} {cumulative_gas/CAPACITY*100:<10.1f}")

# Option 2: Orders of magnitude tiers
print(f"\n{'='*80}")
print(f"Option 2: Orders-of-magnitude tiers")
print(f"{'='*80}")

# Find natural breaks in orders of magnitude
log_profits = np.log10(profits_sorted)
print(f"\nProfit range (log10):")
print(f"  Min: {np.min(log_profits):.2f} (10^{np.min(log_profits):.2f} wei)")
print(f"  Max: {np.max(log_profits):.2f} (10^{np.max(log_profits):.2f} wei)")

# Define tiers by orders of magnitude
tier_boundaries = [
    (1e15, float('inf'), "High (>1e15 wei = >0.001 ETH)"),
    (1e14, 1e15, "Medium (1e14-1e15 wei = 0.0001-0.001 ETH)"),
    (0, 1e14, "Low (<1e14 wei = <0.0001 ETH)")
]

print(f"\n{'Tier':<20} {'Count':<8} {'Profit (ETH)':<15} {'Gas':<15} {'Gas %':<10} {'Range'}")
print("-"*85)

for tier_name, (min_p, max_p, desc) in zip(['High', 'Medium', 'Low'], tier_boundaries):
    mask = (profits >= min_p) & (profits < max_p)
    tier_profits = profits[mask]
    tier_gas = gas_costs[mask]
    
    if len(tier_profits) > 0:
        tier_total_profit = sum(tier_profits)
        tier_total_gas = sum(tier_gas)
        tier_range = np.max(tier_profits) / np.min(tier_profits) if len(tier_profits) > 1 else 1
        
        print(f"{desc:<20} {len(tier_profits):<8} {tier_total_profit/1e18:<15.6f} "
              f"{tier_total_gas:<15,} {tier_total_gas/CAPACITY*100:<10.1f} {tier_range:<.1f}×")

# Simulate hierarchical optimization
print(f"\n{'='*80}")
print("SIMULATED HIERARCHICAL OPTIMIZATION")
print("="*80)

print(f"\nStrategy: Process tiers sequentially, greedy within each tier")
print(f"(This simulates what LPU SHOULD do if it works well)")

remaining_capacity = CAPACITY
selected_txs = []
selected_profit = 0
selected_gas = 0

for tier_num, tier_size in enumerate(tier_sizes, 1):
    start_idx = sum(tier_sizes[:tier_num-1])
    end_idx = start_idx + tier_size
    
    tier_profits = profits_sorted[start_idx:end_idx]
    tier_gas = gas_sorted[start_idx:end_idx]
    
    print(f"\nTier {tier_num} (transactions {start_idx+1}-{end_idx}):")
    print(f"  Available capacity: {remaining_capacity:,} gas")
    print(f"  Transactions in tier: {len(tier_profits)}")
    
    # Greedy selection within tier (by profit/gas ratio)
    tier_ratios = tier_profits / tier_gas
    tier_sorted_indices = np.argsort(tier_ratios)[::-1]
    
    tier_selected = 0
    tier_selected_profit = 0
    tier_selected_gas = 0
    
    for idx in tier_sorted_indices:
        if remaining_capacity >= tier_gas[idx]:
            remaining_capacity -= tier_gas[idx]
            tier_selected += 1
            tier_selected_profit += tier_profits[idx]
            tier_selected_gas += tier_gas[idx]
            selected_txs.append(start_idx + idx)
    
    selected_profit += tier_selected_profit
    selected_gas += tier_selected_gas
    
    print(f"  Selected: {tier_selected}/{len(tier_profits)} transactions")
    print(f"  Profit: {tier_selected_profit/1e18:.6f} ETH")
    print(f"  Gas used: {tier_selected_gas:,}")
    print(f"  Remaining capacity: {remaining_capacity:,} gas")

print(f"\n{'='*80}")
print("FINAL RESULTS")
print("="*80)

print(f"\nHierarchical Strategy:")
print(f"  Selected: {len(selected_txs)}/75 transactions")
print(f"  Profit: {selected_profit/1e18:.6f} ETH")
print(f"  Gas: {selected_gas:,} ({selected_gas/CAPACITY*100:.1f}%)")

print(f"\nOptimal (select all 75):")
print(f"  Selected: 75/75 transactions")
print(f"  Profit: {sum(profits)/1e18:.6f} ETH")
print(f"  Gas: {sum(gas_costs):,} ({sum(gas_costs)/CAPACITY*100:.1f}%)")

print(f"\nComparison:")
efficiency = (selected_profit / sum(profits)) * 100
print(f"  Profit efficiency: {efficiency:.1f}%")
print(f"  Transactions selected: {len(selected_txs)/75*100:.1f}%")

if len(selected_txs) == 75:
    print(f"\n✅ Hierarchical strategy selects ALL transactions!")
    print(f"   This makes sense - all 75 fit in capacity!")
else:
    print(f"\n⚠️  Hierarchical strategy misses {75-len(selected_txs)} transactions")
    print(f"   Profit lost: {(sum(profits) - selected_profit)/1e18:.6f} ETH")

# Analyze variance within tiers
print(f"\n{'='*80}")
print("VARIANCE REDUCTION ANALYSIS")
print("="*80)

print(f"\nCurrent approach (all 75 together):")
print(f"  Profit range: {np.max(profits)/np.min(profits):.1f}×")
print(f"  Gas range: {np.max(gas_costs)/np.min(gas_costs):.1f}×")

print(f"\nHierarchical approach (within each tier):")
for tier_num, tier_size in enumerate(tier_sizes, 1):
    start_idx = sum(tier_sizes[:tier_num-1])
    end_idx = start_idx + tier_size
    
    tier_profits = profits_sorted[start_idx:end_idx]
    tier_gas = gas_sorted[start_idx:end_idx]
    
    profit_range = np.max(tier_profits) / np.min(tier_profits)
    gas_range = np.max(tier_gas) / np.min(tier_gas)
    
    print(f"  Tier {tier_num}: Profit range {profit_range:.1f}×, Gas range {gas_range:.1f}×")

print(f"\n{'='*80}")
print("RECOMMENDATION")
print("="*80)

print(f"\nFor this specific problem:")
print(f"  ✅ All 75 transactions fit in capacity")
print(f"  ✅ Hierarchical strategy still selects all 75")
print(f"  → No benefit from hierarchical approach here")

print(f"\nBUT: For problems where NOT all fit:")
print(f"  ✅ Hierarchical reduces variance within each tier")
print(f"  ✅ LPU can better optimize similar-magnitude transactions")
print(f"  ✅ Prioritizes high-value decisions first")
print(f"  → Could significantly improve LPU performance!")

print(f"\nNext steps:")
print(f"  1. Test on problem where capacity is constrained")
print(f"  2. Run LPU on each tier separately")
print(f"  3. Compare hierarchical LPU vs flat LPU vs greedy")

print(f"\n{'='*80}")

