import React, { useState, useCallback, useEffect } from 'react';

const KnapsackVisual = () => {
  const [selectedItems, setSelectedItems] = useState(new Set());
  const [items, setItems] = useState([]);
  const [numItems, setNumItems] = useState(3);
  const [solutions, setSolutions] = useState({ greedyValue: 0, optimalValue: 0 });
  
  const capacity = 100;
  
  const getValue = (ids, items) => ids.reduce((s, id) => s + items.find(i => i.id === id).value, 0);
  
  const solveGreedy = (items, cap) => {
    const sorted = [...items].sort((a, b) => b.density - a.density);
    const selected = [];
    let weight = 0;
    for (const item of sorted) {
      if (weight + item.weight <= cap) {
        selected.push(item.id);
        weight += item.weight;
      }
    }
    return selected;
  };
  
  const solveSmartGreedy = (items, cap) => {
    // Standard greedy result
    const greedyResult = solveGreedy(items, cap);
    const greedyValue = getValue(greedyResult, items);
    
    // Find single most valuable item that fits
    let bestSingleItem = null;
    let bestSingleValue = 0;
    for (const item of items) {
      if (item.weight <= cap && item.value > bestSingleValue) {
        bestSingleValue = item.value;
        bestSingleItem = item.id;
      }
    }
    
    // Return whichever is better
    if (bestSingleValue > greedyValue) {
      return [bestSingleItem];
    }
    return greedyResult;
  };
  
  const solveOptimal = (items, cap) => {
    const n = items.length;
    
    // For small n, use brute force
    if (n <= 20) {
      let best = [];
      let bestValue = 0;
      for (let mask = 0; mask < (1 << n); mask++) {
        let weight = 0;
        let value = 0;
        const subset = [];
        for (let i = 0; i < n; i++) {
          if (mask & (1 << i)) {
            weight += items[i].weight;
            value += items[i].value;
            subset.push(items[i].id);
          }
        }
        if (weight <= cap && value > bestValue) {
          bestValue = value;
          best = subset;
        }
      }
      return best;
    }
    
    // For larger n, use dynamic programming
    const dp = Array(n + 1).fill(null).map(() => Array(cap + 1).fill(0));
    
    for (let i = 1; i <= n; i++) {
      const item = items[i - 1];
      for (let w = 0; w <= cap; w++) {
        if (item.weight <= w) {
          dp[i][w] = Math.max(dp[i - 1][w], dp[i - 1][w - item.weight] + item.value);
        } else {
          dp[i][w] = dp[i - 1][w];
        }
      }
    }
    
    // Backtrack to find selected items
    const selected = [];
    let w = cap;
    for (let i = n; i > 0 && w > 0; i--) {
      if (dp[i][w] !== dp[i - 1][w]) {
        selected.push(items[i - 1].id);
        w -= items[i - 1].weight;
      }
    }
    return selected;
  };
  
  const generateProblem = useCallback((n) => {
    let bestProblem = null;
    let bestGap = 0;
    
    const maxAttempts = n <= 10 ? 100 : 50;
    const minGapPercent = n <= 10 ? 10 : 5;
    
    for (let attempt = 0; attempt < maxAttempts; attempt++) {
      const genItems = [];
      
      for (let i = 0; i < n; i++) {
        const weight = 15 + Math.floor(Math.random() * 50); // 15-64 kg
        const density = 2 + Math.random() * 6;
        const value = Math.round(weight * density);
        genItems.push({
          weight,
          value,
          density: Math.round(value / weight * 10) / 10,
        });
      }
      
      // Sort by density and assign IDs 1-n
      genItems.sort((a, b) => b.density - a.density);
      genItems.forEach((item, i) => item.id = i + 1);
      
      const greedy = solveGreedy(genItems, capacity);
      const optimal = solveOptimal(genItems, capacity);
      const greedyValue = getValue(greedy, genItems);
      const optimalValue = getValue(optimal, genItems);
      
      const gap = optimalValue - greedyValue;
      const gapPercent = greedyValue > 0 ? (gap / optimalValue) * 100 : 0;
      
      if (gap > 0 && gapPercent >= minGapPercent) {
        if (gap > bestGap) {
          bestGap = gap;
          bestProblem = { items: genItems, greedyValue, optimalValue };
        }
      }
    }
    
    if (!bestProblem) {
      const fallbackItems = [];
      for (let i = 0; i < n; i++) {
        const weight = 20 + i * 10;
        const value = Math.round(weight * (6 - i * 0.5));
        fallbackItems.push({
          id: i + 1,
          weight,
          value,
          density: Math.round(value / weight * 10) / 10,
        });
      }
      bestProblem = { 
        items: fallbackItems, 
        greedyValue: getValue(solveGreedy(fallbackItems, capacity), fallbackItems),
        optimalValue: getValue(solveOptimal(fallbackItems, capacity), fallbackItems)
      };
    }
    
    setItems(bestProblem.items);
    setSolutions({ greedyValue: bestProblem.greedyValue, optimalValue: bestProblem.optimalValue });
    setSelectedItems(new Set());
  }, []);
  
  useEffect(() => {
    generateProblem(numItems);
  }, [generateProblem, numItems]);
  
  const handleNumItemsChange = (n) => {
    const newN = Math.max(2, Math.min(6, n));
    setNumItems(newN);
    generateProblem(newN);
  };
  
  const totalWeight = [...selectedItems].reduce((sum, id) => {
    const item = items.find(i => i.id === id);
    return sum + (item ? item.weight : 0);
  }, 0);
  
  const totalValue = [...selectedItems].reduce((sum, id) => {
    const item = items.find(i => i.id === id);
    return sum + (item ? item.value : 0);
  }, 0);
  
  const toggleItem = (itemId) => {
    const item = items.find(i => i.id === itemId);
    if (!item) return;
    const newSelected = new Set(selectedItems);
    
    if (selectedItems.has(itemId)) {
      newSelected.delete(itemId);
    } else if (totalWeight + item.weight <= capacity) {
      newSelected.add(itemId);
    }
    setSelectedItems(newSelected);
  };
  
  const canAdd = (itemId) => {
    if (selectedItems.has(itemId)) return true;
    const item = items.find(i => i.id === itemId);
    return item && totalWeight + item.weight <= capacity;
  };
  
  const applyStrategy = (strategy) => {
    if (strategy === 'greedy') setSelectedItems(new Set(solveGreedy(items, capacity)));
    else if (strategy === 'smartGreedy') setSelectedItems(new Set(solveSmartGreedy(items, capacity)));
    else if (strategy === 'optimal') setSelectedItems(new Set(solveOptimal(items, capacity)));
    else setSelectedItems(new Set());
  };
  
  const smartGreedyValue = getValue(solveSmartGreedy(items, capacity), items);
  const gapPercent = solutions.optimalValue > 0 
    ? Math.round((1 - smartGreedyValue / solutions.optimalValue) * 100) 
    : 0;

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 p-8">
      <div className="max-w-3xl mx-auto">
        {/* Header */}
        <h1 className="text-2xl font-bold text-gray-800 text-center mb-8">
          Knapsack
        </h1>
        
        {/* Main content */}
        <div className="grid grid-cols-2 gap-8">
          {/* Items table */}
          <div className="bg-white rounded-xl shadow-sm p-5">
            <div className="flex justify-between items-center mb-3">
              <div className="flex items-center gap-2">
                <span className="text-sm text-gray-500">n:</span>
                <input
                  type="number"
                  min="2"
                  max="20"
                  value={numItems}
                  onChange={(e) => setNumItems(Math.max(2, Math.min(20, parseInt(e.target.value) || 2)))}
                  className="w-16 px-2 py-1 text-sm border rounded text-center"
                />
              </div>
              <button
                onClick={() => generateProblem(numItems)}
                className="text-sm text-blue-600 hover:text-blue-800 transition-colors"
              >
                Refresh
              </button>
            </div>
            
            <div className="max-h-80 overflow-y-auto">
              <table className="w-full">
                <thead className="sticky top-0 bg-white">
                  <tr className="text-left text-sm text-gray-500 border-b">
                    <th className="pb-3">Item</th>
                    <th className="pb-3 text-right">Weight</th>
                    <th className="pb-3 text-right">Value</th>
                    <th className="pb-3 text-right">$/kg</th>
                  </tr>
                </thead>
                <tbody>
                  {[...items]
                    .sort((a, b) => b.density - a.density)
                    .map((item) => {
                      const isSelected = selectedItems.has(item.id);
                      const canSelect = canAdd(item.id);
                      
                      return (
                        <tr 
                          key={item.id}
                          onClick={() => toggleItem(item.id)}
                          className={`border-b last:border-0 cursor-pointer transition-all ${
                            isSelected 
                              ? 'bg-blue-50' 
                              : canSelect 
                                ? 'hover:bg-gray-50' 
                                : 'opacity-40 cursor-not-allowed'
                          }`}
                        >
                          <td className="py-2">
                            <span className="font-medium">{item.id}</span>
                          </td>
                          <td className="py-2 text-right font-mono text-sm">{item.weight}kg</td>
                          <td className="py-2 text-right font-mono text-sm text-green-600">${item.value}</td>
                          <td className="py-2 text-right font-mono text-sm text-purple-600">{item.density}</td>
                        </tr>
                      );
                    })}
                </tbody>
              </table>
            </div>
            
            {/* Strategy buttons */}
            <div className="mt-4 pt-4 border-t flex flex-wrap gap-2">
              <button
                onClick={() => applyStrategy('smartGreedy')}
                className="px-3 py-1.5 text-sm bg-amber-100 text-amber-700 rounded-lg hover:bg-amber-200 transition-colors"
              >
                Greedy+ (${smartGreedyValue})
              </button>
              <button
                onClick={() => applyStrategy('optimal')}
                className="px-3 py-1.5 text-sm bg-green-100 text-green-700 rounded-lg hover:bg-green-200 transition-colors"
              >
                Optimal (${solutions.optimalValue})
              </button>
              <button
                onClick={() => applyStrategy('clear')}
                className="px-3 py-1.5 text-sm bg-gray-100 text-gray-600 rounded-lg hover:bg-gray-200 transition-colors"
              >
                Clear
              </button>
            </div>
            
            {/* Gap indicator */}
            <div className="mt-3 text-sm text-gray-700 font-bold">
              Greedy+ misses {gapPercent}% of optimal value
            </div>
          </div>
          
          {/* Knapsack visualization */}
          <div className="flex flex-col items-center">
            {/* Simple container */}
            <div 
              className="relative border-2 border-gray-300 rounded-lg bg-gray-50 overflow-hidden"
              style={{ width: '160px', height: '200px' }}
            >
              {/* Items stacked from bottom */}
              <div className="absolute bottom-0 left-0 right-0 flex flex-col-reverse p-2 gap-1">
                {[...selectedItems].map(id => {
                  const item = items.find(i => i.id === id);
                  if (!item) return null;
                  const height = (item.weight / capacity) * 180;
                  return (
                    <div
                      key={id}
                      className="w-full rounded flex items-center justify-center text-white font-bold text-sm transition-all duration-300 bg-blue-500"
                      style={{
                        height: `${height}px`,
                      }}
                    >
                      {item.id}: ${item.value}
                    </div>
                  );
                })}
              </div>
            </div>
            
            {/* Stats */}
            <div className="mt-6 text-center">
              <div className="text-sm text-gray-500 mb-1">
                {totalWeight} / {capacity} kg
              </div>
              <div className="w-32 h-2 bg-gray-200 rounded-full overflow-hidden">
                <div 
                  className={`h-full transition-all duration-300 ${
                    totalWeight === capacity ? 'bg-green-500' : 'bg-blue-500'
                  }`}
                  style={{ width: `${(totalWeight / capacity) * 100}%` }}
                />
              </div>
              <div className="mt-3 text-3xl font-bold text-gray-800">
                ${totalValue}
              </div>
              {totalValue >= solutions.optimalValue && solutions.optimalValue > 0 && (
                <div className="text-green-600 text-sm font-medium mt-1">
                  ✓ Optimal!
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default KnapsackVisual;
