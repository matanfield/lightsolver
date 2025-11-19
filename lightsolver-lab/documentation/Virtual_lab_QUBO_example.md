Virtual Lab – QUBO Example
Quadratic Unconstrained Binary Optimization (QUBO) is a mathematical formulation used to represent optimization problems. In general, it’s expressed as:

  
 
 

where:

 are binary variables 
,
 are linear coefficients,
 are quadratic coefficients.
The coupling matrix 
 in the emulator can be derived from the QUBO problem’s coefficients. Each element of the matrix corresponds to the interaction between variables 
 and 
:

Diagonal elements represent the linear terms (
).
Off-diagonal elements represent the quadratic terms (
).
Let’s have a look at the problem presented in our demo [link]:

Python
# Example: Constructing the coupling matrix for the QUBO problem
import numpy as np
import ? [fill appropriate libray / function]

# Define QUBO coefficients
Q = np.array([[ -4, 4, 0, 0, 0],
[ 4, -8, 4, 0, 0],
[ 0, 4, -12, 4, 4],
[ 0, 0, 4, -4, 0],
[ 0, 0, 4, 0, -4]])
offset_QUBO = 8

# The corresponding Ising matrix:
I, offset_Ising = probmat_qubo_to_ising(Q, offset_QUBO)

print('Ising matrix:')
print(I)
print('Ising offset: ', offset_Ising)
# Example: Constructing the coupling matrix for the QUBO problem
import numpy as np
import ? [fill appropriate libray / function]

# Define QUBO coefficients
Q = np.array([[ -4,   4,   0,   0,   0],
              [  4,  -8,   4,   0,   0],
              [  0,   4, -12,   4,   4],
              [  0,   0,   4,  -4,   0],
              [  0,   0,   4,   0,  -4]])
offset_QUBO = 8

# The corresponding Ising matrix:
I, offset_Ising = probmat_qubo_to_ising(Q, offset_QUBO)

print('Ising matrix:')
print(I)
print('Ising offset: ', offset_Ising)


In the Ising formulation our variables are transformed from 
 to 
 via:


Which results in the following Ising matrix (offset_ising = 0):

Python
I = np.array([[0., 1., 0., 0., 0.],
[1., 0., 1., 0., 0.],
[0., 1., 0., 1., 1.],
[0., 0., 1., 0., 0.],
[0., 0., 1., 0., 0.]])
I = np.array([[0., 1., 0., 0., 0.],
              [1., 0., 1., 0., 0.],
              [0., 1., 0., 1., 1.],
              [0., 0., 1., 0., 0.],
              [0., 0., 1., 0., 0.]])
Now that we have our problem in its Ising formulation, we can construct the coupling matrix we will use in our emulator. In the coupling matrix, the diagonal is the self-coupling of each laser and the off-diagonal elements are the cross interactions with its counterparts. As such, we need to make sure that the sum of the absolute value of each row in the coupling matrix doesn’t exceed the value of 1. Our function does exactly that:

Python
coupling_matrix = coupling_matrix_xy(I, XYmodelParams())

print('Coupling Matrix:')
print(coupling_matrix)

# make sure that the sum of the absolute value of each row < 1:
row_sums = np.abs(coupling_matrix).sum(axis=0)
is_smaller_than_one = (row_sums < 1).all()
print('sums are smaller than one:', is_smaller_than_one)
coupling_matrix = coupling_matrix_xy(I, XYmodelParams())

print('Coupling Matrix:')
print(coupling_matrix)

# make sure that the sum of the absolute value of each row < 1:
row_sums = np.abs(coupling_matrix).sum(axis=0)
is_smaller_than_one = (row_sums < 1).all()
print('sums are smaller than one:', is_smaller_than_one)
What are the XYmodelParams()?

alphaI – lasers self coupling strength – default: 0.7
coupAmp – Coupling amplitude, default: 0.3
The hyper-parameters, alpha_I and coupAmp, can (and should) be optimized per problem. For instance, if you play around with these parameters, you will notice that ‘too small’ values of self coupling (the exact definition of ‘too small’ depends on the problem at hand) will cause the lasers to eventually ‘die’ – zero amplitude.

Notice that the coupling matrix needs to be complex and symmetric.

Now that we have the coupling matrix, let’s try and solve the problem using the emulator:

Python
from laser_mind_client import LaserMind

lsClient = LaserMind(user_token) # insert your own USER_TOKEN
result = lsClient.solve_coupling_matrix_sim_lpu(matrix_data=coupling_matrix.astype(np.complex64), num_runs=10, num_iterations=1000, rounds_per_record=1)

start_states = result['data']['result']['start_states'] # dims: num_runs x num_lasers
final_states = result['data']['result']['final_states'] # dims: num_runs x num_lasers
final_gains = result['data']['result']['final_gains'] # dims: num_runs x num_lasers
record_states = result['data']['result']['record_states'] # dims: num_records x num_runs x num_lasers
record_gains = result['data']['result']['record_gains'] # dims: num_records x num_runs x num_lasers

