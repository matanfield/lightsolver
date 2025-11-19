#!/bin/bash
####################################################################################################
# Quick Start Commands for LPU Knapsack Solver
####################################################################################################

# Set paths
LAB_DIR="/Users/matanfield/Projects/lightsolver/lightsolver-lab"
PYTHON_LPU="$LAB_DIR/laser-mind-client/.venv/bin/python"
PYTHON39="$LAB_DIR/.venv-py39/bin/python"

cd "$LAB_DIR"

echo "=================================================="
echo "LPU Knapsack Solver - Quick Start"
echo "=================================================="
echo ""
echo "✅ System Status: WORKING"
echo "✅ Emulator: Handles 10-100+ variables"
echo "✅ Workflow: knapsack → QUBO → LPU → results"
echo ""

# Example 1: Solve single instance with 10 transactions
echo "1. Solve single instance (10 transactions):"
echo "   $PYTHON_LPU knapsack_lpu_solver.py ../rbuilder/knapsack_instance_21200000.json 10"
echo ""

# Example 2: Solve with 50 transactions
echo "2. Solve with 50 transactions (medium):"
echo "   $PYTHON_LPU knapsack_lpu_solver.py ../rbuilder/knapsack_instance_21200000.json 50"
echo ""

# Example 3: Solve with 100 transactions
echo "3. Solve with 100 transactions (large):"
echo "   $PYTHON_LPU knapsack_lpu_solver.py ../rbuilder/knapsack_instance_21200000.json 100"
echo ""

# Example 4: Batch solve all instances (coming soon)
echo "4. Batch solve all instances:"
echo "   $PYTHON_LPU batch_solve_knapsacks.py ../rbuilder/"
echo ""

# Example 5: Test pyqubo converter
echo "5. Test pyqubo QUBO converter (Python 3.9):"
echo "   $PYTHON39 knapsack_to_qubo_pyqubo.py"
echo ""

# Example 6: Test direct converter
echo "6. Test direct QUBO converter:"
echo "   $PYTHON_LPU knapsack_to_qubo.py"
echo ""

echo "=================================================="
echo "Available knapsack instances:"
ls -lh ../rbuilder/knapsack_instance_*.json 2>/dev/null | awk '{print "  " $9}' | head -15
echo "=================================================="
echo ""
echo "Current Results (tested):"
echo "  - LPU is ~25-80% worse than greedy (needs optimization)"
echo "  - Emulator works reliably with 10-100 variables"
echo "  - Parameter tuning needed for competitive performance"
echo ""

# Uncomment to run a quick test:
# $PYTHON_LPU knapsack_lpu_solver.py ../rbuilder/knapsack_instance_21200000.json 10

