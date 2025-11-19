####################################################################################################
# Batch solve multiple knapsack instances with LPU
# 
# Usage:
#   python batch_solve_knapsacks.py <directory_with_json_files>
#   python batch_solve_knapsacks.py ../rbuilder/knapsack_instance_*.json
####################################################################################################

import sys
import os
import glob
import json
from knapsack_lpu_solver import main as solve_knapsack


def batch_solve(json_pattern):
    """Solve multiple knapsack instances and aggregate results."""
    
    # Find all matching JSON files
    if os.path.isdir(json_pattern):
        json_files = glob.glob(os.path.join(json_pattern, "knapsack_instance_*.json"))
    else:
        json_files = glob.glob(json_pattern)
    
    json_files.sort()
    
    if not json_files:
        print(f"No knapsack JSON files found matching: {json_pattern}")
        return
    
    print(f"Found {len(json_files)} knapsack instances to solve")
    print("="*80)
    
    all_results = []
    
    for i, json_file in enumerate(json_files, 1):
        print(f"\n\n{'='*80}")
        print(f"PROCESSING {i}/{len(json_files)}: {os.path.basename(json_file)}")
        print(f"{'='*80}")
        
        try:
            result = solve_knapsack(json_file)
            all_results.append({
                'file': json_file,
                'success': True,
                'result': result
            })
        except Exception as e:
            print(f"❌ ERROR solving {json_file}: {e}")
            all_results.append({
                'file': json_file,
                'success': False,
                'error': str(e)
            })
    
    # Aggregate results
    print("\n\n" + "="*80)
    print("AGGREGATE RESULTS")
    print("="*80)
    
    successful = [r for r in all_results if r['success']]
    failed = [r for r in all_results if not r['success']]
    
    print(f"\nTotal instances processed: {len(all_results)}")
    print(f"Successful: {len(successful)}")
    print(f"Failed: {len(failed)}")
    
    if successful:
        print(f"\n{'Block':<12} {'LPU Profit (ETH)':<18} {'Greedy Profit (ETH)':<18} {'Improvement':<12} {'Winner':<10}")
        print("-"*80)
        
        total_lpu_profit = 0
        total_greedy_profit = 0
        lpu_wins = 0
        greedy_wins = 0
        ties = 0
        
        for r in successful:
            block = r['result']['block_number']
            lpu_profit = r['result']['lpu_solution']['total_profit_eth']
            greedy_profit = r['result']['greedy_solution']['total_profit_eth']
            improvement = r['result']['comparison']['profit_improvement_percent']
            
            total_lpu_profit += lpu_profit
            total_greedy_profit += greedy_profit
            
            if improvement > 0.01:
                winner = "LPU 🎉"
                lpu_wins += 1
            elif improvement < -0.01:
                winner = "Greedy"
                greedy_wins += 1
            else:
                winner = "Tie"
                ties += 1
            
            print(f"{block:<12} {lpu_profit:<18.6f} {greedy_profit:<18.6f} {improvement:>+10.2f}% {winner:<10}")
        
        print("-"*80)
        print(f"{'TOTAL':<12} {total_lpu_profit:<18.6f} {total_greedy_profit:<18.6f}")
        print()
        print(f"Overall improvement: {(total_lpu_profit - total_greedy_profit)/total_greedy_profit*100:+.2f}%")
        print(f"\nLPU wins: {lpu_wins}")
        print(f"Greedy wins: {greedy_wins}")
        print(f"Ties: {ties}")
        
        # Save aggregate results
        summary_file = "batch_lpu_results_summary.json"
        summary = {
            'total_instances': len(all_results),
            'successful': len(successful),
            'failed': len(failed),
            'total_lpu_profit_eth': total_lpu_profit,
            'total_greedy_profit_eth': total_greedy_profit,
            'overall_improvement_percent': (total_lpu_profit - total_greedy_profit)/total_greedy_profit*100 if total_greedy_profit > 0 else 0,
            'lpu_wins': lpu_wins,
            'greedy_wins': greedy_wins,
            'ties': ties,
            'results': all_results
        }
        
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2)
        
        print(f"\nAggregate results saved to: {summary_file}")
    
    if failed:
        print(f"\n❌ Failed instances:")
        for r in failed:
            print(f"   {os.path.basename(r['file'])}: {r['error']}")
    
    print("="*80)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python batch_solve_knapsacks.py <json_pattern>")
        print("\nExamples:")
        print("  python batch_solve_knapsacks.py ../rbuilder/knapsack_instance_*.json")
        print("  python batch_solve_knapsacks.py ../rbuilder/")
        sys.exit(1)
    
    pattern = sys.argv[1]
    batch_solve(pattern)

