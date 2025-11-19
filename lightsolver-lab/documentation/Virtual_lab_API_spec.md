Virtual LAB API Spec
This document describes the Virtual Lab function exposed by the LaserMind client.

Client setup
Python
from laser_mind_client import LaserMind
lsClient = LaserMind(pathToRefreshTokenFile="C:\\path\\to\\your\\token.txt", logToConsole=True)
from laser_mind_client import LaserMind
lsClient = LaserMind(pathToRefreshTokenFile="C:\\path\\to\\your\\token.txt", logToConsole=True)
solve_coupling_matrix_sim_lpu
Purpose: Run the SIM LPU (virtual lab) solver on a complex coupling matrix.
Synchronous mode returns the full solution; asynchronous mode returns a request descriptor to retrieve later.
Parameters
matrix_data: numpy.ndarray
Type: complex matrix, dtype numpy.complex64
Shape: [num_lasers, num_lasers]
initial_states_seed: int
Optional; default = -1
Used to generate initial states when initial_states_vector is not provided
Must not be used together with initial_states_vector
initial_states_vector: numpy.ndarray | None
Optional; default = None
Type: complex array, dtype numpy.complex64
Shape: [r, num_lasers]; each row is one initial state vector
If provided, do not also set a non-negative initial_states_seed
If provided, num_runs must be 1 (identical initial states produce identical runs)
num_runs: int
Optional; has a default
Number of simulation repetitions
num_iterations: int
Optional; has a default
Total simulation iterations
rounds_per_record: int
Optional; has a default
Sampling stride for time-series recording; must not exceed num_iterations
timeout: int
Optional; has a default
Upper bound on allowed solver time (seconds)
waitForSolution: bool
Optional; default = True
If True, blocks and returns the final solution dictionary
If False, returns a request descriptor (see “Asynchronous return” below)
gain_info_initial_gain: float
Optional; has a default
gain_info_pump_max: float
Optional; has a default
gain_info_pump_tau: float
Optional; has a default
gain_info_pump_treshold: float
Optional; has a default
gain_info_amplification_saturation: float
Optional; has a default
inputPath: str | None
Optional; default = None
Advanced: reference to a pre-uploaded input; typically omit
Return value (synchronous, when waitForSolution=True)
An dictionary with these top-level keys and types:

serviceCommandName: string
Always “SIMLPU”
data: dictionary
heuristic: string
Always “SIMLPU”
result: dictionary
start_states: numpy.ndarray (dtype numpy.complex64)
Shape: [num_runs, num_lasers]
If initial_states_vector was provided with shape [1, num_lasers], this will be [1, num_lasers]
final_states: numpy.ndarray (dtype numpy.complex64)
Shape: [num_runs, num_lasers]
final_gains: numpy.ndarray (dtype numpy.float32)
Shape: [num_runs, num_lasers]
record_states: numpy.ndarray (dtype numpy.complex64)
Shape: [num_records, num_runs, num_lasers]
record_gains: numpy.ndarray (dtype numpy.float32)
Shape: [num_records, num_runs, num_lasers]
solver_time: float
Total solver processing time in seconds
creationTime: string
“DD-MM-YYYY-HH-MM-SS-microseconds”
reqTime: string
“DD-MM-YYYY-HH-MM-SS-microseconds”
reqId: string
userId: string
receivedTime: string
If an error occurs:

error: string (present instead of data)
Notes and constraints:

matrix_data must be square and dtype numpy.complex64.
If initial_states_vector is provided, it must be dtype numpy.complex64 and each row length must equal num_lasers.
Do not set both initial_states_vector and a non-negative initial_states_seed.
rounds_per_record must not exceed num_iterations.
Return value (asynchronous, when waitForSolution=False)
A dictionary you can later use to retrieve the solution:

id: string
reqTime: string (“DD-MM-YYYY-HH-MM-SS-microseconds”)
receivedTime: string
Minimal example
Python
import numpy as np
from laser_mind_client.laser_mind_client import LaserMind

lsClient = LaserMind(pathToRefreshTokenFile="C:\\path\\to\\your\\token.txt", logToConsole=True)

H = np.array([
[0+0j, 1-0.5j],
[1+0.5j, 0+0j]
], dtype=np.complex64)

result = lsClient.solve_coupling_matrix_sim_lpu(
matrix_data=H,
num_runs=1,
num_iterations=1000,
rounds_per_record=50,
timeout=10,
waitForSolution=True
)

final_states = result["data"]["result"]["final_states"] # numpy.complex64, [num_runs, num_lasers]
record_states = result["data"]["result"]["record_states"] # numpy.complex64, [num_records, num_runs, num_lasers]
import numpy as np
from laser_mind_client.laser_mind_client import LaserMind

lsClient = LaserMind(pathToRefreshTokenFile="C:\\path\\to\\your\\token.txt", logToConsole=True)

H = np.array([
    [0+0j, 1-0.5j],
    [1+0.5j, 0+0j]
], dtype=np.complex64)

result = lsClient.solve_coupling_matrix_sim_lpu(
    matrix_data=H,
    num_runs=1,
    num_iterations=1000,
    rounds_per_record=50,
    timeout=10,
    waitForSolution=True
)

final_states = result["data"]["result"]["final_states"]     # numpy.complex64, [num_runs, num_lasers]
record_states = result["data"]["result"]["record_states"]   # numpy.complex64, [num_records, num_runs, num_lasers]
Error model
On failure, a top-level error: string is returned (no data).
Common causes include invalid credentials, non-square or wrong-typed matrix_data, conflicting initial-state settings, exceeding spin limits, or service availability.
