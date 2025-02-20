from ..utils.order_status import OrderStatus, food_options
import mesa
import numpy as np

class ManagerAgent(mesa.Agent):
    def __init__(self, model):
        super().__init__(model)
        # Initialize manager properties
        self.food_inventory = {option: 100 for option in food_options}  # Initial stock
        # Track daily statistics
        self.daily_stats = {
            'total_customers': 0,        # Total customers in restaurant
            'avg_waiting_time': 0,       # Average customer waiting time
            'active_waiters': 0,         # Number of available waiters
            'profit': 0                  # Daily profit
        }    

    def step(self):
        # Update daily statistics
        model = self.model
        self.daily_stats['total_customers'] = len(model.customers)
        self.daily_stats['active_waiters'] = len([w for w in model.waiters if not w.busy])
        self.daily_stats['avg_waiting_time'] = np.mean([c.waiting_time for c in model.customers])

    def order_food(self, food_type, amount):
        # Replenish food inventory
        self.food_inventory[food_type] += amount

    def calculate_profit(self):
        # Calculate daily profit considering various costs
        total_sales = sum(w.tips for w in self.model.waiters)
        staff_costs = len(self.model.waiters) * 10  # Fixed cost per waiter
        food_costs = sum(100 - amount for amount in self.food_inventory.values())
        self.daily_stats['profit'] = total_sales - (staff_costs + food_costs)