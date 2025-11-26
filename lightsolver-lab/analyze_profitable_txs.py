#!/usr/bin/env python3
"""
Analyze the 75 profitable transactions to understand:
1. Do they all fit in one block (30M gas)?
2. What's their total profit?
3. What's the distribution of profit/gas ratios?
"""

import json
import numpy as np

CAPACITY = 30_000_000

def load_knapsack(json_path):
    """Load and parse knapsack data."""
    with open(json_path) as f:
        data = json.load(f)
    
    items = data['items']
    profits = []
    gas_costs = []
    tx_ids = []
    
    for item in items:
        tx_ids.append(item['id'])
        profit_hex = item['profit']
        profit = int(profit_hex, 16) if profit_hex.startswith('0x') else int(profit_hex)
        profits.append(profit)
        gas_costs.append(item['gas'])
    
    return tx_ids, profits, gas_costs

# Load data
json_path = '../rbuilder/knapsack_instance_21200000.json'
tx_ids, profits, gas_costs = load_knapsack(json_path)

print("="*80)
print("ANALYSIS OF PROFITABLE TRANSACTIONS")
print("="*80)

# Find profitable transactions
profitable_indices = [i for i, p in enumerate(profits) if p > 0]
zero_profit_count = len(profits) - len(profitable_indices)

print(f"\nTotal transactions: {len(profits)}")
print(f"Profitable transactions: {len(profitable_indices)} ({len(profitable_indices)/len(profits)*100:.1f}%)")
print(f"Zero-profit transactions: {zero_profit_count} ({zero_profit_count/len(profits)*100:.1f}%)")

# Analyze profitable subset
profitable_profits = [profits[i] for i in profitable_indices]
profitable_gas = [gas_costs[i] for i in profitable_indices]
profitable_ids = [tx_ids[i] for i in profitable_indices]

total_profit = sum(profitable_profits)
total_gas = sum(profitable_gas)

print(f"\n{'='*80}")
print("PROFITABLE TRANSACTIONS ANALYSIS")
print("="*80)
print(f"Total profit available: {total_profit/1e18:.6f} ETH ({total_profit:,} wei)")
print(f"Total gas if all selected: {total_gas:,}")
print(f"Block capacity: {CAPACITY:,}")
print(f"Gas ratio: {total_gas/CAPACITY*100:.1f}%")

if total_gas <= CAPACITY:
    print(f"\n✅ ALL 75 PROFITABLE TXS FIT IN ONE BLOCK!")
    print(f"   Spare capacity: {CAPACITY - total_gas:,} gas ({(CAPACITY-total_gas)/CAPACITY*100:.1f}%)")
    print(f"\n   → This means there's NO optimization needed among profitable txs")
    print(f"   → Optimal solution: Select all 75 profitable transactions")
    print(f"   → Any algorithm that selects fewer is suboptimal")
else:
    print(f"\n⚠️  NOT ALL 75 FIT - Need to choose subset")
    print(f"   Overflow: {total_gas - CAPACITY:,} gas")
    print(f"   → Optimization IS needed among profitable txs")

# Distribution analysis
print(f"\n{'='*80}")
print("PROFIT DISTRIBUTION")
print("="*80)

profit_stats = {
    'min': min(profitable_profits),
    'max': max(profitable_profits),
    'mean': np.mean(profitable_profits),
    'median': np.median(profitable_profits),
    'std': np.std(profitable_profits),
}

print(f"Min profit:    {profit_stats['min']/1e18:.9f} ETH")
print(f"Max profit:    {profit_stats['max']/1e18:.9f} ETH")
print(f"Mean profit:   {profit_stats['mean']/1e18:.9f} ETH")
print(f"Median profit: {profit_stats['median']/1e18:.9f} ETH")
print(f"Std dev:       {profit_stats['std']/1e18:.9f} ETH")
print(f"Range:         {profit_stats['max']/profit_stats['min']:.1f}x")

# Gas distribution
gas_stats = {
    'min': min(profitable_gas),
    'max': max(profitable_gas),
    'mean': np.mean(profitable_gas),
    'median': np.median(profitable_gas),
}

print(f"\n{'='*80}")
print("GAS DISTRIBUTION")
print("="*80)
print(f"Min gas:    {gas_stats['min']:,}")
print(f"Max gas:    {gas_stats['max']:,}")
print(f"Mean gas:   {gas_stats['mean']:,.0f}")
print(f"Median gas: {gas_stats['median']:,.0f}")

# Profit/gas ratios
ratios = [p/g for p, g in zip(profitable_profits, profitable_gas)]
ratio_stats = {
    'min': min(ratios),
    'max': max(ratios),
    'mean': np.mean(ratios),
    'median': np.median(ratios),
}

print(f"\n{'='*80}")
print("PROFIT/GAS RATIO DISTRIBUTION")
print("="*80)
print(f"Min ratio:    {ratio_stats['min']:.2e} wei/gas")
print(f"Max ratio:    {ratio_stats['max']:.2e} wei/gas")
print(f"Mean ratio:   {ratio_stats['mean']:.2e} wei/gas")
print(f"Median ratio: {ratio_stats['median']:.2e} wei/gas")
print(f"Range:        {ratio_stats['max']/ratio_stats['min']:.1f}x")

# Top 10 most profitable
print(f"\n{'='*80}")
print("TOP 10 MOST PROFITABLE TRANSACTIONS")
print("="*80)
sorted_indices = sorted(profitable_indices, key=lambda i: profits[i], reverse=True)
for rank, idx in enumerate(sorted_indices[:10], 1):
    profit_eth = profits[idx] / 1e18
    gas = gas_costs[idx]
    ratio = profits[idx] / gas
    print(f"{rank:2d}. Profit: {profit_eth:.9f} ETH | Gas: {gas:,} | Ratio: {ratio:.2e}")

# What if we test on these 75?
print(f"\n{'='*80}")
print("IMPLICATIONS FOR LPU TESTING")
print("="*80)

if total_gas <= CAPACITY:
    print("Since all 75 fit in one block:")
    print("  1. Optimal solution is trivial: select all 75")
    print("  2. Testing LPU on these 75 won't show optimization capability")
    print("  3. Need to test on larger set that DOESN'T all fit")
    print()
    print("RECOMMENDATION:")
    print("  → Test on n=200 (includes 75 profitable + 125 zeros)")
    print("  → This requires choosing WHICH 75 to include")
    print("  → LPU must learn to ignore zeros and select profitables")
    print("  → Fair test of optimization capability")
else:
    print("Since not all 75 fit:")
    print("  1. Optimization IS needed among profitable txs")
    print("  2. Testing LPU on these 75 is meaningful")
    print("  3. This is a fair test of LPU's capability")

print(f"\n{'='*80}")
print("CONCLUSION")
print("="*80)
print(f"Test configurations to try:")
print(f"  1. n=75 (all profitable) - Check if LPU selects all")
print(f"  2. n=200 (75 profitable + 125 zeros) - Test discrimination")
print(f"  3. n=300 (if emulator supports) - Larger realistic test")
print("="*80)


