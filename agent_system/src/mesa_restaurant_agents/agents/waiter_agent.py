from ..utils.order_status import OrderStatus, food_options
from ..agents.customer_agent import CustomerAgent
import mesa

class WaiterAgent(mesa.Agent):
    def __init__(self, model):
        super().__init__(model)
        # Initialize waiter properties
        self.model = model
        self.busy = False                # Current serving status
        self.current_orders = {}         # List of (customer, order) tuples
        self.carrying_food = []  # List of orders currently being carried
        self.max_carry = 2  # Maximum number of food items that can be carried
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

    def calculate_closest_customer(self, ordered):
        for customer in self.model.agents.select(agent_type=CustomerAgent):
            if customer in self.current_orders.keys() and ordered:
                return customer
            elif customer not in self.current_orders.keys() and not ordered:
                return customer

    def step(self):
        if self.busy:
            customer = self.calculate_closest_customer(ordered=True)
            if customer:
                self.serve_dish(customer)
        else:
            customer = self.calculate_closest_customer(ordered=False)
            if customer:
                self.take_order(customer)

    def take_order(self, customer):
        # Take order from customer if waiter is available
        if not self.busy:
            order = customer.order_dish(self)
            if order:
                self.current_orders.update({customer: order})
                self.busy = True
                return True
        return False

    def serve_dish(self, customer):
        # Serve food to customer and collect feedback
        if customer in self.current_orders.keys():
            order = self.current_orders[customer]
            if order in self.carrying_food:
                # Serve the food
                self.carrying_food.remove(order)
                customer.order_status = OrderStatus.SERVED
                # Remove served customer from current orders
                del self.current_orders[customer]
                self.busy = len(self.current_orders) > 0
                self.served_customers += 1
                return True
            elif not self.carrying_food and self.can_pick_up_food():
                # Pick up food from kitchen if not carrying anything
                self.pick_up_food(order)
        return False

    def update_performance_metrics(self, customer):
        # Update waiter's performance metrics
        #rating = customer.rating
        tip = customer.tip
        self.tips += tip
        #self.ratings_count += 1
        #self.avg_rating = ((self.avg_rating * (self.ratings_count - 1)) + rating) / self.ratings_count