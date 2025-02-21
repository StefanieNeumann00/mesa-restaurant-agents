import mesa
import numpy as np
from datetime import datetime, timedelta
import random

from ..agents.customer_agent import CustomerAgent
from ..agents.manager_agent import ManagerAgent
from ..agents.waiter_agent import WaiterAgent
from ..utils.environment_definition import EnvironmentDefinition

class RestaurantModel(mesa.Model):

    def __init__(self, n_waiters, grid_width, grid_height, seed=None):
        super().__init__(seed=seed)

        self.grid_height = grid_height if grid_height % 2 != 0 else grid_height+1 # make sure grid_height is uneven
        self.grid_width = grid_width if grid_width % 2 != 0 else grid_width+1 # make sure grid_width is uneven
        self.opening_time = datetime.strptime("11:00", "%H:%M")
        self.closing_time = datetime.strptime("23:00", "%H:%M")
        self.current_time = self.opening_time
        self.time_step = 5  # Each step represents 5 minutes

        WaiterAgent.create_agents(model=self, n=n_waiters)
        ManagerAgent.create_agents(model=self, n=1)

        self.grid = mesa.space.MultiGrid(self.grid_width, self.grid_height, True)
        self.environment = np.zeros((self.grid_width, self.grid_height))
        self.kitchen_pos = (self.grid_width - 2, self.grid_height-2)
        self.layout = {
            'kitchen': self.kitchen_pos,
            'walkways': set(),
            'tables': set()
        }

        self._setup_restaurant_layout()

        self.position(self.agents)

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
                "Waiter_Info": lambda m: self.get_waiter_info(m.agents)
            }
        )

    def get_free_positions(self, agent):
        free_positions = []
        if isinstance(agent, CustomerAgent):
            for x in range(len(self.environment)):
                for y in range(len(self.environment[x])):
                    if self.environment[x][y] == EnvironmentDefinition.FREE_TABLE.value:
                        free_positions.append((x,y))
        else:
            for x in range(len(self.environment)):
                for y in range(len(self.environment[x])):
                    if self.environment[x][y] == EnvironmentDefinition.FREE.value:
                        free_positions.append((x,y))
        return free_positions

    def set_occupied(self, pos):
        x = pos[0]
        y = pos[1]
        if self.environment[x][y] == EnvironmentDefinition.FREE.value:
            self.environment[x][y] = EnvironmentDefinition.OCCUPIED.value
        elif self.environment[x][y] == EnvironmentDefinition.FREE_TABLE.value:
            self.environment[x][y] = EnvironmentDefinition.OCCUPIED_TABLE.value

    def _setup_restaurant_layout(self):
        """Initialize the restaurant layout with tables, kitchen, and walkways"""
        # Set kitchen location
        self.environment[self.kitchen_pos[0]][self.kitchen_pos[1]] = EnvironmentDefinition.KITCHEN.value

        # Set tables and walkways
        for x in range(self.grid_width):
            for y in range(self.grid_height):
                pos = (x, y)
                # Tables are placed on odd coordinates, not on edges
                if (y % 2 != 0 and x % 2 != 0 and
                        x != self.grid_width - 1 and y != self.grid_height - 1 and (x,y) != self.kitchen_pos):
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
                      "current_orders": waiter.current_orders,
                      "tips": waiter.tips,
                      "avg_rating": waiter.avg_rating,
                      "served_customers": waiter.served_customers}
            w_infos.append(w_info)
        return w_infos

    def get_customers_count(self, agents):
        return len(agents.select(agent_type=CustomerAgent))

    def is_peak_hour(self):
        """Check if current time is during peak hours"""
        hour = self.current_time.hour
        return (12 <= hour <= 14) or (17 <= hour <= 20)

    def calculate_new_customers(self):
        """Calculate number of new customers based on time of day"""
        base_rate = 2  # Base arrival rate (non-peak)
        if self.is_peak_hour():
            base_rate = 5  # Increased arrival rate during peak hours
        return np.random.poisson(base_rate)  # Random variation in arrivals

    def add_new_customers(self):
        n_new = self.calculate_new_customers()
        for _ in range(n_new):
            customer = CustomerAgent(model=self)
            customer.order_time = self.current_time
            self.agents.add(customer)
            self.position([customer])

    def remove_customer(self, customer):
        """Remove customer from restaurant tracking"""
        if customer in self.agents.select(agent_type=CustomerAgent):
            self.grid.remove_agent(customer)
            self.agents.remove(customer)

    def step(self):
        """Advance simulation by one time step"""
        # Process restaurant operations during open hours
        if self.opening_time <= self.current_time <= self.closing_time:
            self.add_new_customers()

        # Collect data and execute agent steps in random order
        self.datacollector.collect(self)
        self.agents.shuffle_do("step")

        # Update time
        self.current_time += timedelta(minutes=self.time_step)

        # Check closing time
        if self.current_time >= self.closing_time:
            self.running = False
