from ..utils.order_status import OrderStatus, food_options
import mesa
import random

class CustomerAgent(mesa.Agent):
    def __init__(self):
        super().__init__()
        # Initialize customer properties
        self.food_preference = random.choice(list(food_options.keys()))
        self.bill = 0                                 # Amount to pay for food
        self.waiting_time = 0                         # Time spent waiting
        self.order_status = OrderStatus.WAITING       # Current order status
        self.order_time = None                        # Time when order was placed
        self.satisfaction = 0                         # Overall satisfaction (0-100)
        self.tip = 0                                  # Amount of tip given
        self.assigned_waiter = None                   # Reference to assigned waiter

        # Table assignment and timing
        self.table = None                             # Assigned table
        self.arrival_time = None                      # Time customer arrived
        self.dining_duration = random.randint(60, 90, 120) # Time to spend at restaurant

    def step(self):
        """Update customer state each time step (5 minutes)"""
        # Increment waiting time if not served yet
        if self.order_status != OrderStatus.SERVED:
            current_time = self.model.current_time
            wait_minutes = (current_time - self.order_time).total_minutes()

        # Check if customer should leave after finishing meal
        if self.table and self.order_status == OrderStatus.SERVED:
            current_time = self.model.current_time
            if (current_time - self.arrival_time).total_minutes() >= self.dining_duration:
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

        wait_minutes = (self.model.current_time - self.order_time).total_minutes()
        base_tip_rate = 0.20  # 20% maximum tip

        if wait_minutes <= 10:
            tip_rate = base_tip_rate
        elif wait_minutes >= 30:
            tip_rate = 0
        else:
            # Decrease by 1% per minute after 10 minutes
            tip_rate = base_tip_rate - (1 * (wait_minutes - 20))

        return round(self.bill * tip_rate, 2)

    def rate_and_pay(self):
        """Calculate payment including tip based on service time"""
        self.tip = self.calculate_tip()
        # Satisfaction based on waiting time (0-100)
        wait_minutes = (self.model.current_time - self.order_time).total_minutes()
        self.satisfaction = max(0, 100 - (wait_minutes * 2))  # Decrease by 2 points per minute
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