# grabbing just one of the runs, for all lasers, every iteration:
outWave = record_states[:, 0, :] # iterations x lasers (since rounds_per_record = 1)

from laser_mind_client import LaserMind 

lsClient = LaserMind(user_token)    # insert your own USER_TOKEN
result = lsClient.solve_coupling_matrix_sim_lpu(matrix_data=coupling_matrix.astype(np.complex64), num_runs=10, num_iterations=1000, rounds_per_record=1)

start_states = result['data']['result']['start_states']     # dims: num_runs x num_lasers
final_states = result['data']['result']['final_states']     # dims: num_runs x num_lasers 
final_gains = result['data']['result']['final_gains']       # dims: num_runs x num_lasers
record_states = result['data']['result']['record_states']   # dims: num_records x num_runs x num_lasers
record_gains = result['data']['result']['record_gains']     # dims: num_records x num_runs x num_lasers

# grabbing just one of the runs, for all lasers, every iteration:
outWave = record_states[:, 0, :]    # iterations x lasers (since rounds_per_record = 1)
If we’d like to visualize the result, we can look at the phases and amplitudes of one of the initial states over the iteration number:

Python
# if needed: pip install plotly
import plotly.graph_objects as go
import plotly.express as px

def generateAnimation(outWave, save=False):

# Number of frames in the animation
num_frames = outWave.shape[0]
color_scale = px.colors.qualitative.Set1[:outWave.shape[1]]

fig = go.Figure()

# Create text for the polar plot
N = outWave.shape[1]
text = [str(int(a)) for a in np.linspace(1, N, num=N, endpoint=True)]

# Create data for the initial frame
theta = np.angle(outWave[0, :]) * 180 / np.pi
radius = np.abs(outWave[0, :])
initial_frame_data = [go.Scatterpolar(r=radius, theta=theta, mode='markers+text', marker=dict(size=10, color=color_scale), text=text, textposition='top center', showlegend=False),
]

# Create the layout
layout = go.Layout(
showlegend=False,
polar=dict(radialaxis=dict(visible=True)),
)

# Create the figure with the initial frame
fig.add_trace(initial_frame_data[0]) # Add the initial trace
fig.update_layout(layout)
fig.update_xaxes(title_text="iteration")
fig.update_layout(showlegend=True)

# Define animation frames
animation_frames = []

for i in range(1, num_frames):
theta = np.angle(outWave[i, :]) * 180 / np.pi
r_values = np.abs(outWave[i, :])
frame_data = [go.Scatterpolar(r=r_values, theta=theta, mode='markers+text', marker=dict(size=10, color=color_scale), name='polar plot', text=text, textposition='top center', showlegend=False),
]
animation_frames.append(go.Frame(data=frame_data, name=f"frame_{i}"))

# Add frames to the figure
fig.frames = animation_frames

# Define animation options
animation_opts = dict(
frame=dict(duration=500, redraw=True),
fromcurrent=True
)

# Add play button
fig.update_layout(
updatemenus=[
{
'buttons': [
{
'args': [None, {'frame': {'duration': 500, 'redraw': True}, 'fromcurrent': True}],
'label': 'Play',
'method': 'animate'
},
{
'args': [[None], {'frame': {'duration': 0, 'redraw': True}, 'mode': 'immediate', 'transition': {'duration': 0}}],
'label': 'Pause',
'method': 'animate'
}
],
'direction': 'left',
'pad': {'r': 10, 't': 87},
'showactive': False,
'type': 'buttons',
'x': 0.1,
'xanchor': 'right',
'y': 0.2,
'yanchor': 'top'
}
],
template= "seaborn" # "plotly_dark"
)

# Define slider steps
steps = []
for i in range(num_frames):
step = dict(
method="animate",
args=[
[f"frame_{i}"],
dict(
mode="immediate",
frame=dict(duration=300, redraw=True),
transition=dict(duration=0)
),
],
label=str(i)
)
steps.append(step)

# Add slider to layout
fig.update_layout(
sliders=[dict(
active=0,
currentvalue={"prefix": "Frame: "},
pad={"t": 50},
steps=steps
)]
)

fig.update_layout(
polar=dict(
radialaxis=dict(visible=True)
),
xaxis=dict(domain=[0.65, 1]),
yaxis=dict(domain=[0.65, 1]),
yaxis2=dict(domain=[0, 0.35], anchor='x', overlaying='y', side='right')
)

fig.update_layout(
autosize=False,
width=1200,
height=800,
)
# Display & save the figure
fig.show()
# Save the figure as an HTML file
if save:
fig.write_html('polar_animation.html')
# if needed: pip install plotly
import plotly.graph_objects as go
import plotly.express as px

