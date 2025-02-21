from ..utils.order_status import OrderStatus, food_options
from ..agents.customer_agent import CustomerAgent
import mesa

class WaiterAgent(mesa.Agent):
    def __init__(self, model):
        super().__init__(model)
        # Initialize waiter properties
        self.model = model            # Current serving status
        self.current_orders = {}         # List of (customer, order) tuples
        self.carrying_food = []  # List of orders currently being carried
        self.max_carry = 2       # Maximum number of food items that can be carried
        self.tips = 0                    # Total tips received
        self.avg_rating = 0              # Average rating from customers
        self.ratings_count = 0           # Number of ratings received
        self.served_customers = 0        # Total customers served

    def can_pick_up_food(self):
        return len(self.carrying_food) < self.max_carry

    def pick_up_food(self, food):
        if self.can_pick_up_food():
            self.carrying_food.append(food)
            return True
        return False
    
    def is_ordered(self, agent):
        if isinstance(agent, CustomerAgent) and agent.order_status == OrderStatus.ORDERED:
            return True
        return False

    def get_best_customer(self):
        customers_ordered = self.model.agents.select(filter_func=self.is_ordered)
        if len(customers_ordered) > 0:
            return customers_ordered.__getitem__(0)
        return None

    def step(self):
        customer = self.get_best_customer()
        if customer:
            self.serve_dish(customer)

    def serve_dish(self, customer):
        customer.order_status = OrderStatus.SERVED
        customer.assigned_waiter.append(self)
        self.served_customers += 1

    def update_performance_metrics(self, customer):
        tip = customer.tip
        self.tips += tip