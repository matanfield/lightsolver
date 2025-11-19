####################################################################################################
# This example connects to the LightSolver Cloud using the LaserMind client and retrieves account details.
# The `get_account_details` method fetches information such as username, spin limit, expiration date, and credits.
####################################################################################################

import os
from laser_mind_client import LaserMind

pathToTokenFile = os.path.join(os.path.dirname(__file__), "lightsolver-token.txt")

# Connect to the LightSolver Cloud
lsClient = LaserMind(pathToRefreshTokenFile=pathToTokenFile)

res = lsClient.get_account_details()

assert 'username' in res
assert 'dlpu_spin_limit' in res
assert 'expiration_date' in res
assert 'dlpu_credit_seconds' in res

print(f"Test PASSED, response is: \n{res}")