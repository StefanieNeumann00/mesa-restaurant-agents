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

        self.multi_day_mode = True
        self.grid_height = grid_height if grid_height % 2 != 0 else grid_height + 1  # make sure grid_height is uneven
        self.grid_width = grid_width if grid_width % 2 != 0 else grid_width + 1  # make sure grid_width is uneven

        # Set up environment
        kitchen_x = (self.grid_width // 2) + 2 if self.grid_width % 2 == 1 else (self.grid_width // 2) + 2
        kitchen_y = (self.grid_width // 2) + 2 if self.grid_height % 2 == 1 else (self.grid_height // 2) + 2
        self.kitchen = Kitchen(pos=(kitchen_x, kitchen_y))
        self.grid = RestaurantGrid(self.grid_width, self.grid_height, self.kitchen.pos)

        # Initialize tracking variables
        self.revenue = 0
        self.customers_paid = 0
        self.customers_left_without_paying = 0
        self.customer_count = 0
        self.daily_customers = []
        self.total_orders_served = 0

        # Time settings
        self.opening_hour = 11 * 60
        self.closing_hour = 23 * 60
        self.time_step = 5
        self.current_minute = self.opening_hour

        # Add day tracking
        self.current_day = 1
        self.daily_record = [{}]  # For storing metrics across days

        # Define shifts by time ranges (in minutes)
        self.shifts = {
            1: {"name": "Morning", "start": 11 * 60, "end": 15 * 60},  # 11am-3pm
            2: {"name": "Afternoon", "start": 15 * 60, "end": 19 * 60},  # 3pm-7pm
            3: {"name": "Evening", "start": 19 * 60, "end": 23 * 60}  # 7pm-11pm
        }

        # Track customers by shift
        self.shift_customers = {1: 0, 2: 0, 3: 0}

        # Debugging
        #print(f"Step {self.current_minute}, Revenue: {self.revenue}")
        #print(f"Active customers: {len(self.agents.select(agent_type=CustomerAgent))}")

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
        self.manager = manager

        # Set up model parameters
        self.n_waiters = n_waiters
        self.width = self.grid_width
        self.height = self.grid_height

        # Set up data collection for model metrics
        self.datacollector = mesa.DataCollector(
            model_reporters={
                "day": lambda m: m.current_day,
                "shift": lambda m: m.get_current_shift(),
                "time": lambda m: m.current_minute,
                "Customer_Count": lambda m: m.get_customers_count(m.agents),
                "Waiters_Count": lambda m: m.get_waiters_count(m.agents),
                "Average_Wait_Time": lambda m: m.get_average_wait_time(),
                "Average_Customer_Satisfaction": lambda m: m.get_average_satisfaction(),
                "Revenue": lambda m: m.revenue,
                "Tips": lambda m: m.get_total_tips(),
                "Customer_Info": lambda m: m.get_customer_info(m.agents),
                "Waiter_Info": lambda m: m.get_waiter_info(m.agents),
                "GridState": lambda m: m.get_grid_state(),
                "Daily_Stats": lambda m: m.daily_record,
            }
        )
        # Collect initial state
        self.datacollector.collect(self)

    def get_grid_state(self):
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
                    'nr': agent.unique_id,
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
                      "served_customers": waiter.served_customers}
            w_infos.append(w_info)
        return w_infos

    def get_customers_count(self, agents):
        return len(agents.select(agent_type=CustomerAgent))
    
    def get_waiters_count(self, agents):
        return len(agents.select(agent_type=WaiterAgent))

    def is_peak_hour(self):
        """Check if current time is during peak hours"""
        hour = self.current_minute // 60
        return (12 <= hour <= 14) or (17 <= hour <= 20)

    def calculate_new_customers(self):
        """Calculate number of new customers based on time of day"""
        base_rate = 0.8  # Base arrival rate (non-peak)
        if self.is_peak_hour():
            base_rate = 6  # Increased arrival rate during peak hours
        return np.random.poisson(base_rate)  # Random variation in arrivals

    def get_current_shift(self):
        current_shift = None
        for shift_id, shift_info in self.shifts.items():
            if shift_info["start"] <= self.current_minute < shift_info["end"]:
                current_shift = shift_id
                break
        return current_shift

    def add_new_customers(self):
        n_new = self.calculate_new_customers()

        # Determine current shift
        current_shift = self.get_current_shift()

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

    def reset_for_new_day(self):
        """Reset restaurant state for a new day while preserving persistent data"""
        # Calculate additional stats
        stats = self.get_daily_stats()

        # Print revenue report
        print(f"===== Day {self.current_day} Revenue Report =====")
        print(f"Food revenue: ${stats['food_revenue']:.2f}")
        print(f"Tips collected: ${stats['tips']:.2f}")
        print(f"Total revenue: ${stats['total_revenue']:.2f}")
        print(f"Customers paid: {stats['customers_paid']}")
        print(f"Customers left without paying: {stats['customers_left']}")
        print(f"Total orders served: {stats['served_customers']}")
        print(f"===================================")

        # Store daily stats before resetting
        self.daily_record[0] = {
            'day': stats['day'],
            'customers_paid': stats['customers_paid'],
            'customers_left': stats['customers_left'],
            'revenue': stats['total_revenue'],
            'food_revenue': stats['food_revenue'],
            'tips': stats['tips'],
            'served_orders': stats['served_customers'],
            'avg_satisfaction': self.get_average_satisfaction()
        }

        # Before advancing day counter, apply the manager's optimized schedule
        #print(f"DEBUG: Day {self.current_day} completed, resetting for day {self.current_day + 1}")
        #print(f"DEBUG: Before reset - current_minute: {self.current_minute}")

        # Apply manager's schedule if available
        if hasattr(self.manager, 'waiters_assigned_count') and any(self.manager.waiters_assigned_count.values()):
            print(f"Applying manager's schedule for day {self.current_day + 1}")
            print(f"Predicted customers: {self.manager.predicted_customers}")
            print(f"Waiters per shift: {self.manager.waiters_assigned_count}")
        else:
            print(f"No schedule available for day {self.current_day + 1}, using defaults")
            if not hasattr(self.manager, 'waiters_assigned_count'):
                self.manager.waiters_assigned_count = {1: 2, 2: 2, 3: 2}  #

        # Reset time to opening hour
        self.current_minute = self.opening_hour

        # Reset daily counters
        self.customers_paid = 0
        self.customers_left_without_paying = 0
        self.revenue = 0
        self.total_orders_served = 0

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
            waiter.carrying_food = []  # Clear any carried food
            waiter.target_pos = None

            # Reset position to kitchen
            self.grid.move_agent(waiter, self.kitchen.pos)

        # Advance day counter
        self.current_day += 1

        # Reset running flag
        self.running = True

        #print(f"DEBUG: After reset - current_minute: {self.current_minute}, day: {self.current_day}")
        #print(f"DEBUG: Opening hour: {self.opening_hour}, Closing hour: {self.closing_hour}")

        # Create waiters for first shift after reset
        print(f"Creating waiters for first shift of day {self.current_day}")
        first_shift = min(self.shifts.keys())
        self.create_waiters_for_shift(first_shift)

    def create_waiters_for_shift(self, shift_id):
        """Create waiters for the specified shift based on manager's schedule"""
        if not self.manager or not hasattr(self.manager, 'schedule'):
            print(f"Warning: No manager or schedule found for shift {shift_id}")
            return

        # Default min waiters if on day 1 or no schedule exists
        if self.current_day == 1 and not self.manager.waiters_assigned_count.get(shift_id, 0):
            waiters_needed = 4  # Minimum default for day 1
        else:
            waiters_needed = self.manager.waiters_assigned_count.get(shift_id, 2)

        # Get current waiters
        current_waiters = list(self.agents.select(agent_type=WaiterAgent))
        current_count = len(current_waiters)

        print(f"Shift {shift_id}: {waiters_needed} waiters needed, {current_count} currently active")

        # Case 1: Remove excess waiters
        if current_count > waiters_needed:
            waiters_to_remove = current_waiters[waiters_needed:]
            for waiter in waiters_to_remove:
                self.grid.remove_agent(waiter)
                self.agents.remove(waiter)
            print(f"Removed {len(waiters_to_remove)} excess waiters")

        # Case 2: Add new waiters
        elif current_count < waiters_needed:
            waiters_to_add = waiters_needed - current_count
            # Find max existing ID to avoid duplicates
            max_waiter_id = 0
            for w in current_waiters:
                if hasattr(w, 'unique_id') and w.unique_id > max_waiter_id:
                    max_waiter_id = w.unique_id

            for i in range(waiters_to_add):
                waiter_agent = WaiterAgent(self)
                waiter_agent.shift = shift_id
                waiter_agent.unique_id = max_waiter_id + i + 1  # Use truly unique IDs
                waiter_agent.is_available = True
                waiter_agent.carrying_food = []  # Initialize with empty list
                waiter_agent.target_pos = None

                self.agents.add(waiter_agent)
                self.grid.place_agent(waiter_agent, self.kitchen.pos)
            print(f"Added {waiters_to_add} new waiters")

        else:
            print(f"No change in waiters for shift {shift_id}")

        # Reset all waiters for the new shift
        for waiter in self.agents.select(agent_type=WaiterAgent):
            # Update shift assignment
            waiter.shift = shift_id

        # Debug state of all waiters
        #print(f"DEBUG: Created waiters for shift {shift_id}: {waiters_needed} needed, {current_count} existing")
        #for w in self.agents.select(agent_type=WaiterAgent):
        #    print(
        #        f"DEBUG: Waiter {w.unique_id} state: "
        #        f"available={w.is_available}, "
        #        f"carrying_food={len(w.carrying_food) if hasattr(w, 'carrying_food') else 0},"
        #        f"target_pos={w.target_pos}"
        #    )

    def get_total_tips(self):
        total_tips = sum(waiter.tips for waiter in self.agents
                         if hasattr(waiter, 'tips'))
        return total_tips
        
    def get_daily_stats(self):
        """Get daily statistics for debugging and reporting"""
        # Calculate tips from waiters
        total_tips = self.get_total_tips()

        # Get food revenue (revenue minus tips)
        food_revenue = self.revenue - total_tips

        stats = {
            'day': self.current_day,
            'food_revenue': food_revenue,
            'tips': total_tips,
            'total_revenue': self.revenue,
            'customers_paid': self.customers_paid,
            'customers_left': self.customers_left_without_paying,
            'served_customers': self.total_orders_served
        }

        return stats

    def step(self):
        """Advance simulation by one time step"""
        # Update metrics
        self.customer_count = len(self.agents.select(agent_type=CustomerAgent))
        self.datacollector.collect(self)

        self.current_minute += self.time_step

        # Create waiters at the beginning of each shift
        for shift_id, shift_info in self.shifts.items():
            if self.current_minute == shift_info["start"]:
                print(f"Starting shift {shift_id}: {shift_info['name']}")
                self.create_waiters_for_shift(shift_id)

        # print(f"DEBUG: After reset - current_minute: {self.current_minute}, day: {self.current_day}")
        # print(f"DEBUG: Opening hour: {self.opening_hour}, Closing hour: {self.closing_hour}")

        # Debug customer generation attempts
        if self.opening_hour <= self.current_minute < self.closing_hour:
            self.add_new_customers()

        if self.current_minute % 60 == 0:  # Print stats every hour
            hour_24_format = self.current_minute // 60
            print(f"Day {self.current_day}, Hour {hour_24_format}:00:")
            print(f"Customers paid: {self.customers_paid}")
            print(f"Customers left without paying: {self.customers_left_without_paying}")
            print(f"Current Revenue: ${self.revenue:.2f}\n")

        #print(
        #    f"DEBUG: Day {self.current_day}, minute {self.current_minute}: "
        #    f"Active customers: {len(self.agents.select(agent_type=CustomerAgent))}, "
        #    f"waiters: {len(self.agents.select(agent_type=WaiterAgent))}")

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
            #print(f"DEBUG: Day {self.current_day} complete, transitioning to day {self.current_day + 1}")
            self.reset_for_new_day()
            return  # Important: return after reset to avoid multiple resets

        # print(f"Kitchen state: {len(self.kitchen.requested_orders)} requested, "
        #      f"{len(self.kitchen.prepared_orders)} prepared")

        # Update metrics
        self.customer_count = len(self.agents.select(agent_type=CustomerAgent))
