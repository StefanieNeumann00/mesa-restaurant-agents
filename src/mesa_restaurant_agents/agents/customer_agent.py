from ..utils.order_status import OrderStatus, food_options
import mesa
import random

class CustomerAgent(mesa.Agent):
    def __init__(self, model):
        super().__init__(model)
        # Initialize customer properties
        self.active = True
        self.food_preference = random.choice(food_options)
        self.waiting_time = 0                         # Time spent waiting
        self.order_status = OrderStatus.WAITING       # Current order status
        self.satisfaction = 100                         # Overall satisfaction (0-100)
        self.tip = 0                                 # Amount of tip given
        self.rating = 0                              # Rating given (1-5)
        self.assigned_waiter = None                  # Reference to assigned waiter

         # Table assignment and timing
        self.table = None                            # Assigned table
        self.arrival_time = None                     # Time customer arrived
        self.dining_duration = random.randint(30, 90)  # Time to spend at restaurant

    def step(self):
        # Increment waiting time if not served yet
        if self.order_status != OrderStatus.SERVED:
            self.waiting_time += 1

        # Check if customer should leave after finishing meal
        if self.table and self.order_status == OrderStatus.SERVED:
            current_time = self.model.current_time
            if (current_time - self.arrival_time).total_minutes() >= self.dining_duration:
                self.leave_restaurant()

    def order_dish(self, waiter):
        # Place order with waiter if not already ordered
        if self.order_status == OrderStatus.WAITING:
            self.order_status = OrderStatus.ORDERED
            self.assigned_waiter = waiter
            return self.food_preference

    def rate_experience(self):
        # Calculate satisfaction based on waiting time
        self.satisfaction = max(0, 100 - self.waiting_time)
        # Convert satisfaction to 1-5 star rating
        self.rating = max(1, self.satisfaction / 20)
        # Calculate tip based on satisfaction
        self.tip = self.satisfaction / 10
        self.active = False

    def leave_restaurant(self):
        """Handle customer departure process"""
        if self.table:
            self.rate_experience()      # Rate service before leaving
            self.table.remove_customer(self)
            self.model.remove_customer(self)