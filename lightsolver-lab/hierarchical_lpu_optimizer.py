#!/usr/bin/env python3
"""
Hierarchical Multi-Tier LPU Optimizer

Automatically separates transactions into tiers by orders of magnitude,
then optimizes each tier sequentially with LPU.
"""

import json
import numpy as np
import time
from laser_mind_client import LaserMind
from lightsolver_lib.lightsolver_lib import probmat_qubo_to_ising, coupling_matrix_xy, XYModelParams

CAPACITY = 30_000_000
TOKEN_FILE = 'laser-mind-client/examples/lightsolver-token.txt'

def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)

def load_knapsack(json_path):
    """Load knapsack data."""
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

def create_tiers_by_magnitude(profits, gas_costs, tx_ids):
    """
    Automatically create tiers by orders of magnitude.
    Returns list of tiers, each with indices, profits, gas_costs.
    """
    # Get profitable transactions only
    profitable_mask = np.array(profits) > 0
    profitable_indices = np.where(profitable_mask)[0]
    
    if len(profitable_indices) == 0:
        return []
    
    profitable_profits = np.array([profits[i] for i in profitable_indices])
    profitable_gas = np.array([gas_costs[i] for i in profitable_indices])
    
    # Calculate log10 of profits to find natural tiers
    log_profits = np.log10(profitable_profits)
    min_log = np.floor(np.min(log_profits))
    max_log = np.ceil(np.max(log_profits))
    
    log(f"Profit range: 10^{min_log:.0f} to 10^{max_log:.0f} wei")
    log(f"Creating tiers by orders of magnitude...")
    
    # Create tiers (from high to low)
    tiers = []
    for tier_log in range(int(max_log), int(min_log) - 1, -1):
        # Transactions in this order of magnitude
        lower_bound = 10 ** tier_log
        upper_bound = 10 ** (tier_log + 1)
        
        mask = (profitable_profits >= lower_bound) & (profitable_profits < upper_bound)
        tier_indices = profitable_indices[mask]
        
        if len(tier_indices) > 0:
            tier_profits = [profits[i] for i in tier_indices]
            tier_gas = [gas_costs[i] for i in tier_indices]
            tier_ids = [tx_ids[i] for i in tier_indices]
            
            tiers.append({
                'name': f"10^{tier_log} - 10^{tier_log+1} wei",
                'log_range': (tier_log, tier_log + 1),
                'indices': tier_indices,
                'profits': tier_profits,
                'gas_costs': tier_gas,
                'tx_ids': tier_ids,
                'total_profit': sum(tier_profits),
                'total_gas': sum(tier_gas),
            })
    
    return tiers

