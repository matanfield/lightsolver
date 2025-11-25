# Prototype simulation

**Mission:** Find indication for LPU superiority over greedy on GPU/CPU for ETH block bulding.
**Goal:** Better optimize simulated block building with LPU emulator (to indicate edge for real LPU in realtime block building).
**How:** Block building live data → historical data → cleaned Knapsack array → QUBO → Ising → LPU emulator

### Steps taken

- Step 1 (approximation, assume valid): Live → static historical data → Knapsack array
    - Approximate live block building with retrospective block building on historical data
    - Real data streams in over time, with multiple improving simulations, time constraints etc
    - There’s cleanup of irrelevant and conflicting transactions, which is also dynamical in time
    - Constraints: haven’t dived into which and how it simulates the real process
    - The optimization over the resulting array is a pure knapsack problem → but there is indication (yet to be understood) that real problem and what we neglect along the way has more to it (could be related to the conflicting transactions constraints)
    - Which script is doing this? What is the mempool dumpster data we start with exactly? what are the operations we do over it? 
    - Regardless, we should make sure that eventually we run greedy and emulator on the same final array
- Step 2 (should be exact under fine-tuning): Transform Knapsack to QUBO
    - There’s an approximate transformation which becomes exact fir fine-tuned penalty parameter
    - To understand better the relationship of the fine-tuning to the mapping -- how could it be exact if it depends on fine-tuning?
    - In practice, it's not clear how to fine-tune beyond trial and error
    - How can we test this step alone?
- Step 3 (exact): Transform QUBO to Ising
    - They are equivalent → simple change of variables
    - Why aren’t we transforming Knapsack to Ising directly?
    - Using lab's scripts - which exactly? How can we test it alone?
- Step 4 (uncontrolled approximation): Compute Ising approximately with LPU emulator
    - Real LPU solves Ising approximately → understand approximation (not sure needed rn)
    - LPU emulator approximates LPU → understand approximation (not sure needed rn)
    - Emulator (and so LPU) has paramters, which are absent from some of the scripts - apparently hard-coded; but appear on some other scripts (see coupmat); might need to play with them to make this approximation actually work