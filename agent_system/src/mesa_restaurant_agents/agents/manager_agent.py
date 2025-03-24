from ..utils.order_status import OrderStatus, food_options
from ..agents.customer_agent import CustomerAgent
from ..agents.waiter_agent import WaiterAgent
from ..utils.schedule_optimizer import ScheduleOptimizer
from ..utils.waiter_definfitions import WaiterDefinition


import mesa
import numpy as np

class ManagerAgent(mesa.Agent):
    def __init__(self, model):
        super().__init__(model)
        # Initialize manager properties
        #self.food_inventory = {option: 100 for option in food_options}  # Initial stock
        # Track daily statistics
        #self.daily_stats = {
        #    'total_customers': 0,        # Total customers in restaurant
        #    'avg_waiting_time': 0,       # Average customer waiting time
        #    'active_waiters': 0,         # Number of available waiters
        #    'profit': 0                  # Daily profit
        #}

        # Initialize schedule optimizer# Initialize optimizer
        self.schedule_optimizer = ScheduleOptimizer()

        # Essential properties from WaiterDefinition
        self.shifts = WaiterDefinition.SHIFTS
        self.fulltime_waiters = WaiterDefinition.get_fulltime_waiters()
        self.parttime_waiters = WaiterDefinition.get_parttime_waiters()
        self.eligible_waiters = WaiterDefinition.ELIGIBLE_WAITERS_BY_SHIFT

        # For storing the current schedule state
        self.predicted_customers = {shift: 0 for shift in self.shifts}
        self.waiters_assigned_count = {shift: 0 for shift in self.shifts}
        self.schedule = {1: [], 2: [], 3: []}

        # Add some default waiters to ensure shifts have coverage on first day
        for shift in range(1, 4):
            for i in range(1, 3):  # Add 2 waiters per shift
                waiter_id = f"waiter_{shift}_{i}"
                self.schedule[shift].append(waiter_id)

    def step(self):
        # Update daily statistics
        #self.daily_stats['total_customers'] = len(self.model.agents.select(agent_type=CustomerAgent))
        #self.daily_stats['active_waiters'] = len([w for w in self.model.agents.select(agent_type=WaiterAgent)])
        #self.daily_stats['avg_waiting_time'] = int(round(np.mean([c.waiting_time for c in self.model.agents.select(agent_type=CustomerAgent)] or [0])))
        #self.calculate_profit()

        # Daily scheduling and predictions (at restaurant opening)
        if self.model.current_minute == self.model.opening_hour:
            # Ensure we have a schedule for today
            if all(len(waiters) == 0 for waiters in self.schedule.values()):
                self._optimize_schedule_for_day()

            # Print prediction information for the day
            #print(f"Predicted customers per shift: {self.predicted_customers}")
            #print(f"Waiters assigned per shift: {self.waiters_assigned_count}")

            # Print detailed schedule information
            for shift in self.shifts:
                waiters_in_shift = self.schedule.get(shift, [])
                #print(f"Shift {shift}: {', '.join(waiters_in_shift)}")

        # At end of day, update training data with actual customer counts
        if self.model.current_minute >= self.model.closing_hour - self.model.time_step:
            # Use actual shift data instead of placeholder
            actual_data = [
                self.model.shift_customers[1],
                self.model.shift_customers[2],
                self.model.shift_customers[3]
                ]

            # Process actual data to improve predictions
            updated_predictions = self.schedule_optimizer.process_actual_data(actual_data)
            self.predicted_customers = updated_predictions
            #print(f"Updated predictions after processing actual data: {self.predicted_customers}")

            # Optimize the schedule for the next day
            self._optimize_schedule_for_day()

            #print(f"Applying optimized schedule for next day")
            #print(f"Predicted customers: {self.predicted_customers}")
            #print(f"Waiters per shift: {self.waiters_assigned_count}")

            # Reset shift counters for next day
            self.model.shift_customers = {1: 0, 2: 0, 3: 0}

    def _optimize_schedule_for_day(self):
        """Create an optimized schedule for the day"""
        # Use actual shift data or default values
        waiter_vars = {}
        waiter_availability = {waiter: True for waiter in self.fulltime_waiters + self.parttime_waiters}

        # If we have no prediction yet, use default values
        if all(count == 0 for count in self.predicted_customers.values()):
            self.predicted_customers = {1: 30, 2: 40, 3: 20}  # Default predictions

        # Solve the scheduling problem
        pyoptmodel = self.schedule_optimizer.solve_scheduling_problem(
            waiter_vars=waiter_vars,
            waiter_availability=waiter_availability,
            predicted_demand=self.predicted_customers,
            fulltime_waiters=self.fulltime_waiters,
            parttime_waiters=self.parttime_waiters
        )

        # Extract schedule from model solution
        self.schedule = {shift: [] for shift in [1, 2, 3]}
        for var_name, var in waiter_vars.items():
            if pyoptmodel.get_value(var) > 0.5:
                waiter_id, shift = var_name.rsplit('_', 1)
                self.schedule[int(shift)].append(waiter_id)

        # Ensure each shift has at least one waiter
        for shift in [1, 2, 3]:
            if not self.schedule[shift]:
                self.schedule[shift].append(f"default_waiter_{shift}")

        # Update the waiters assigned count
        self.waiters_assigned_count = {
            shift: len(waiters) for shift, waiters in self.schedule.items()
        }

        # Print the schedule information
        print(f"Optimized schedule for day {self.model.current_day}:")
        for shift, waiters in self.schedule.items():
            print(f"Shift {shift}: {', '.join(waiters)} ({len(waiters)} waiters)")

    # def order_food(self, food_type, amount):
    #     # Replenish food inventory
    #     self.food_inventory[food_type] += amount

    # def calculate_profit(self):
    #     # Calculate revenue from customer bills and tips
    #     # Calculate daily profit considering various costs
    #     total_sales = sum(w.tips for w in self.model.agents.select(agent_type=WaiterAgent))

    #     # Calculate costs
    #     staff_costs = len(self.model.agents.select(agent_type=WaiterAgent)) * 10  # Fixed cost per waiter
    #     food_costs = sum(100 - amount for amount in self.food_inventory.values())

    #     # Update profit
    #     #self.daily_stats['profit'] = total_sales - (staff_costs + food_costs)