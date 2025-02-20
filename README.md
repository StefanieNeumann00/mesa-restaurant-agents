# mesa-restaurant-agents

A Mesa-based restaurant simulation that models customer, waiter, and manager interactions in a restaurant environment.

## Description

This project simulates a restaurant environment using the Mesa agent-based modeling framework. The simulation includes:

- Multiple agent types (customers, waiters, managers)
- Time-based customer arrivals with peak hour variations
- Order processing and table management
- Customer satisfaction tracking
- Financial metrics collection

## Build project
 
* Navigate to directory containing pyproject.toml (agents_system/)
* Execute `python -m build`
* Restart kernel
* Install build package with `pip install --force-reinstall <dir to whl file>.whl` (The whl-file is created in the dist/ folder)

## Installation

```bash
pip install mesa-restaurant-agents# mesa-restaurant-agents
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
Basic example of running the simulation:

```python
from mesa_restaurant_agents.model import RestaurantModel

# Create model with 50 customers and 5 waiters
model = RestaurantModel(n_customers=50, n_waiters=5)

# Run the simulation
while model.running:
    model.step()

# Access collected data
data = model.datacollector.get_model_vars_dataframe()
```

## Features
* Dynamic arrival rates based on time (11:00-23:00)
* 100 tables with customer management
* Food options: vegetarian, meat, gluten-free
* Order status tracking
* Customer satisfaction metrics
* Financial tracking and profit calculation

## License
MIT License EOL