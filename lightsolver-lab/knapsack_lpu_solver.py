####################################################################################################
# Complete workflow: Knapsack JSON → QUBO → LPU Solution → Compare with Greedy
# 
# This script:
# 1. Loads knapsack instance JSON (real block data)
# 2. Converts to QUBO matrix
# 3. Solves using LightSolver LPU
# 4. Converts solution back to transaction list
# 5. Calculates total profit
# 6. Compares with greedy results (if available)
#
# Usage:
#   python knapsack_lpu_solver.py path/to/knapsack_instance.json
####################################################################################################

import json
import sys
import os
import numpy as np
from laser_mind_client import LaserMind

# Ethereum block gas limit (standard)
BLOCK_GAS_LIMIT = 30_000_000

# Emulator mode (True = emulator with 1000+ vars, False = physical LPU with 5-100 vars)
USE_EMULATOR = True

# Import only the functions that actually exist in lightsolver_lib
if USE_EMULATOR:
    try:
        from lightsolver_lib.lightsolver_lib import (
            probmat_qubo_to_ising, 
            coupling_matrix_xy, 
            XYModelParams, 
            best_energy_search_xy
        )
    except ImportError as e:
        print(f"Warning: Could not import from lightsolver_lib: {e}")
        print("Falling back to physical LPU mode.")
        USE_EMULATOR = False


def load_knapsack_json(filepath):
    """Load knapsack instance from JSON file."""
    with open(filepath, 'r') as f:
        data = json.load(f)
    return data


def parse_knapsack_data(data):
    """
    Parse knapsack data from JSON format.
    
    Returns:
        block_number: int
        tx_ids: list of transaction IDs
        profits: list of profits (in wei, as integers)
        gas_costs: list of gas costs
        capacity: gas limit
    """
    block_number = data['block_number']
    items = data['items']
    
    tx_ids = []
    profits = []
    gas_costs = []
    
    for item in items:
        tx_ids.append(item['id'])
        # Convert hex profit to integer
        profit_hex = item['profit']
        profit_int = int(profit_hex, 16) if profit_hex.startswith('0x') else int(profit_hex)
        profits.append(profit_int)
        gas_costs.append(item['gas'])
    
    return block_number, tx_ids, profits, gas_costs, BLOCK_GAS_LIMIT


def knapsack_to_qubo(profits, gas_costs, capacity, penalty=None):
    """
    Convert knapsack problem to QUBO matrix.
    
    Args:
        profits: list of item profits (to maximize)
        gas_costs: list of gas costs (weights)
        capacity: maximum gas limit
        penalty: constraint penalty strength (auto-calculated if None)
    
    Returns:
        Q: QUBO matrix (upper triangular)
        offset: constant offset
    """
    n = len(profits)
    
    # Auto-calculate penalty if not provided
    if penalty is None:
        max_profit = max(profits) if profits else 1
        max_gas = max(gas_costs) if gas_costs else 1
        # Scale penalty to ensure constraint violation is more costly than profit gain
        penalty = (max_profit / max_gas) * 2
    
    Q = np.zeros((n, n))
    
    # Diagonal terms: -profit_i + penalty*(gas_i^2 - 2*capacity*gas_i)
    for i in range(n):
        Q[i, i] = -profits[i] + penalty * (gas_costs[i]**2 - 2*capacity*gas_costs[i])
    
    # Off-diagonal terms (upper triangle): 2*penalty*gas_i*gas_j
    for i in range(n):
        for j in range(i+1, n):
            Q[i, j] = 2 * penalty * gas_costs[i] * gas_costs[j]
    
    # Constant offset: penalty * capacity^2
    offset = penalty * capacity**2
    
    return Q, offset