def optimize_tier_with_lpu(profits, gas_costs, capacity, alpha_divisor=10000):
    """
    Optimize a single tier using LPU.
    Returns binary solution vector.
    """
    n = len(profits)
    
    if n == 0:
        return []
    
    # Build QUBO
    max_profit = max(profits)
    max_gas = max(gas_costs)
    alpha = 2 * (max_profit / max_gas) / alpha_divisor
    
    Q = np.zeros((n, n))
    for i in range(n):
        Q[i, i] = -profits[i] + alpha * (gas_costs[i]**2 - 2*capacity*gas_costs[i])
    for i in range(n):
        for j in range(i+1, n):
            Q[i, j] = 2 * alpha * gas_costs[i] * gas_costs[j]
    
    # Normalize
    Q_max = np.max(np.abs(Q))
    if Q_max == 0 or np.isnan(Q_max):
        # Fallback to greedy
        return greedy_select(profits, gas_costs, capacity)
    
    Q_norm = Q / Q_max
    
    # Convert to Ising
    I, _ = probmat_qubo_to_ising(Q_norm)
    
    # Coupling matrix
    coupling_matrix = coupling_matrix_xy(I, XYModelParams())
    
    # Validate
    row_sums = np.abs(coupling_matrix).sum(axis=0)
    if not (row_sums < 1).all():
        # Fallback to greedy
        return greedy_select(profits, gas_costs, capacity)
    
    # Solve with LPU
    try:
        lsClient = LaserMind(pathToRefreshTokenFile=TOKEN_FILE, logToConsole=False)
        
        res = lsClient.solve_coupling_matrix_sim_lpu(
            matrix_data=coupling_matrix.astype(np.complex64),
            num_runs=5,
            num_iterations=500,
            rounds_per_record=1
        )
        
        # Extract solution
        record_states = res['data']['result']['record_states']
        num_runs = record_states.shape[1]
        
        best_solution = None
        best_energy = float('inf')
        
        for run_idx in range(num_runs):
            final_state = record_states[-1, run_idx, :]
            phases = np.angle(final_state)
            ising_state = np.where(phases >= 0, 1, -1)
            energy = np.dot(ising_state, np.dot(I, ising_state))
            
            if energy < best_energy:
                best_energy = energy
                best_solution = ((ising_state + 1) // 2).astype(int)
        
        return best_solution
        
    except Exception as e:
        log(f"  LPU failed: {str(e)[:50]}, falling back to greedy")
        return greedy_select(profits, gas_costs, capacity)

def greedy_select(profits, gas_costs, capacity):
    """Greedy selection by profit/gas ratio."""
    n = len(profits)
    ratios = [profits[i] / gas_costs[i] if gas_costs[i] > 0 else 0 for i in range(n)]
    sorted_indices = sorted(range(n), key=lambda i: ratios[i], reverse=True)
    
    solution = np.zeros(n, dtype=int)
    total_gas = 0
    
    for idx in sorted_indices:
        if total_gas + gas_costs[idx] <= capacity:
            solution[idx] = 1
            total_gas += gas_costs[idx]
    
    return solution

def hierarchical_optimize(tiers, capacity):
    """
    Optimize all tiers hierarchically.
    Returns global solution and metrics.
    """
    global_solution = {}  # Maps original index to selection (0 or 1)
    remaining_capacity = capacity
    
    total_selected = 0
    total_profit = 0
    total_gas = 0
    
    for tier_num, tier in enumerate(tiers, 1):
        log(f"\n{'='*80}")
        log(f"TIER {tier_num}: {tier['name']}")
        log(f"{'='*80}")
        log(f"  Transactions: {len(tier['indices'])}")
        log(f"  Total profit: {tier['total_profit']/1e18:.6f} ETH")
        log(f"  Total gas: {tier['total_gas']:,}")
        log(f"  Available capacity: {remaining_capacity:,}")
        
        if remaining_capacity <= 0:
            log(f"  ⚠️  No capacity remaining, skipping tier")
            continue
        
        # Calculate variance within tier
        if len(tier['profits']) > 1:
            profit_range = max(tier['profits']) / min(tier['profits'])
            gas_range = max(tier['gas_costs']) / min(tier['gas_costs'])
            log(f"  Variance: Profit {profit_range:.1f}×, Gas {gas_range:.1f}×")
        
        # Optimize this tier
        log(f"  Running LPU optimization...")
        t0 = time.time()
        
        tier_solution = optimize_tier_with_lpu(
            tier['profits'],
            tier['gas_costs'],
            remaining_capacity
        )
        
        elapsed = time.time() - t0
        
        # Evaluate tier results
        tier_selected_indices = [i for i, x in enumerate(tier_solution) if x == 1]
        tier_selected_count = len(tier_selected_indices)
        tier_selected_profit = sum(tier['profits'][i] for i in tier_selected_indices)
        tier_selected_gas = sum(tier['gas_costs'][i] for i in tier_selected_indices)
        
        log(f"  ✓ Completed in {elapsed:.1f}s")
        log(f"  Selected: {tier_selected_count}/{len(tier['indices'])} transactions")
        log(f"  Profit: {tier_selected_profit/1e18:.6f} ETH")
        log(f"  Gas used: {tier_selected_gas:,}")
        
        # Update global solution
        for i, orig_idx in enumerate(tier['indices']):
            global_solution[orig_idx] = tier_solution[i]
        
        # Update totals
        total_selected += tier_selected_count
        total_profit += tier_selected_profit
        total_gas += tier_selected_gas
        remaining_capacity -= tier_selected_gas
        
        log(f"  Remaining capacity: {remaining_capacity:,}")
    
    return global_solution, {
        'total_selected': total_selected,
        'total_profit': total_profit,
        'total_gas': total_gas,
        'gas_utilization': total_gas / capacity,
    }

# Main execution
log("="*80)
log("HIERARCHICAL MULTI-TIER LPU OPTIMIZER")
log("="*80)

# Load data
json_path = '../rbuilder/knapsack_instance_21200000.json'
log(f"\nLoading: {json_path}")
tx_ids, profits, gas_costs = load_knapsack(json_path)

log(f"Total transactions: {len(profits)}")
profitable_count = sum(1 for p in profits if p > 0)
log(f"Profitable: {profitable_count}")

# Create tiers
log(f"\n{'='*80}")
log("CREATING TIERS BY ORDERS OF MAGNITUDE")
log(f"{'='*80}")

tiers = create_tiers_by_magnitude(profits, gas_costs, tx_ids)

log(f"\nCreated {len(tiers)} tiers:")
for i, tier in enumerate(tiers, 1):
    log(f"  Tier {i}: {tier['name']}")
    log(f"    Count: {len(tier['indices'])}")
    log(f"    Profit: {tier['total_profit']/1e18:.6f} ETH ({tier['total_profit']/sum(tier['total_profit'] for tier in tiers)*100:.1f}%)")
    log(f"    Gas: {tier['total_gas']:,} ({tier['total_gas']/CAPACITY*100:.1f}%)")

# Run hierarchical optimization
log(f"\n{'='*80}")
log("RUNNING HIERARCHICAL OPTIMIZATION")
log(f"{'='*80}")

t_start = time.time()
solution, metrics = hierarchical_optimize(tiers, CAPACITY)
t_total = time.time() - t_start

# Final results
log(f"\n{'='*80}")
log("FINAL RESULTS")
log(f"{'='*80}")

log(f"\nHierarchical LPU:")
log(f"  Selected: {metrics['total_selected']}/{profitable_count} transactions")
log(f"  Profit: {metrics['total_profit']/1e18:.6f} ETH")
log(f"  Gas: {metrics['total_gas']:,} ({metrics['gas_utilization']*100:.1f}%)")
log(f"  Time: {t_total:.1f}s")

# Compare with optimal
optimal_profit = sum(p for p in profits if p > 0)
optimal_gas = sum(gas_costs[i] for i, p in enumerate(profits) if p > 0)

log(f"\nOptimal (select all {profitable_count}):")
log(f"  Profit: {optimal_profit/1e18:.6f} ETH")
log(f"  Gas: {optimal_gas:,} ({optimal_gas/CAPACITY*100:.1f}%)")

efficiency = (metrics['total_profit'] / optimal_profit) * 100
log(f"\nEfficiency: {efficiency:.1f}%")

if metrics['total_selected'] == profitable_count:
    log(f"\n🎉 SUCCESS! Selected all {profitable_count} profitable transactions!")
    log(f"   Hierarchical approach found the optimal solution!")
else:
    log(f"\n⚠️  Selected {metrics['total_selected']}/{profitable_count} ({metrics['total_selected']/profitable_count*100:.1f}%)")
    log(f"   Profit efficiency: {efficiency:.1f}%")
    
    missing = profitable_count - metrics['total_selected']
    missing_profit = optimal_profit - metrics['total_profit']
    log(f"   Missing: {missing} transactions, {missing_profit/1e18:.6f} ETH")

log(f"\n{'='*80}")
log("OPTIMIZATION COMPLETE")
log(f"{'='*80}")

# Save results
results = {
    'method': 'hierarchical_lpu',
    'num_tiers': len(tiers),
    'tiers': [
        {
            'name': t['name'],
            'count': len(t['indices']),
            'profit': t['total_profit'],
            'gas': t['total_gas']
        } for t in tiers
    ],
    'results': {
        'selected': metrics['total_selected'],
        'total': profitable_count,
        'profit': metrics['total_profit'],
        'gas': metrics['total_gas'],
        'efficiency': efficiency,
        'time': t_total
    },
    'optimal': {
        'selected': profitable_count,
        'profit': optimal_profit,
        'gas': optimal_gas
    }
}

import json as json_module
with open('hierarchical_lpu_results.json', 'w') as f:
    json_module.dump(results, f, indent=2)

log(f"\nResults saved to: hierarchical_lpu_results.json")

