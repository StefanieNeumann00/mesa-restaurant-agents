from ..utils.order_status import OrderStatus, food_options
import mesa
import random

class CustomerAgent(mesa.Agent):
    def __init__(self, model):
        super().__init__(model)
        # Initialize customer properties
        self.food_preference = random.choice(list(food_options.keys()))
        self.bill = food_options[self.food_preference]["price"]    # Amount to pay for food
        self.waiting_time = 0                         # Time spent waiting
        self.order_status = OrderStatus.ORDERED       # Current order status
        self.order_time = None                        # Time when order was placed
        self.satisfaction = 100                       # Overall satisfaction (0-100)
        self.tip = 0                                  # Amount of tip given
        self.assigned_waiter = []                     # Reference to assigned waiter
        self.dining_duration = random.randint(60, 120)  # Time to spend at restaurant

    def step(self):
        """Update customer state each time step (5 minutes)"""
        # Increment waiting time if not served yet
        if self.order_status != OrderStatus.SERVED:
            self.waiting_time = ((self.model.current_time - self.order_time).total_seconds() % 3600) // 60
            self.satisfaction = max(0, 100 - (self.waiting_time * 2))  # Decrease by 2 points per minute
            if self.waiting_time >= self.dining_duration:
                self.leave_without_paying()

        # Check if customer should leave after finishing meal
        if self.order_status == OrderStatus.SERVED:
            current_time = self.model.current_time
            if ((current_time - self.order_time).total_seconds() % 3600) // 60 >= self.dining_duration:
                self.leave_restaurant()

    def calculate_tip(self):
        """Calculate tip based on waiting time"""
        if not self.order_time:
            return 0

        self.waiting_time = ((self.model.current_time - self.order_time).total_seconds() % 3600) // 60
        base_tip_rate = 0.20  # 20% maximum tip

        if self.waiting_time <= 10:
            tip_rate = base_tip_rate
        elif self.waiting_time >= 30:
            tip_rate = 0.02
        else:
            # Decrease by 1% per minute after 10 minutes
            tip_rate = base_tip_rate - (1 * (self.waiting_time - 18))

        return round(self.bill * tip_rate, 2)

    def rate_and_pay(self):
        """Calculate payment including tip based on service time"""
        self.tip = self.calculate_tip()
        # Satisfaction based on waiting time (0-100)
        self.waiting_time = ((self.model.current_time - self.order_time).total_seconds() % 3600) // 60
        self.satisfaction = max(0, 100 - (self.waiting_time * 2))  # Decrease by 2 points per minute
        return self.bill + self.tip

    def leave_without_paying(self):
        """Leave restaurant due to excessive waiting time"""
        self.satisfaction = 0
        self.tip = 0
        self.model.remove_customer(self)

    def leave_restaurant(self):
        """Leave restaurant after dining"""
        payment = self.rate_and_pay()
        self.waiter.process_payment(self, payment)
        self.model.remove_customer(self)
        self.assigned_waiter.update_performance_metrics(self)