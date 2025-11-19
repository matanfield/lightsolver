Common API Spec
This document describes the functions exposed by the LaserMind client that are common to both virtual and physical labs:

get_solution_sync
get_account_details
All examples assume you already installed the client and have your token file as described in LightSolver Lab Installation Guide.

Client setup
Python
from laser_mind_client import LaserMind
lsClient = LaserMind(pathToRefreshTokenFile="C:\\path\\to\\your\\token.txt", logToConsole=True)
from laser_mind_client import LaserMind
lsClient = LaserMind(pathToRefreshTokenFile="C:\\path\\to\\your\\token.txt", logToConsole=True)
get_solution_sync
Purpose: Retrieve a solution previously submitted with any solver when you called a solve method with waitForSolution=False. Polls until the solution is ready or a timeout occurs.
Input dictionary
requestInfo: dictionary
id: string
The request ID returned by the solve call.
reqTime: string
The request time string (“DD-MM-YYYY-HH-MM-SS-microseconds”) returned by the solve call.
receivedTime: string
The server receive-time string returned by the solve call.
You pass this dictionary exactly as returned by the solve method.

Return dictionary
A solution envelope with common fields and a solver-specific payload:

serviceCommandName: string
The solver identifier (“SIMLPU”, “LPU”)
data: dictionary
Solver-specific result dictionary. See the relevant solver spec for a full schema:
Virtual Lab API Spec
Physical Lab API Spec
creationTime: string
“DD-MM-YYYY-HH-MM-SS-microseconds”
reqTime: string
reqId: string
userId: string
receivedTime: string
Errors:

On failure, the client raises an exception rather than returning a dictionary with an error field.
Example (asynchronous flow):

Python
# Submit a job with waitForSolution=False using any solver; get a requestInfo dict back
req = lsClient.solve_qubo_lpu(matrixData=..., num_runs=2, waitForSolution=False)

# Later, retrieve the solution; this request will block until the solution is ready
solution = lsClient.get_solution_sync(req)
print(solution["serviceCommandName"])
print(solution["data"]) # Payload shape depends on the solver you used
# Submit a job with waitForSolution=False using any solver; get a requestInfo dict back
req = lsClient.solve_qubo_lpu(matrixData=..., num_runs=2, waitForSolution=False)

# Later, retrieve the solution; this request will block until the solution is ready
solution = lsClient.get_solution_sync(req)
print(solution["serviceCommandName"])
print(solution["data"])  # Payload shape depends on the solver you used
get_account_details
Purpose: Retrieve account information such as spin limits and credit/expiration information for your user.
Note: LightSolver Lab is currently in early access; approved customers have virtually endless credit (solve time) at this stage.
Input
None. Just call the method.
Return dictionary
username: string
Your account email.
dlpu_spin_limit: integer
Maximum allowed problem size (in spins/variables) for relevant solvers under your account.
expiration_date: string
Human-readable expiration date for credits or license.
dlpu_credit_seconds: number | string
Remaining credit time in seconds.
Example:

Python
info = lsClient.get_account_details()
print(info["username"]) # string
print(info["dlpu_spin_limit"]) # int
print(info["expiration_date"]) # string, e.g., "Mon Jan 1 12:34:56 2025"
print(info["dlpu_credit_seconds"]) # number or "Unlimited"
info = lsClient.get_account_details()
print(info["username"])             # string
print(info["dlpu_spin_limit"])      # int
print(info["expiration_date"])      # string, e.g., "Mon Jan  1 12:34:56 2025"
print(info["dlpu_credit_seconds"])  # number or "Unlimited"
