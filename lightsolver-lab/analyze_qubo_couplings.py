#!/usr/bin/env python3
"""
Analyze QUBO matrix couplings to understand magnitude ranges.
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

# Get profitable subset (n=75)
profitable_indices = [i for i, p in enumerate(all_profits) if p > 0]
profits = np.array([all_profits[i] for i in profitable_indices])
gas_costs = np.array([all_gas_costs[i] for i in profitable_indices])

print("="*80)
print("QUBO COUPLING ANALYSIS")
print("="*80)

# Build QUBO
max_profit = max(profits)
max_gas = max(gas_costs)
alpha = 2 * (max_profit / max_gas)

print(f"\nProblem size: n={len(profits)}")
print(f"Alpha (penalty): {alpha:.2e}")

n = len(profits)
Q = np.zeros((n, n))

# Diagonal terms: -profit_i + α(gas_i² - 2*capacity*gas_i)
for i in range(n):
    Q[i, i] = -profits[i] + alpha * (gas_costs[i]**2 - 2*CAPACITY*gas_costs[i])

# Off-diagonal terms: 2*α*gas_i*gas_j
for i in range(n):
    for j in range(i+1, n):
        Q[i, j] = 2 * alpha * gas_costs[i] * gas_costs[j]

print(f"\n{'='*80}")
print("QUBO MATRIX STATISTICS")
print("="*80)

# Diagonal terms
diag = np.diag(Q)
print(f"\nDIAGONAL TERMS (Q[i,i]):")
print(f"  Min:    {np.min(diag):.2e}")
print(f"  Max:    {np.max(diag):.2e}")
print(f"  Mean:   {np.mean(diag):.2e}")
print(f"  Median: {np.median(diag):.2e}")
print(f"  Range:  {np.max(diag) / np.min(diag):.2e}× (max/min)")

# Off-diagonal terms
upper_triangle = Q[np.triu_indices(n, k=1)]
print(f"\nOFF-DIAGONAL TERMS (Q[i,j] for i<j):")
print(f"  Min:    {np.min(upper_triangle):.2e}")
print(f"  Max:    {np.max(upper_triangle):.2e}")
print(f"  Mean:   {np.mean(upper_triangle):.2e}")
print(f"  Median: {np.median(upper_triangle):.2e}")
print(f"  Range:  {np.max(upper_triangle) / np.min(upper_triangle):.2e}× (max/min)")

# Overall
print(f"\nOVERALL QUBO:")
print(f"  Min:    {np.min(Q):.2e}")
print(f"  Max:    {np.max(Q):.2e}")
print(f"  Range:  {np.max(np.abs(Q)) / np.min(np.abs(Q[Q != 0])):.2e}× (max/min magnitude)")

print(f"\n{'='*80}")
print("WHERE DO THESE RANGES COME FROM?")
print("="*80)

# Analyze input data
print(f"\nINPUT DATA RANGES:")
print(f"\nProfits:")
print(f"  Min:    {np.min(profits):.2e} wei")
print(f"  Max:    {np.max(profits):.2e} wei")
print(f"  Range:  {np.max(profits) / np.min(profits):.1f}× (max/min)")
print(f"  This is the PROFIT variation in the knapsack!")

print(f"\nGas costs:")
print(f"  Min:    {np.min(gas_costs):,}")
print(f"  Max:    {np.max(gas_costs):,}")
print(f"  Range:  {np.max(gas_costs) / np.min(gas_costs):.1f}× (max/min)")

print(f"\nProfit/Gas ratios:")
ratios = profits / gas_costs
print(f"  Min:    {np.min(ratios):.2e} wei/gas")
print(f"  Max:    {np.max(ratios):.2e} wei/gas")
print(f"  Range:  {np.max(ratios) / np.min(ratios):.1f}× (max/min)")

print(f"\n{'='*80}")
print("TRACING THE COUPLING RANGES")
print("="*80)

print(f"\n1. DIAGONAL TERMS: Q[i,i] = -profit[i] + α(gas[i]² - 2*capacity*gas[i])")
print(f"\n   Components:")
print(f"   a) -profit[i]:")
print(f"      Range: {-np.max(profits):.2e} to {-np.min(profits):.2e}")
print(f"      Variation: {np.max(profits) / np.min(profits):.1f}× ← FROM PROFIT VARIATION!")

print(f"\n   b) α*gas[i]²:")
min_gas_sq = alpha * np.min(gas_costs)**2
max_gas_sq = alpha * np.max(gas_costs)**2
print(f"      Range: {min_gas_sq:.2e} to {max_gas_sq:.2e}")
print(f"      Variation: {max_gas_sq / min_gas_sq:.1f}× ← FROM GAS VARIATION!")

print(f"\n   c) -2*α*capacity*gas[i]:")
min_linear = -2 * alpha * CAPACITY * np.min(gas_costs)
max_linear = -2 * alpha * CAPACITY * np.max(gas_costs)
print(f"      Range: {min_linear:.2e} to {max_linear:.2e}")
print(f"      Variation: {abs(max_linear / min_linear):.1f}× ← FROM GAS VARIATION!")

print(f"\n   RESULT: Diagonal terms vary by {np.max(diag) / np.min(diag):.2e}×")
print(f"   This comes from BOTH profit and gas variations!")

print(f"\n2. OFF-DIAGONAL TERMS: Q[i,j] = 2*α*gas[i]*gas[j]")
print(f"\n   Components:")
print(f"   a) gas[i]*gas[j]:")
min_product = np.min(gas_costs) * np.min(gas_costs)
max_product = np.max(gas_costs) * np.max(gas_costs)
print(f"      Range: {min_product:,.0f} to {max_product:,.0f}")
print(f"      Variation: {max_product / min_product:.1f}× ← FROM GAS VARIATION SQUARED!")

print(f"\n   b) 2*α*gas[i]*gas[j]:")
min_coupling = 2 * alpha * min_product
max_coupling = 2 * alpha * max_product
print(f"      Range: {min_coupling:.2e} to {max_coupling:.2e}")
print(f"      Variation: {max_coupling / min_coupling:.1f}× ← SAME AS GAS² VARIATION!")

print(f"\n   RESULT: Off-diagonal terms vary by {np.max(upper_triangle) / np.min(upper_triangle):.2e}×")

print(f"\n{'='*80}")
print("ROOT CAUSE ANALYSIS")
print("="*80)

print(f"\nThe broad magnitude ranges in QUBO come from:")
print(f"\n1. PROFIT VARIATION (162,793×):")
print(f"   - Smallest profitable tx: {np.min(profits)/1e18:.9f} ETH")
print(f"   - Largest profitable tx:  {np.max(profits)/1e18:.9f} ETH")
print(f"   - This is INHERENT to the blockchain data!")
print(f"   - Some txs are 160,000× more valuable than others")

print(f"\n2. GAS COST VARIATION (222×):")
print(f"   - Smallest gas: {np.min(gas_costs):,}")
print(f"   - Largest gas:  {np.max(gas_costs):,}")
print(f"   - Simple transfers vs complex contracts")

print(f"\n3. QUADRATIC AMPLIFICATION:")
print(f"   - Off-diagonal: gas[i] × gas[j]")
print(f"   - Variation: 222² = 49,284× !")
print(f"   - The constraint term SQUARES the gas variation")

print(f"\n4. ALPHA MULTIPLIER:")
print(f"   - α = {alpha:.2e}")
print(f"   - Multiplies all constraint terms")
print(f"   - Makes large values even larger")

print(f"\n{'='*80}")
print("IMPACT ON EMULATOR")
print("="*80)

print(f"\nAfter normalization (Q_norm = Q / max|Q|):")
Q_max = np.max(np.abs(Q))
Q_norm = Q / Q_max
print(f"  All values scaled to [-1, 1]")
print(f"  But relative structure preserved")

print(f"\nIssue for LPU emulator:")
print(f"  1. Coupling matrix has huge range of interaction strengths")
print(f"  2. Some couplings are 10⁶× stronger than others")
print(f"  3. Laser dynamics may struggle with this asymmetry")
print(f"  4. Strong couplings dominate, weak ones ignored")

print(f"\nWhy this matters:")
print(f"  - High-profit txs should be strongly preferred")
print(f"  - But after normalization, this signal is diluted")
print(f"  - Gas constraints (quadratic) dominate profit (linear)")
print(f"  - LPU sees 'avoid gas' more than 'maximize profit'")

print(f"\n{'='*80}")
print("VISUALIZATION")
print("="*80)

# Find specific examples
min_profit_idx = np.argmin(profits)
max_profit_idx = np.argmax(profits)
min_gas_idx = np.argmin(gas_costs)
max_gas_idx = np.argmax(gas_costs)

print(f"\nEXAMPLE TRANSACTIONS:")
print(f"\nLowest profit tx (idx {min_profit_idx}):")
print(f"  Profit: {profits[min_profit_idx]/1e18:.9f} ETH")
print(f"  Gas:    {gas_costs[min_profit_idx]:,}")
print(f"  Q[{min_profit_idx},{min_profit_idx}] = {Q[min_profit_idx, min_profit_idx]:.2e}")

print(f"\nHighest profit tx (idx {max_profit_idx}):")
print(f"  Profit: {profits[max_profit_idx]/1e18:.9f} ETH")
print(f"  Gas:    {gas_costs[max_profit_idx]:,}")
print(f"  Q[{max_profit_idx},{max_profit_idx}] = {Q[max_profit_idx, max_profit_idx]:.2e}")

print(f"\nCoupling between them:")
if min_profit_idx < max_profit_idx:
    coupling = Q[min_profit_idx, max_profit_idx]
else:
    coupling = Q[max_profit_idx, min_profit_idx]
print(f"  Q[{min_profit_idx},{max_profit_idx}] = {coupling:.2e}")

print(f"\n{'='*80}")
print("CONCLUSION")
print("="*80)

print(f"\nThe QUBO couplings span {np.max(np.abs(Q)) / np.min(np.abs(Q[Q != 0])):.2e}× in magnitude.")
print(f"\nThis comes from:")
print(f"  1. Profit variation: 162,793× (blockchain data)")
print(f"  2. Gas variation: 222× (transaction complexity)")
print(f"  3. Quadratic terms: Square the gas variation → 49,284×")
print(f"  4. Alpha multiplier: {alpha:.2e}")
print(f"\nThis extreme asymmetry may be why the XY laser model struggles:")
print(f"  - Designed for more uniform coupling strengths")
print(f"  - May not handle 10⁶× range well")
print(f"  - Strong couplings dominate weak ones")
print(f"  - Profit signal gets lost in constraint noise")

print(f"\n{'='*80}")

