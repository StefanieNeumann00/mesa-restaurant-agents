from ..utils.order_status import OrderStatus, food_options
from ..agents.customer_agent import CustomerAgent
from ..agents.waiter_agent import WaiterAgent
from ..utils.schedule_optimizer import ScheduleOptimizer

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

        # Initialize schedule optimizer# Initialize optimizer
        self.schedule_optimizer = ScheduleOptimizer()
        self.shifts = [1, 2, 3]
        self.predicted_customers = {shift: 0 for shift in self.shifts}
        self.waiters_per_shift = {shift: 0 for shift in self.shifts}
        self.schedule = {}  # Initialize empty schedule

    def step(self):
        # Update daily statistics
        model = self.model
        self.daily_stats['total_customers'] = len(model.agents.select(agent_type=CustomerAgent))
        self.daily_stats['active_waiters'] = len([w for w in model.agents.select(agent_type=WaiterAgent)])
        self.daily_stats['avg_waiting_time'] = np.mean([c.waiting_time for c in model.agents.select(agent_type=CustomerAgent)])
        self.calculate_profit()

        # Daily scheduling and predictions (at restaurant opening)
        if model.current_minute == model.opening_hour:
            # Reset availability for all waiters
            for waiter in model.agents.select(agent_type=WaiterAgent):
                waiter.reset_availability()

            # Print available waiters for the day
            available_waiters = [f"Waiter {w.unique_id}" for w in model.agents.select(agent_type=WaiterAgent) if
                                 w.is_available]
            print(f"Available waiters for the day: {', '.join(available_waiters)}")

            # Predict customer demand for today
            self.predicted_customers = self.schedule_optimizer.predict_customer_demand()
            print(f"Predicted customers per shift: {self.predicted_customers}")

            # Create schedule for today's waiters
            waiters = model.agents.select(agent_type=WaiterAgent)
            self.schedule, self.waiters_per_shift = self.schedule_optimizer.create_waiter_schedule(
                waiters, self.predicted_customers
            )
            print(f"Waiters assigned per shift: {self.waiters_per_shift}")

        # At end of day, update training data with actual customer counts
        if self.model.current_minute >= self.model.closing_hour - self.model.time_step:
            # Use actual shift data instead of placeholder
            actual_data = [
                model.shift_customers[1],
                model.shift_customers[2],
                model.shift_customers[3]
            ]

            updated_predictions = self.schedule_optimizer.process_actual_data(actual_data)
            self.predicted_customers = updated_predictions

            # Reset shift counters for next day
            self.model.shift_customers = {1: 0, 2: 0, 3: 0}

            # Update consecutive days worked for waiters
            for waiter in model.agents.select(agent_type=WaiterAgent):
                if waiter.unique_id in [w.unique_id for shift_waiters in self.schedule.values() for w in shift_waiters]:
                    waiter.consecutive_days_worked += 1
                else:
                    waiter.consecutive_days_worked = 0

    def order_food(self, food_type, amount):
        # Replenish food inventory
        self.food_inventory[food_type] += amount

    def calculate_profit(self):
        # Calculate revenue from customer bills and tips
        # Calculate daily profit considering various costs
        total_sales = sum(w.tips for w in self.model.agents.select(agent_type=WaiterAgent))

        # Calculate costs
        staff_costs = len(self.model.agents.select(agent_type=WaiterAgent)) * 10  # Fixed cost per waiter
        food_costs = sum(100 - amount for amount in self.food_inventory.values())

        # Update profit
        self.daily_stats['profit'] = total_sales - (staff_costs + food_costs)