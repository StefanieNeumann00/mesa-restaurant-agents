# mesa-restaurant-agents

A Mesa-based restaurant simulation that models customer, waiter, and manager interactions in a restaurant environment.

## Description

This project simulates a restaurant environment using the Mesa agent-based modeling framework. The simulation includes:

- Multiple agent types (customers, waiters, managers)
- Step-based simulation with configurable parameters
- Pathfinding and movement mechanics for agents
- Grid-based environment with walkways and tables
- Order processing and table management
- Customer satisfaction tracking
- Comprehensive agent metrics collection
- Visualization tools for analysis

## Build project
 
* Navigate to directory containing pyproject.toml (agents_system/)
* Execute `python -m build`
* Restart kernel

## Installation

* Install build package with 
```bash
pip install --force-reinstall <dir to whl file>.whl` (The whl-file is created in the dist/-folder)
```

## Requirements
* Python >= 3.12
* mesa == 3.1.0
* pandas == 2.2.3
* numpy == 2.2.2
* scikit-learn == 1.6.1
* scipy == 1.15.1
* seaborn == 0.13.2
* matplotlib == 3.4.3

## Usage
Example of running a batch simulation:

```python
from mesa_restaurant_agents.model import RestaurantModel
from mesa.batchrunner import batch_run
import pandas as pd

# Define parameters
params = {
    "n_customers": [50],
    "n_waiters": [5]
}

# Run batch simulation
results = batch_run(
    RestaurantModel,
    parameters=params,
    iterations=5,
    max_steps=100
)

# Analyze results
df = pd.DataFrame(results)
```

The `visualization.py` module shows that time-based mechanics have been replaced with step-based logic, and new visualization features have been added.

## Features
* Grid-based environment with designated walkways
* Smart pathfinding for waiters using Manhattan distance
* Multiple visualization options:
  - Agent position heatmaps
  - Step-based performance metrics
  - Customer and waiter statistics
* Batch simulation support for multiple runs
* Customer metrics tracking:
  - Waiting time
  - Order status
  - Satisfaction levels
* Waiter performance metrics:
  - Tips received
  - Average rating
  - Number of customers served
* Financial tracking and profit calculation

## Performance Profiling

The restaurant simulation provides profiling capabilities to analyze performance bottlenecks and execution times. Use the `profile_simulation()` function to generate detailed performance metrics.

### Basic Usage

```python
from mesa_restaurant_agents.model.restaurant_model import RestaurantModel
from mesa_restaurant_agents.profiling import profile_simulation

# Configure simulation parameters
params = {
    "n_waiters": 2,
    "grid_width": 20,
    "grid_height": 20
}

# Profile the simulation
profile_simulation(
    model_class=RestaurantModel,
    params=params,
    steps=15,
    iterations=1
)
```

### Inspecting Profile Results

After running `profile_simulation()`, a `profile_results.prof` file will be generated. You can analyze this file using Python's built-in tools:

#### Using snakeviz (Recommended)
```bash
# Install snakeviz
pip install snakeviz

# View results in browser
snakeviz profile_results.prof
```


## License
MIT License EOL