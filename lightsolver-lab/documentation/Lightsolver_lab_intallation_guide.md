LightSolver Lab Installation Guide
Congratulations on being approved for access to LightSolver Lab!
This guide will walk you through getting started in three simple steps:

Download your API token
Install laser-mind-client, our open-source Python client
Run sample code to confirm your setup
1. Download Your API Token
Click the Download API Token button (available on any page through the navigation bar).
Click the button on the download page.
Save the downloaded file to a safe location—you’ll need it later.
Note: your token will be valid for up to 9 months. Upon expiration, you will be required to download a new token file.

That’s it—your API token is ready.

2. Install the Client
Prerequisites
Windows, Linux, or macOS
Python 3.10-3.12
Note: Python 3.13 or later is not currently supported. An update will soon be released to add this support.
Setup Instructions
Create a new folder for your LightSolver Lab project and navigate into it.
Linux/macOS:
mkdir lightsolver-lab && cd lightsolver-lab
Windows (PowerShell):
mkdir lightsolver-lab; cd lightsolver-lab
Create and activate a virtual environment named .venv.
Linux/macOS:
python3 -m venv .venv
source .venv/bin/activate
Windows (PowerShell):
python -m venv .venv
.venv\Scripts\Activate
Install the client:
pip install laser-mind-client
3. Run Sample Code
Clone the client source code:
git clone https://github.com/LightSolverInternal/laser-mind-client.git
Navigate to the examples folder:
cd laser-mind-client/examples
In the folder explorer, paste the lightsolver-token.txt file from Step 1 into the examples folder. By default, all example scripts expect the token in this path, but you can change the path by editing the pathToTokenFile variable within each script.
For example, in sim_lpu_coupmat.py, edit line #5.
Run the file:
Linux/macOS:
python3 lpu_coupmat.py
Windows (PowerShell):
python lpu_coupmat.py
Congratulations—you’ve just run your first LPU problem using LightSolver Lab!

Next Steps
Updating the Client
LightSolver will occasionally issue mandatory updates. If you are notified about such an update, run:
pip install --upgrade --upgrade-strategy eager laser-mind-client
This ensures both the client and its dependencies are up to date for smooth operation.
Learn More
Explore our documentation:
Virtual Lab API Spec
Physical Lab API Spec
Common API Spec
© Knowledge-lightsolver, 2025. Powered by weDocs plugin for WordPress
https://kb.lightsolver.com