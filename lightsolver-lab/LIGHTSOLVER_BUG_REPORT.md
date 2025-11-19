# Bug Report: lightsolver_lib v0.7.0

**Date:** November 19, 2025  
**Reporter:** matanfield  
**Package:** lightsolver_lib version 0.7.0  
**Python Version:** 3.12.12  
**Installation Method:** pip install laser-mind-client

## Issue Summary

The `lightsolver_lib` package has a broken `__init__.py` that imports functions which don't exist in the actual library, causing complete import failure and making the package unusable.

## Error Encountered

```python
>>> from lightsolver_lib import probmat_qubo_to_ising
Traceback (most recent call last):
  File "<stdin>", line 1, in <module>
  File ".../lightsolver_lib/__init__.py", line 8, in <module>
    from .lightsolver_lib import embed_coupmat
ImportError: cannot import name 'embed_coupmat' from 'lightsolver_lib.lightsolver_lib'
```

## Root Cause

The `__init__.py` file attempts to import functions that don't exist in `lightsolver_lib.py`:

### Functions Incorrectly Listed in `__init__.py` (DON'T EXIST):
1. `embed_coupmat` - line 8
2. `analyze_sol_XY` - line 9  
3. `generate_animation` - line 10

### Function Missing from `__init__.py` (EXISTS but not exported):
- `best_energy_search_xy` - exists in library but not in `__all__`

## Actual Functions Available in lightsolver_lib.py

```python
# Verified existing functions:
- calc_ising_energies
- probmat_qubo_to_ising
- probmat_ising_to_qubo
- create_random_initial_states
- best_energy_search_xy  # Missing from __init__.py
- calc_ising_energy_from_states
- coupling_matrix_xy

# Verified existing classes:
- XYModelParams
```

## Impact

**Severity:** Critical  
**Scope:** Entire package is unusable without manual modification

Users cannot import ANY function from lightsolver_lib, even the ones that exist, because Python fails on the first bad import in `__init__.py`.

## Reproduction Steps

1. Install: `pip install laser-mind-client` (installs lightsolver_lib 0.7.0 as dependency)
2. Try to import any function: `from lightsolver_lib import probmat_qubo_to_ising`
3. Error: `ImportError: cannot import name 'embed_coupmat'`

## Temporary Workaround

Manually edit the installed package file:  
`.venv/lib/python3.12/site-packages/lightsolver_lib/__init__.py`

```python
# Remove these lines:
from .lightsolver_lib import embed_coupmat
from .lightsolver_lib import analyze_sol_XY
from .lightsolver_lib import generate_animation

# Add this line:
from .lightsolver_lib import best_energy_search_xy

# Update __all__ accordingly
```

## Suggested Fix

Update `lightsolver_lib/__init__.py` to match actual available functions:

```python
from .lightsolver_lib import calc_ising_energies
from .lightsolver_lib import probmat_qubo_to_ising
from .lightsolver_lib import probmat_ising_to_qubo
from .lightsolver_lib import create_random_initial_states
from .lightsolver_lib import calc_ising_energy_from_states
from .lightsolver_lib import XYModelParams
from .lightsolver_lib import coupling_matrix_xy
from .lightsolver_lib import best_energy_search_xy

__all__ = [
    'calc_ising_energies',
    'probmat_qubo_to_ising',
    'probmat_ising_to_qubo',
    'create_random_initial_states',
    'calc_ising_energy_from_states',
    'XYModelParams',
    'coupling_matrix_xy',
    'best_energy_search_xy',
]
```

## Additional Notes

- The missing functions (`embed_coupmat`, etc.) may be planned features not yet implemented
- `best_energy_search_xy` is a critical function for extracting solutions from emulator results
- This bug affects all users trying to use the Virtual Lab emulator functionality

## Environment Details

```
OS: macOS 14.6.0 (Darwin 24.6.0)
Python: 3.12.12
laser-mind-client: 0.1.1
lightsolver_lib: 0.7.0
Installation: Fresh install via pip
```

## Request

Please release lightsolver_lib v0.7.1 with corrected `__init__.py` that matches the actual available functions in the library.

---

**Contact:** Available for testing updated package if needed.