def solve_qubo_emulator(Q_matrix, token_file_path, num_runs=10, num_iterations=1000):
    """
    Solve QUBO using LightSolver Virtual Lab Emulator.
    
    Args:
        Q_matrix: QUBO matrix
        token_file_path: path to LightSolver token file
        num_runs: number of simulation runs
        num_iterations: number of iterations per run
    
    Returns:
        solution: binary vector (list of 0s and 1s)
        response: full emulator response
    """
    # Connect to LightSolver Cloud
    lsClient = LaserMind(pathToRefreshTokenFile=token_file_path)
    
    n = Q_matrix.shape[0]
    print(f"Converting QUBO ({n}x{n}) to coupling matrix...")
    
    # Normalize QUBO matrix to avoid numerical issues
    Q_max = np.max(np.abs(Q_matrix))
    Q_normalized = Q_matrix / Q_max if Q_max > 0 else Q_matrix
    print(f"  Normalized QUBO (max value: {Q_max:.2e})")
    
    # Step 1: QUBO → Ising
    I, offset_ising = probmat_qubo_to_ising(Q_normalized)
    print(f"  ✓ Ising matrix created (offset: {offset_ising:.2e})")
    
    # Step 2: Ising → Coupling Matrix
    coupling_matrix = coupling_matrix_xy(I, XYModelParams())
    
    # Verify coupling matrix constraint
    row_sums = np.abs(coupling_matrix).sum(axis=0)
    is_valid = (row_sums < 1).all()
    if not is_valid:
        print(f"  ⚠️  Warning: Coupling matrix row sums exceed 1, adjusting XY parameters...")
        # Try with smaller coupling amplitude
        coupling_matrix = coupling_matrix_xy(I, XYModelParams(alphaI=0.7, coupAmp=0.2))
        row_sums = np.abs(coupling_matrix).sum(axis=0)
        is_valid = (row_sums < 1).all()
    
    print(f"  ✓ Coupling matrix created (valid: {is_valid})")
    
    # Step 3: Solve with emulator
    print(f"Sending to Virtual Lab Emulator (runs={num_runs}, iterations={num_iterations})...")
    res = lsClient.solve_coupling_matrix_sim_lpu(
        matrix_data=coupling_matrix.astype(np.complex64),
        num_runs=num_runs,
        num_iterations=num_iterations,
        rounds_per_record=1
    )
    print(f"  ✓ Emulator solution received")
    
    # Step 4: Extract solution from laser states
    record_states = res['data']['result']['record_states']  # dims: num_records x num_runs x num_lasers
    
    # Try all runs and pick the best based on simple phase thresholding
    best_solution = None
    best_energy = float('inf')
    
    for run_idx in range(num_runs):
        # Get final state for this run: last iteration, all lasers
        final_state = record_states[-1, run_idx, :]  # [num_lasers]
        
        # Extract solution from phases: positive phase → +1, negative → -1 (Ising)
        phases = np.angle(final_state)
        ising_state = np.where(phases >= 0, 1, -1)
        
        # Calculate energy for this state
        energy = np.dot(ising_state, np.dot(I, ising_state))
        
        if energy < best_energy:
            best_energy = energy
            # Convert Ising {-1, +1} to QUBO {0, 1}
            best_solution = ((ising_state + 1) // 2).astype(int).tolist()
    
    print(f"  Best energy: {best_energy:.4f}")
    
    return best_solution, res


def solve_qubo_lpu_hardware(Q_matrix, token_file_path, timeout=60):
    """
    Solve QUBO using physical LightSolver LPU hardware (limited to 5-100 variables).
    
    Args:
        Q_matrix: QUBO matrix
        token_file_path: path to LightSolver token file
        timeout: timeout in seconds
    
    Returns:
        solution: binary vector (list of 0s and 1s)
        response: full LPU response
    """
    # Connect to LightSolver Cloud
    lsClient = LaserMind(pathToRefreshTokenFile=token_file_path)
    
    # Request LPU solution
    print(f"Sending QUBO matrix ({Q_matrix.shape[0]}x{Q_matrix.shape[1]}) to physical LPU...")
    res = lsClient.solve_qubo_lpu(matrixData=Q_matrix)
    
    # Verify response format
    assert 'command' in res, "Missing 'command' field"
    assert 'data' in res, "Missing 'data' field"
    assert 'solutions' in res['data'], "Missing 'solutions' field"
    
    # Extract best solution
    solutions = res['data']['solutions']
    if not solutions:
        raise ValueError("No solutions returned from LPU")
    
    # Get the first solution (best one)
    best_solution = solutions[0]['solution']
    
    return best_solution, res


def evaluate_solution(solution, tx_ids, profits, gas_costs, capacity):
    """
    Evaluate a solution and return metrics.
    
    Args:
        solution: binary vector
        tx_ids: list of transaction IDs
        profits: list of profits
        gas_costs: list of gas costs
        capacity: gas limit
    
    Returns:
        dict with metrics
    """
    selected_indices = [i for i, x in enumerate(solution) if x == 1]
    selected_txs = [tx_ids[i] for i in selected_indices]
    total_profit = sum(profits[i] for i in selected_indices)
    total_gas = sum(gas_costs[i] for i in selected_indices)
    
    # Check constraint satisfaction
    constraint_satisfied = total_gas <= capacity
    constraint_violation = max(0, total_gas - capacity)
    
    return {
        'num_selected': len(selected_indices),
        'selected_indices': selected_indices,
        'selected_txs': selected_txs,
        'total_profit': total_profit,
        'total_profit_eth': total_profit / 1e18,  # Convert wei to ETH
        'total_gas': total_gas,
        'capacity': capacity,
        'gas_utilization': total_gas / capacity if capacity > 0 else 0,
        'constraint_satisfied': constraint_satisfied,
        'constraint_violation': constraint_violation,
    }


def greedy_knapsack(profits, gas_costs, capacity):
    """
    Solve knapsack using greedy algorithm (profit/gas ratio).
    
    Returns:
        solution: binary vector
    """
    n = len(profits)
    
    # Calculate profit/gas ratios
    items = []
    for i in range(n):
        if gas_costs[i] > 0:
            ratio = profits[i] / gas_costs[i]
            items.append((i, ratio, profits[i], gas_costs[i]))
    
    # Sort by ratio (descending)
    items.sort(key=lambda x: x[1], reverse=True)
    
    # Greedy selection
    solution = [0] * n
    total_gas = 0
    
    for idx, ratio, profit, gas in items:
        if total_gas + gas <= capacity:
            solution[idx] = 1
            total_gas += gas
    
    return solution


def format_number(num):
    """Format large numbers with commas."""
    return f"{num:,}"


def select_top_transactions(tx_ids, profits, gas_costs, max_items=100):
    """
    Select top transactions by profit/gas ratio.
    LPU has a limit of 5-100 variables, so we need to pre-filter.
    
    Returns:
        filtered tx_ids, profits, gas_costs, mapping
    """
    n = len(tx_ids)
    
    # Calculate profit/gas ratios
    items = []
    for i in range(n):
        if gas_costs[i] > 0:
            ratio = profits[i] / gas_costs[i]
            items.append((i, ratio, tx_ids[i], profits[i], gas_costs[i]))
    
    # Sort by ratio (descending) and take top max_items
    items.sort(key=lambda x: x[1], reverse=True)
    items = items[:max_items]
    
    # Extract filtered data
    filtered_tx_ids = [item[2] for item in items]
    filtered_profits = [item[3] for item in items]
    filtered_gas_costs = [item[4] for item in items]
    index_mapping = [item[0] for item in items]  # Original indices
    
    return filtered_tx_ids, filtered_profits, filtered_gas_costs, index_mapping


def main(knapsack_json_path, token_file_path=None, max_lpu_variables=None, custom_alpha=None):
    """Main workflow."""
    
    # Set default based on mode
    if max_lpu_variables is None:
        max_lpu_variables = 1000 if USE_EMULATOR else 20
    
    mode_name = "EMULATOR" if USE_EMULATOR else "PHYSICAL LPU"
    print("="*80)
    print(f"KNAPSACK TO LPU SOLVER ({mode_name})")
    print("="*80)
    
    # Default token path
    if token_file_path is None:
        token_file_path = os.path.join(
            os.path.dirname(__file__),
            "laser-mind-client/examples/lightsolver-token.txt"
        )
    
    # 1. Load knapsack data
    print(f"\n1. Loading knapsack instance from: {knapsack_json_path}")
    data = load_knapsack_json(knapsack_json_path)
    block_number, tx_ids, profits, gas_costs, capacity = parse_knapsack_data(data)
    
    print(f"   Block number: {block_number}")
    print(f"   Number of transactions: {len(tx_ids)}")
    print(f"   Total profit available: {sum(profits)/1e18:.6f} ETH ({format_number(sum(profits))} wei)")
    print(f"   Total gas available: {format_number(sum(gas_costs))}")
    print(f"   Gas limit (capacity): {format_number(capacity)}")
    
    # 1b. Filter to top transactions if needed (LPU constraint: 5-100 variables)
    if len(tx_ids) > max_lpu_variables:
        print(f"\n   ⚠️  Problem size ({len(tx_ids)}) exceeds LPU limit ({max_lpu_variables})")
        print(f"   Selecting top {max_lpu_variables} transactions by profit/gas ratio...")
        tx_ids_lpu, profits_lpu, gas_costs_lpu, index_mapping = select_top_transactions(
            tx_ids, profits, gas_costs, max_lpu_variables
        )
        print(f"   Filtered to {len(tx_ids_lpu)} transactions")
        print(f"   Filtered profit available: {sum(profits_lpu)/1e18:.6f} ETH")
    else:
        tx_ids_lpu = tx_ids
        profits_lpu = profits
        gas_costs_lpu = gas_costs
        index_mapping = list(range(len(tx_ids)))
    
    # 2. Convert to QUBO
    print(f"\n2. Converting to QUBO matrix...")
    if custom_alpha is not None:
        print(f"   Using custom penalty α = {custom_alpha:.2e}")
    Q, offset = knapsack_to_qubo(profits_lpu, gas_costs_lpu, capacity, penalty=custom_alpha)
    print(f"   QUBO matrix shape: {Q.shape}")
    print(f"   Offset: {offset:.2e}")
    
    # 3. Solve with LPU/Emulator
    solver_name = "Emulator" if USE_EMULATOR else "Physical LPU"
    print(f"\n3. Solving with LightSolver {solver_name}...")
    
    if USE_EMULATOR:
        lpu_solution, lpu_response = solve_qubo_emulator(Q, token_file_path)
    else:
        lpu_solution, lpu_response = solve_qubo_lpu_hardware(Q, token_file_path)
    
    print(f"   ✓ {solver_name} solution received")
    
    # 4. Evaluate LPU solution (on filtered set)
    print(f"\n4. Evaluating LPU solution...")
    lpu_metrics = evaluate_solution(lpu_solution, tx_ids_lpu, profits_lpu, gas_costs_lpu, capacity)
    
    print(f"   Transactions selected: {lpu_metrics['num_selected']}")
    print(f"   Total profit: {lpu_metrics['total_profit_eth']:.6f} ETH ({format_number(lpu_metrics['total_profit'])} wei)")
    print(f"   Total gas used: {format_number(lpu_metrics['total_gas'])}")
    print(f"   Gas utilization: {lpu_metrics['gas_utilization']*100:.2f}%")
    print(f"   Constraint satisfied: {lpu_metrics['constraint_satisfied']}")
    if not lpu_metrics['constraint_satisfied']:
        print(f"   ⚠️  Constraint violation: {format_number(lpu_metrics['constraint_violation'])} gas over limit")
    
    # 5. Compare with greedy (on same filtered set for fair comparison)
    print(f"\n5. Comparing with greedy algorithm (on same subset)...")
    greedy_solution_filtered = greedy_knapsack(profits_lpu, gas_costs_lpu, capacity)
    greedy_metrics_filtered = evaluate_solution(greedy_solution_filtered, tx_ids_lpu, profits_lpu, gas_costs_lpu, capacity)
    
    print(f"   Greedy transactions selected: {greedy_metrics_filtered['num_selected']}")
    print(f"   Greedy total profit: {greedy_metrics_filtered['total_profit_eth']:.6f} ETH ({format_number(greedy_metrics_filtered['total_profit'])} wei)")
    print(f"   Greedy gas used: {format_number(greedy_metrics_filtered['total_gas'])}")
    print(f"   Greedy gas utilization: {greedy_metrics_filtered['gas_utilization']*100:.2f}%")
    
    # 5b. Also run greedy on full dataset for reference
    if len(tx_ids) > max_lpu_variables:
        print(f"\n   Running greedy on full dataset for reference...")
        greedy_solution_full = greedy_knapsack(profits, gas_costs, capacity)
        greedy_metrics_full = evaluate_solution(greedy_solution_full, tx_ids, profits, gas_costs, capacity)
        print(f"   Greedy (full) transactions selected: {greedy_metrics_full['num_selected']}")
        print(f"   Greedy (full) total profit: {greedy_metrics_full['total_profit_eth']:.6f} ETH")
    else:
        greedy_metrics_full = greedy_metrics_filtered
    
    # 6. Comparison
    print(f"\n6. COMPARISON RESULTS (LPU vs Greedy on filtered subset)")
    print("="*80)
    
    profit_diff = lpu_metrics['total_profit'] - greedy_metrics_filtered['total_profit']
    profit_diff_eth = profit_diff / 1e18
    profit_improvement = (profit_diff / greedy_metrics_filtered['total_profit'] * 100) if greedy_metrics_filtered['total_profit'] > 0 else 0
    
    print(f"   LPU Profit:    {lpu_metrics['total_profit_eth']:.6f} ETH")
    print(f"   Greedy Profit: {greedy_metrics_filtered['total_profit_eth']:.6f} ETH")
    print(f"   Difference:    {profit_diff_eth:+.6f} ETH ({profit_improvement:+.2f}%)")
    
    if profit_diff > 0:
        print(f"   🎉 LPU is BETTER by {profit_diff_eth:.6f} ETH ({profit_improvement:.2f}%)")
    elif profit_diff < 0:
        print(f"   ⚠️  Greedy is better by {-profit_diff_eth:.6f} ETH ({-profit_improvement:.2f}%)")
    else:
        print(f"   = Both solutions have the same profit")
    
    print()
    print(f"   Gas utilization: LPU {lpu_metrics['gas_utilization']*100:.2f}% vs Greedy {greedy_metrics_filtered['gas_utilization']*100:.2f}%")
    
    if len(tx_ids) > max_lpu_variables:
        print(f"\n   Note: Greedy on full dataset achieved {greedy_metrics_full['total_profit_eth']:.6f} ETH")
    
    # Save results
    results_file = knapsack_json_path.replace('.json', '_lpu_results.json')
    results = {
        'block_number': block_number,
        'problem_size_original': len(tx_ids),
        'problem_size_filtered': len(tx_ids_lpu),
        'lpu_solution': {
            'selected_tx_indices': lpu_metrics['selected_indices'],
            'num_txs': lpu_metrics['num_selected'],
            'total_profit_wei': lpu_metrics['total_profit'],
            'total_profit_eth': lpu_metrics['total_profit_eth'],
            'total_gas': lpu_metrics['total_gas'],
            'gas_utilization': lpu_metrics['gas_utilization'],
            'constraint_satisfied': lpu_metrics['constraint_satisfied'],
        },
        'greedy_solution_filtered': {
            'selected_tx_indices': greedy_metrics_filtered['selected_indices'],
            'num_txs': greedy_metrics_filtered['num_selected'],
            'total_profit_wei': greedy_metrics_filtered['total_profit'],
            'total_profit_eth': greedy_metrics_filtered['total_profit_eth'],
            'total_gas': greedy_metrics_filtered['total_gas'],
            'gas_utilization': greedy_metrics_filtered['gas_utilization'],
        },
        'greedy_solution_full': {
            'num_txs': greedy_metrics_full['num_selected'],
            'total_profit_wei': greedy_metrics_full['total_profit'],
            'total_profit_eth': greedy_metrics_full['total_profit_eth'],
            'total_gas': greedy_metrics_full['total_gas'],
            'gas_utilization': greedy_metrics_full['gas_utilization'],
        },
        'comparison': {
            'profit_difference_wei': profit_diff,
            'profit_difference_eth': profit_diff_eth,
            'profit_improvement_percent': profit_improvement,
            'lpu_is_better': profit_diff > 0,
        }
    }
    
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n   Results saved to: {results_file}")
    print("="*80)
    
    return results


if __name__ == "__main__":
    if len(sys.argv) < 2:
        mode_str = "Emulator (1000+ vars)" if USE_EMULATOR else "Physical LPU (5-100 vars)"
        default_vars = "1000" if USE_EMULATOR else "20"
        
        print("Usage: python knapsack_lpu_solver.py <knapsack_instance.json> [max_variables] [alpha]")
        print("\nExamples:")
        print("  python knapsack_lpu_solver.py ../rbuilder/knapsack_instance_21200000.json")
        print("  python knapsack_lpu_solver.py ../rbuilder/knapsack_instance_21200000.json 75")
        print("  python knapsack_lpu_solver.py ../rbuilder/knapsack_instance_21200000.json 75 1e5")
        print(f"\nMode: {mode_str}")
        print(f"Default max_variables: {default_vars}")
        print("Default alpha: auto-calculated (usually too large!)")
        print("\nRecommended alpha values: 1e3 to 1e6")
        sys.exit(1)
    
    knapsack_json = sys.argv[1]
    max_vars = int(sys.argv[2]) if len(sys.argv) > 2 else None
    custom_alpha = float(sys.argv[3]) if len(sys.argv) > 3 else None
    
    main(knapsack_json, None, max_vars, custom_alpha)

