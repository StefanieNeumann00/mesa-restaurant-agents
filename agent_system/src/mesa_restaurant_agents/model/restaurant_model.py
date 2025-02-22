import mesa
import numpy as np
import random

from ..agents.customer_agent import CustomerAgent
from ..agents.manager_agent import ManagerAgent
from ..agents.waiter_agent import WaiterAgent
from ..utils.environment_definition import EnvironmentDefinition
from ..utils.kitchen import Kitchen

class RestaurantModel(mesa.Model):
    def __init__(self, n_waiters, grid_width, grid_height, seed=None):
        super().__init__(seed=seed)

        self.grid_height = grid_height if grid_height % 2 != 0 else grid_height+1 # make sure grid_height is uneven
        self.grid_width = grid_width if grid_width % 2 != 0 else grid_width+1 # make sure grid_width is uneven

        # Initialize grid and environment first
        self.grid = mesa.space.SingleGrid(self.grid_width, self.grid_height, True)
        # Initialize environment and agents list
        self.environment = [[0 for _ in range(grid_height)] for _ in range(grid_width)]
        self.agent_list = []

        # Initialize sets after environment is created
        self.free_positions = set()
        self.occupied_positions = set()
        self.walkway_positions = {(x, y)
                                  for x in range(self.grid_width)
                                  for y in range(self.grid_height)
                                  if self.is_walkway((x, y))}
        # Convert times to minutes since opening
        self.opening_hour = 11 * 60  # 11:00 in minutes
        self.closing_hour = 23 * 60  # 23:00 in minutes
        self.time_step = 5  # minutes per step
        self.current_minute = self.opening_hour  # Start at opening time

        self.kitchen = Kitchen(pos = (self.grid_width - 2, self.grid_height-2))
        self.layout = {
            'kitchen': self.kitchen.pos,
            'walkways': set(),
            'tables': set()
        }

        self._setup_restaurant_layout()

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
                "Step": lambda m: getattr(m, 'current_minute', 0),
                "Customer_Count": lambda m: len([a for a in m.agents if isinstance(a, CustomerAgent)]),
                "Average_Wait_Time": lambda m: m.get_average_wait_time(),
                "Average_Customer_Satisfaction": lambda m: m.get_average_satisfaction(),
                "Profit": lambda m: m.get_total_profit(),
                "Customer_Info": lambda m: m.get_customer_info(m.agents),
                "Waiter_Info": lambda m: m.get_waiter_info(m.agents)
            }
         )
        # Collect initial state
        self.datacollector.collect(self)

    def get_current_time(self):
        """Convert current minutes to datetime for display"""
        hours = self.current_minute // 60
        minutes = self.current_minute % 60
        return f"{hours:02d}:{minutes:02d}"

    def get_free_positions(self, agent):
        env_view = self.environment  # avoid repeated lookups
        target = (EnvironmentDefinition.FREE_TABLE.value
                  if isinstance(agent, CustomerAgent)
                  else EnvironmentDefinition.FREE.value)

        return [(x, y) for x in range(len(env_view))
                for y in range(len(env_view[x]))
                if env_view[x][y] == target]

    def set_occupied(self, pos):
        x, y = pos
        if self.environment[x][y] in (EnvironmentDefinition.FREE.value,
                                      EnvironmentDefinition.FREE_TABLE.value):
            self.environment[x][y] += 1  # Assuming OCCUPIED is FREE + 1

    def _setup_restaurant_layout(self):
        """Initialize the restaurant layout with tables, kitchen, and walkways"""
        # Set kitchen location
        self.environment[self.kitchen.pos[0]][self.kitchen.pos[1]] = EnvironmentDefinition.KITCHEN.value

        # Set tables and walkways
        for x in range(self.grid_width):
            for y in range(self.grid_height):
                pos = (x, y)
                # Tables are placed on odd coordinates, not on edges
                if (y % 2 != 0 and x % 2 != 0 and
                        x != self.grid_width - 1 and y != self.grid_height - 1 and (x,y) != self.kitchen.pos):
                    self.environment[x][y] = EnvironmentDefinition.FREE_TABLE.value
                    self.layout['tables'].add(pos)
                else:
                    self.layout['walkways'].add(pos)

    def is_walkway(self, pos):
        """Check if a position is a walkway"""
        x, y = pos
        return (self.environment[x][y] == EnvironmentDefinition.FREE.value or
                self.environment[x][y] == EnvironmentDefinition.OCCUPIED.value)

    def position(self, agents):
        for agent in agents:
            free_positions = self.get_free_positions(agent)
            if len(free_positions) > 0:
                index = random.randint(0, len(free_positions)-1)
                pos = free_positions[index]
                self.grid.place_agent(agent, pos)
                self.set_occupied(pos)
            else:
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
        base_rate = 3  # Base arrival rate (non-peak)
        if self.is_peak_hour():
            base_rate = 8  # Increased arrival rate during peak hours
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
