from ..utils.order_status import OrderStatus, food_options
import mesa
import random

class CustomerAgent(mesa.Agent):
    def __init__(self, model):
        super().__init__(model)
        # Initialize customer properties
        self.food_preference = random.choice(list(food_options.keys()))
        self.bill = 0                                 # Amount to pay for food
        self.waiting_time = 0                         # Time spent waiting
        self.order_status = OrderStatus.WAITING       # Current order status
        self.order_time = None                        # Time when order was placed
        self.satisfaction = 100                       # Overall satisfaction (0-100)
        self.tip = 0                                  # Amount of tip given
        self.assigned_waiter = None                   # Reference to assigned waiter

        # Table assignment and timing
        self.table = None                             # Assigned table
        self.dining_duration = random.randint(60, 120)  # Time to spend at restaurant

    def step(self):
        """Update customer state each time step (1 minute)"""
        # Increment waiting time if not served yet
        if self.order_status != OrderStatus.SERVED:
            self.waiting_time = ((self.model.current_time - self.order_time).total_seconds() % 3600) // 60
            self.satisfaction = max(0, 100 - (self.waiting_time * 2))  # Decrease by 2 points per minute
            if self.waiting_time >= self.dining_duration:
                self.leave_without_paying()

        # Check if customer should leave after finishing meal
        if self.table and self.order_status == OrderStatus.SERVED:
            current_time = self.model.current_time
            if ((current_time - self.order_time).total_seconds() % 3600) // 60 >= self.dining_duration:
                self.leave_restaurant()

    def order_dish(self, waiter):
        # Place order and calculate bill with waiter if not already ordered
        if self.order_status == OrderStatus.WAITING:
            self.order_status = OrderStatus.ORDERED
            self.assigned_waiter = waiter
            self.bill = food_options[self.food_preference]["price"]
            self.order_time = self.model.current_time
            return self.food_preference
        return None

    def calculate_tip(self):
        """Calculate tip based on waiting time"""
        if not self.order_time:
            return 0

        self.waiting_time = ((self.model.current_time - self.order_time).total_seconds() % 3600) // 60
        base_tip_rate = 0.20  # 20% maximum tip

        if self.waiting_time <= 10:
            tip_rate = base_tip_rate
        elif self.waiting_time >= 30:
            tip_rate = 0
        else:
            # Decrease by 1% per minute after 10 minutes
            tip_rate = base_tip_rate - (1 * (self.waiting_time - 20))

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
        if self.table:
            if self.assigned_waiter:
                self.assigned_waiter.current_orders = [
                    (c, o) for c, o in self.assigned_waiter.current_orders
                    if c != self
                ]
            self.satisfaction = 0
            self.tip = 0
            self.table.remove_customer(self)
            self.model.remove_customer(self)

    def leave_restaurant(self):
        """Leave restaurant after dining"""
        if self.table:
            payment = self.rate_and_pay()
            if self.assigned_waiter:
                self.assigned_waiter.process_payment(self, payment)
            self.table.remove_customer(self)
            self.model.remove_customer(self)
            self.assigned_waiter.update_performance_metrics(self)