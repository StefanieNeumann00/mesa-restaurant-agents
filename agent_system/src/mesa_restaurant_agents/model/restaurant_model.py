import mesa
import numpy as np
from datetime import datetime, timedelta

from ..agents.customer_agent import CustomerAgent
from ..agents.manager_agent import ManagerAgent
from ..agents.waiter_agent import WaiterAgent
from ..utils.kitchen import Kitchen
from ..utils.restaurant_grid import RestaurantGrid

class RestaurantModel(mesa.Model):
    def __init__(self, n_waiters, grid_width, grid_height, seed=None):
        super().__init__(seed=seed)

        self.grid_height = grid_height if grid_height % 2 != 0 else grid_height+1 # make sure grid_height is uneven
        self.grid_width = grid_width if grid_width % 2 != 0 else grid_width+1 # make sure grid_width is uneven

        # Initialize grid and environment first
        self.grid = mesa.space.SingleGrid(self.grid_width, self.grid_height, True)
        # Initialize environment and agents list
        self.agent_list = []

        # Convert times to minutes since opening
        self.opening_hour = 11 * 60  # 11:00 in minutes
        self.closing_hour = 23 * 60  # 23:00 in minutes
        self.time_step = 5  # minutes per step
        self.current_minute = self.opening_hour  # Start at opening time

        WaiterAgent.create_agents(model=self, n=n_waiters)
        ManagerAgent.create_agents(model=self, n=1)

        self.kitchen = Kitchen(pos = (self.grid_width - 2, self.grid_height-2))
        self.grid = RestaurantGrid(self.grid_width, self.grid_height, self.kitchen.pos)

        # Create agents after environment setup
        WaiterAgent.create_agents(model=self, n=n_waiters)
        ManagerAgent.create_agents(model=self, n=1)
        self.position(self.agents)

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
                "Profit": lambda m: np.mean(
                    [ma.daily_stats['profit'] for ma in m.agents.select(agent_type=ManagerAgent)]),
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
        for content, pos in self.grid.coord_iter():
            if content:
                state.append({
                    'pos': pos,
                    'type': type(content).__name__,
                    'state': getattr(content, 'state', None)
                })
        return state

    def position(self, agents):
        for agent in agents:
            if not self.grid.position_randomly(agent):
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

    def get_customers_count(self, agents):
        return len(agents.select(agent_type=CustomerAgent))

    def is_peak_hour(self):
        """Check if current time is during peak hours"""
        hour = self.current_minute // 60
        return (12 <= hour <= 14) or (17 <= hour <= 20)

    def calculate_new_customers(self):
        """Calculate number of new customers based on time of day"""
        base_rate = 5  # Base arrival rate (non-peak)
        if self.is_peak_hour():
            base_rate = 11  # Increased arrival rate during peak hours
        return np.random.poisson(base_rate)  # Random variation in arrivals

    def add_new_customers(self):
        n_new = self.calculate_new_customers()
        for _ in range(n_new):
            customer = CustomerAgent(model=self)
            customer.order_time = self.current_minute
            self.agents.add(customer)
            self.position([customer])
            self.kitchen.add_new_customer_order(customer, customer.food_preference, customer.order_time)

    def remove_customer(self, customer):
        """Remove customer from restaurant tracking"""
        if customer in self.agents.select(agent_type=CustomerAgent):
            self.grid.remove_agent(customer)
            self.agents.remove(customer)

    def get_average_wait_time(self):
        """Calculate average wait time safely"""
        customers = [a for a in self.agents if isinstance(a, CustomerAgent)]
        if not customers:
            return 0.0
        return sum(c.waiting_time for c in customers) / len(customers)

    def get_average_satisfaction(self):
        """Calculate average satisfaction safely"""
        customers = [a for a in self.agents if isinstance(a, CustomerAgent)]
        if not customers:
            return 100.0
        return sum(c.satisfaction for c in customers) / len(customers)

    def get_total_profit(self):
        """Calculate total profit safely"""
        managers = [a for a in self.agents if isinstance(a, ManagerAgent)]
        if not managers:
            return 0.0
        return sum(m.daily_stats.get('profit', 0) for m in managers)

    def step(self):
        """Advance simulation by one time step"""
        # Process restaurant operations during open hours
        if not self.opening_hour <= self.current_minute <= self.closing_hour:
            self.running = False
            return

        # Always collect data first
        self.datacollector.collect(self)

        self.add_new_customers()
        self.kitchen.add_ready_orders_to_prepared(self.current_minute)
        self.agents.shuffle_do("step")
        self.current_minute += self.time_step

        # Check if restaurant is closing
        if self.current_minute >= self.closing_hour:
            self.running = False

