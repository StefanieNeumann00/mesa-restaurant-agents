import mesa
import numpy as np
import random
from datetime import datetime, timedelta
import random

from ..agents.customer_agent import CustomerAgent
from ..agents.manager_agent import ManagerAgent
from ..agents.waiter_agent import WaiterAgent

from ..utils.table import Table

class RestaurantModel(mesa.Model):
    def __init__(self, n_waiters, seed=None):
        super().__init__(seed=seed)

        self.opening_time = datetime.strptime("11:00", "%H:%M")
        self.closing_time = datetime.strptime("23:00", "%H:%M")
        self.current_time = self.opening_time
        self.time_step = 5            # Each step represents 5 minutes

        # Create agents
        self.tables = [Table(i) for i in range(100)]  # Create 100 tables
        WaiterAgent.create_agents(model=self, n=n_waiters)
        ManagerAgent.create_agents(model=self, n=1)

        '''
        self.customers = []
        self.waiters = []
        self.managers = []

        for agent in self.agents:
            if isinstance(agent, CustomerAgent):
                self.customers.append(agent)
            elif isinstance(agent, WaiterAgent):
                self.waiters.append(agent)
            elif isinstance(agent, ManagerAgent):
                self.managers.append(agent)

        print(self.customers)
        print(self.waiters)
        print(self.managers)
        '''

        # Set up data collection for model metrics
        self.datacollector = mesa.DataCollector(
            model_reporters={
                "Customer_Count": lambda m: self.get_customers_count(m.agents),
                "Average_Wait_Time": lambda m: np.mean([c.waiting_time for c in m.agents.select(agent_type=CustomerAgent)]),
                "Average_Customer_Satisfaction": lambda m: np.mean([c.satisfaction for c in m.agents.select(agent_type=CustomerAgent)]),
                "Profit": lambda m: np.mean([ma.daily_stats['profit'] for ma in m.agents.select(agent_type=ManagerAgent)]),
                "Customer_Info": lambda m: self.get_customer_info(m.agents)
            }
        )
    
    def get_customer_info(self, agents):
        customers = agents.select(agent_type=CustomerAgent)
        c_infos = []
        c_nr = 0
        for customer in customers:
            c_info = {}
            c_info['customer_nr'] = c_nr
            c_info['waiting_time'] = customer.waiting_time
            c_info['order_status'] = customer.order_status.value
            c_info['satisfaction'] = customer.satisfaction
            c_infos.append(c_info)
            c_nr += 1
        return c_infos

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

    def find_available_table(self):
        """Find a random table with available seats"""
        available_tables = [t for t in self.tables if t.is_available()]
        return random.choice(available_tables) if available_tables else None

    def add_new_customers(self):
        """Add new customers to the restaurant if tables are available"""
        n_new = self.calculate_new_customers()
        for _ in range(n_new):
            if table := self.find_available_table():
                customer = CustomerAgent(model=self)
                customer.arrival_time = self.current_time
                table.add_customer(customer)
                self.agents.add(customer)

    def remove_customer(self, customer):
        """Remove customer from restaurant tracking"""
        if customer in self.agents.select(agent_type=CustomerAgent):
            self.agents.remove(customer)

    def step(self):
        """Advance simulation by one time step"""
        # Update time
        self.current_time += timedelta(minutes=self.time_step)

        # Process restaurant operations during open hours
        if self.opening_time <= self.current_time <= self.closing_time:
            self.add_new_customers()

        # Collect data and execute agent steps in random order
        self.datacollector.collect(self)
        self.agents.shuffle_do("step")

        # Check closing time
        if self.current_time >= self.closing_time:
            self.running = False