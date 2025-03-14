import mesa
import numpy as np

from ..agents.customer_agent import CustomerAgent
from ..agents.manager_agent import ManagerAgent
from ..agents.waiter_agent import WaiterAgent
from ..utils.kitchen import Kitchen
from ..utils.restaurant_grid import RestaurantGrid


class RestaurantModel(mesa.Model):
    def __init__(self, n_waiters, grid_width, grid_height, seed=None):
        super().__init__(seed=seed)

        self.grid_height = grid_height if grid_height % 2 != 0 else grid_height + 1  # make sure grid_height is uneven
        self.grid_width = grid_width if grid_width % 2 != 0 else grid_width + 1  # make sure grid_width is uneven
        # self.grid = mesa.space.SingleGrid(self.grid_width, self.grid_height, True)

        # Set up environment
        kitchen_x = (self.grid_width // 2) + 2 if self.grid_width % 2 == 1 else (self.grid_width // 2) + 2
        kitchen_y = (self.grid_width // 2) + 2 if self.grid_height % 2 == 1 else (self.grid_height // 2) + 2
        self.kitchen = Kitchen(pos=(kitchen_x, kitchen_y))
        self.grid = RestaurantGrid(self.grid_width, self.grid_height, self.kitchen.pos)

        # Initialize tracking variables
        self.profit = 0
        self.customers_paid = 0
        self.customers_left_without_paying = 0
        self.customer_count = 0
        self.daily_customers = []
        self.kitchen_access = None  # Track which waiter has kitchen access

        # Time settings
        self.opening_hour = 11 * 60
        self.closing_hour = 23 * 60
        self.time_step = 5
        self.current_minute = self.opening_hour

        # Add day tracking
        self.current_day = 1
        self.daily_records = []  # For storing metrics across days

        # Define shifts by time ranges (in minutes)
        self.shifts = {
            1: {"name": "Morning", "start": 11 * 60, "end": 15 * 60},  # 11am-3pm
            2: {"name": "Afternoon", "start": 15 * 60, "end": 19 * 60},  # 3pm-7pm
            3: {"name": "Evening", "start": 19 * 60, "end": 23 * 60}  # 7pm-11pm
        }

        # Track customers by shift
        self.shift_customers = {1: 0, 2: 0, 3: 0}

        # Debugging
        print(f"Step {self.current_minute}, Profit: {self.profit}")
        print(f"Active customers: {len(self.agents.select(agent_type=CustomerAgent))}")

        # Create agents after environment setup
        WaiterAgent.create_agents(model=self, n=n_waiters)

        # Create waiter agents with assignment of fulltime/part-time
        fulltime_count = max(1, n_waiters // 2)  # At least 1 fulltime waiter
        part_time_count = n_waiters - fulltime_count

        # Create fulltime waiters
        for i in range(fulltime_count):
            waiter = WaiterAgent(self)
            waiter.is_fulltime = True
            self.agents.add(waiter)

        # Create part-time waiters
        for i in range(part_time_count):
            waiter = WaiterAgent(self)
            waiter.is_fulltime = False
            self.agents.add(waiter)

        self.position(self.agents)

        # Create manager
        manager = ManagerAgent(self)
        self.agents.add(manager)

        # Set up model parameters
        self.n_waiters = n_waiters
        self.width = grid_width
        self.height = grid_height

        # Set up data collection for model metrics
        self.datacollector = mesa.DataCollector(
            model_reporters={
                "Customer_Count": lambda m: self.get_customers_count(m.agents),
                "Average_Wait_Time": lambda m: np.mean(
                    [c.waiting_time for c in m.agents.select(agent_type=CustomerAgent)]),
                "Average_Customer_Satisfaction": lambda m: np.mean(
                    [c.satisfaction for c in m.agents.select(agent_type=CustomerAgent)]),
                "Profit": lambda m: m.profit,
                "Customer_Info": lambda m: self.get_customer_info(m.agents),
                "Waiter_Info": lambda m: self.get_waiter_info(m.agents),
                "GridState": self._get_grid_state,
            }
        )
        # Collect initial state
        self.datacollector.collect(self)

    def _get_grid_state(self):
        """Return lightweight grid state representation"""
        state = []
        # Add kitchen position
        state.append({
            'pos': self.kitchen.pos,
            'type': 'Kitchen'
        })
        # Add table positions
        for table_pos in self.grid.layout['tables']:
            state.append({
                'pos': table_pos,
                'type': 'Table'
            })

        # Debug the grid structure
        # print("Grid empties:", self.grid.empties)
        # print("Agents count:", len(self.agents))

        for agent in self.agents:
            # print(f"Agent: {type(agent).__name__}, Position: {getattr(agent, 'pos', None)}")
            if hasattr(agent, 'pos') and agent.pos is not None:
                state.append({
                    'pos': agent.pos,
                    'type': type(agent).__name__,
                })
        # print(f"Final state size: {len(state)}")
        return state

    def position(self, agents):
        for agent in agents:
            # Place waiters at the kitchen position
            if isinstance(agent, WaiterAgent):
                self.grid.place_agent(agent, self.kitchen.pos)
            # Position other agent types randomly
            elif not self.grid.position_randomly(agent):
                self.agents.remove(agent)

    def get_customer_info(self, agents):
        customers = agents.select(agent_type=CustomerAgent)
        c_infos = []
        for customer in customers:
            c_info = {"customer_nr": customer.unique_id,
                      "waiting_time": customer.waiting_time,
                      "order_status": customer.order_status.value,
                      "satisfaction": customer.satisfaction}
            c_infos.append(c_info)
        return c_infos

    def get_waiter_info(self, agents):
        waiters = agents.select(agent_type=WaiterAgent)
        w_infos = []
        for waiter in waiters:
            w_info = {"waiter_nr": waiter.unique_id,
                      "tips": waiter.tips,
                      "avg_rating": waiter.avg_rating,
                      "served_customers": waiter.served_customers}
            w_infos.append(w_info)
        return w_infos

    def reserve_kitchen_access(self, agent):
        """Reserve exclusive access to the kitchen for an agent"""
        if self.kitchen_access is None or self.kitchen_access == agent:
            self.kitchen_access = agent
            return True
        return False

    def release_kitchen_access(self, agent):
        """Release kitchen access when agent leaves"""
        if self.kitchen_access == agent:
            self.kitchen_access = None

    def get_customers_count(self, agents):
        return len(agents.select(agent_type=CustomerAgent))

    def is_peak_hour(self):
        """Check if current time is during peak hours"""
        hour = self.current_minute // 60
        return (12 <= hour <= 14) or (17 <= hour <= 20)

    def calculate_new_customers(self):
        """Calculate number of new customers based on time of day"""
        base_rate = 1  # Base arrival rate (non-peak)
        if self.is_peak_hour():
            base_rate = 8  # Increased arrival rate during peak hours
        return np.random.poisson(base_rate)  # Random variation in arrivals

    def add_new_customers(self):
        n_new = self.calculate_new_customers()

        # Determine current shift
        current_shift = None
        for shift_id, shift_info in self.shifts.items():
            if shift_info["start"] <= self.current_minute < shift_info["end"]:
                current_shift = shift_id
                break

        for _ in range(n_new):
            customer = CustomerAgent(model=self)
            customer.order_time = self.current_minute
            self.agents.add(customer)
            self.grid.position_randomly(customer)  # Use direct grid positioning
            self.kitchen.add_new_customer_order(customer, customer.food_preference, customer.order_time)

            # Track customer by shift
            if current_shift:
                self.shift_customers[current_shift] += 1

    def remove_customer(self, customer):
        """Remove customer from restaurant tracking"""
        if customer in self.agents.select(agent_type=CustomerAgent):
            self.grid.remove_agent(customer)
            self.agents.remove(customer)

    def get_average_wait_time(self):
        """Calculate average wait time safely"""
        customers = self.agents.select(agent_type=CustomerAgent)
        if not customers:
            return 0.0
        return sum(c.waiting_time for c in customers) / len(customers)

    def get_average_satisfaction(self):
        """Calculate average satisfaction safely"""
        customers = self.agents.select(agent_type=CustomerAgent)
        if not customers:
            return 100.0
        return sum(c.satisfaction for c in customers) / len(customers)

    def get_total_profit(self):
        """Calculate total profit safely"""
        managers = self.agents.select(agent_type=ManagerAgent)
        if not managers:
            return 0.0
        return sum(m.daily_stats.get('profit', 0) for m in managers)

    def reset_for_new_day(self):
        """Reset restaurant state for a new day while preserving persistent data"""
        # Store daily stats before resetting
        self.daily_records.append({
            'day': self.current_day,
            'customers_paid': self.customers_paid,
            'customers_left': self.customers_left_without_paying,
            'profit': self.profit,
            'avg_satisfaction': self.get_average_satisfaction()
        })

        print(f"DEBUG: Day {self.current_day} completed, resetting for day {self.current_day + 1}")
        print(f"DEBUG: Before reset - current_minute: {self.current_minute}")

        # After counters are reset but before advancing day, apply the manager's optimized schedule
        manager = self.agents.select(agent_type=ManagerAgent)
        if manager:
            manager = manager[0]
            # Apply the manager's optimized schedule for the new day
            print(f"Applying optimized schedule for day {self.current_day + 1}")
            print(f"Predicted customers: {manager.predicted_customers}")
            print(f"Waiters per shift: {manager.waiters_assigned_count}")

        # Reset time to opening hour
        self.current_minute = self.opening_hour

        # Reset daily counters
        self.customers_paid = 0
        self.customers_left_without_paying = 0
        self.profit = 0

        # Reset kitchen orders
        self.kitchen.requested_orders.clear()
        self.kitchen.prepared_orders.clear()

        # Reset shift customer counts
        self.shift_customers = {1: 0, 2: 0, 3: 0}

        # Remove any remaining customers from previous day
        customers_to_remove = self.agents.select(agent_type=CustomerAgent)
        for customer in customers_to_remove:
            self.grid.remove_agent(customer)
            self.agents.remove(customer)

        # Reset waiters' daily assignments
        for waiter in self.agents.select(agent_type=WaiterAgent):
            waiter.current_customer = None
            waiter.has_order_to_deliver = False

            # Reset position to kitchen
            self.grid.move_agent(waiter, self.kitchen.pos)

        # Advance day counter
        self.current_day += 1

        # Reset running flag
        self.running = True

        print(f"DEBUG: After reset - current_minute: {self.current_minute}, day: {self.current_day}")
        print(f"DEBUG: Opening hour: {self.opening_hour}, Closing hour: {self.closing_hour}")

    def step(self):
        """Advance simulation by one time step"""
        self.current_minute += self.time_step

        # print(f"DEBUG: After reset - current_minute: {self.current_minute}, day: {self.current_day}")
        # print(f"DEBUG: Opening hour: {self.opening_hour}, Closing hour: {self.closing_hour}")

        # Debug customer generation attempts
        if self.opening_hour <= self.current_minute < self.closing_hour:
            self.add_new_customers()

        if self.current_minute % 60 == 0:  # Print stats every hour
            print(f"Day {self.current_day}, Hour {(self.current_minute // 60) % 12 or 12}:")
            print(f"Hour {self.current_minute // 60}:")
            print(f"Customers paid: {self.customers_paid}")
            print(f"Customers left without paying: {self.customers_left_without_paying}")
            print(f"Current profit: ${self.profit:.2f}\n")

        # Process kitchen orders
        self.kitchen.add_ready_orders_to_prepared(self.current_minute)

        # Update all agents EXCEPT the manager at end of day
        # This prevents the manager's step from being called twice
        if self.current_minute >= self.closing_hour - self.time_step:
            agents_copy = list(self.agents)
            for agent in agents_copy:
                if not isinstance(agent, ManagerAgent):
                    agent.step()
        else:
            self.agents.shuffle_do("step")

        # Process manager at end of day explicitly so it happens AFTER all customer data is collected
        if self.current_minute >= self.closing_hour - self.time_step:
            manager = next(iter(self.agents.select(agent_type=ManagerAgent)), None)
            if manager:
                # Skip redundant manager step call if we're about to transition days
                if not (self.multi_day_mode and self.current_minute >= self.closing_hour):
                    manager.step()  # Run manager's end of day processing

        # Handle day transition ONLY when day actually ends
        if hasattr(self, 'multi_day_mode') and self.multi_day_mode and self.current_minute >= self.closing_hour:
            print(f"DEBUG: Day {self.current_day} complete, transitioning to day {self.current_day + 1}")
            self.reset_for_new_day()
            return  # Important: return after reset to avoid multiple resets

        # print(f"Kitchen state: {len(self.kitchen.requested_orders)} requested, "
        #      f"{len(self.kitchen.prepared_orders)} prepared")

        # Update metrics
        self.customer_count = len(self.agents.select(agent_type=CustomerAgent))
        self.datacollector.collect(self)