def generateAnimation(outWave, save=False):

    # Number of frames in the animation
    num_frames = outWave.shape[0]
    color_scale = px.colors.qualitative.Set1[:outWave.shape[1]]

    fig = go.Figure()

    # Create text for the polar plot
    N = outWave.shape[1]
    text = [str(int(a)) for a in np.linspace(1, N, num=N, endpoint=True)]

    # Create data for the initial frame
    theta = np.angle(outWave[0, :]) *  180 / np.pi
    radius = np.abs(outWave[0, :])
    initial_frame_data = [go.Scatterpolar(r=radius, theta=theta, mode='markers+text', marker=dict(size=10, color=color_scale), text=text, textposition='top center', showlegend=False), 
                          ] 

    # Create the layout
    layout = go.Layout(
        showlegend=False,
        polar=dict(radialaxis=dict(visible=True)),
    )

    # Create the figure with the initial frame
    fig.add_trace(initial_frame_data[0])                      # Add the initial trace
    fig.update_layout(layout)            
    fig.update_xaxes(title_text="iteration")
    fig.update_layout(showlegend=True)

    # Define animation frames
    animation_frames = []

    for i in range(1, num_frames):
        theta = np.angle(outWave[i, :]) *  180 / np.pi
        r_values = np.abs(outWave[i, :])
        frame_data = [go.Scatterpolar(r=r_values, theta=theta, mode='markers+text', marker=dict(size=10, color=color_scale), name='polar plot', text=text, textposition='top center', showlegend=False),
                      ]
        animation_frames.append(go.Frame(data=frame_data, name=f"frame_{i}"))
    
    # Add frames to the figure
    fig.frames = animation_frames 

    # Define animation options
    animation_opts = dict(
        frame=dict(duration=500, redraw=True),
        fromcurrent=True
    )

    # Add play button
    fig.update_layout(
        updatemenus=[
            {
                'buttons': [
                    {
                        'args': [None, {'frame': {'duration': 500, 'redraw': True}, 'fromcurrent': True}],
                        'label': 'Play',
                        'method': 'animate'
                    },
                    {
                        'args': [[None], {'frame': {'duration': 0, 'redraw': True}, 'mode': 'immediate', 'transition': {'duration': 0}}],
                        'label': 'Pause',
                        'method': 'animate'
                    }
                ],
                'direction': 'left',
                'pad': {'r': 10, 't': 87},
                'showactive': False,
                'type': 'buttons',
                'x': 0.1,
                'xanchor': 'right',
                'y': 0.2,
                'yanchor': 'top'
            }
        ],
        template= "seaborn" # "plotly_dark"
    )

    # Define slider steps
    steps = []
    for i in range(num_frames):
        step = dict(
            method="animate",
            args=[
                [f"frame_{i}"],
                dict(
                    mode="immediate",
                    frame=dict(duration=300, redraw=True),
                    transition=dict(duration=0)
                ),
            ],
            label=str(i)
        )
        steps.append(step)

    # Add slider to layout
    fig.update_layout(
        sliders=[dict(
            active=0,
            currentvalue={"prefix": "Frame: "},
            pad={"t": 50},
            steps=steps
        )]
    )

    fig.update_layout(
            polar=dict(
                radialaxis=dict(visible=True)
            ),
            xaxis=dict(domain=[0.65, 1]),
            yaxis=dict(domain=[0.65, 1]),
            yaxis2=dict(domain=[0, 0.35], anchor='x', overlaying='y', side='right')
        )

    fig.update_layout(
            autosize=False,
            width=1200,
            height=800,
        )
    # Display & save the figure
    fig.show()
    # Save the figure as an HTML file
    if save:
        fig.write_html('polar_animation.html')
Expand
The code above will generate the following animation:


The steady state of the dynamics is:


How is this the solution? In this model, the solution is extracted from the phases of the steady-state reached by the system. We are looking for the optimal cut, that separates the phases in the polar coordinate system into two groups. It’s optimal in the sense that it minimizes the expression in equation (1). We’ll use our best_enregy_search_xy function:

Python
# search for the best state:
best_state, best_energy = best_energy_search_xy(outWave[:, 0, -1], I)

# transform Ising best state to QUBO best state:
QUBO_best_state = (best_state + 1) / 2

print('QUBO best state: ', QUBO_best_state)
# search for the best state:
best_state, best_energy = best_energy_search_xy(outWave[:, 0, -1], I)     

# transform Ising best state to QUBO best state:
QUBO_best_state = (best_state + 1) / 2

print('QUBO best state: ', QUBO_best_state)
The solution we recieve is the expected result (see demo):

Python
> array([0., 1., 0., 1., 1.])
> array([0., 1., 0., 1., 1.])
An illustration of the ‘cut’ that produced this result:


