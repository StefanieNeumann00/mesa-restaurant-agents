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
        self.order_minute = model.current_minute      # Step when order was placed
        self.satisfaction = 100                       # Overall satisfaction (0-100)
        self.tip = 0                                  # Amount of tip given
        self.assigned_waiter = []                     # Reference to assigned waiter
        self.dining_duration = random.randint(60, 120)  # Time to spend at restaurant
        self._served_logged = False

    def step(self):
        """Update customer state each time step (5 minutes)"""
        if self.order_status == OrderStatus.SERVED and not hasattr(self, '_served_logged'):
            #print(f"Customer was served after {self.waiting_time} minutes")
            self._served_logged = True

        # Increment waiting time if not served yet
        if self.order_status != OrderStatus.SERVED:
            self.waiting_time = self.model.current_minute - self.order_minute
            self.satisfaction = max(0, 100 - (self.waiting_time * 2))  # Decrease by 2 points per minute
            if self.waiting_time >= self.dining_duration:
                # print(f"Customer left unserved after waiting {self.waiting_time} minutes")
                self.leave_without_paying()

        # Check if customer should leave after finishing meal
        if self.order_status == OrderStatus.SERVED:
            time_spent = self.model.current_minute - self.order_minute
            if time_spent >= self.dining_duration:
                self.leave_restaurant()

    def calculate_tip(self):
        """Calculate tip based on waiting time"""
        if not self.order_minute:
            return 0

        self.waiting_time = self.model.current_minute - self.order_minute
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
        self.waiting_time = self.model.current_minute - self.order_minute
        self.satisfaction = max(0, 100 - (self.waiting_time * 2))  # Decrease by 2 points per minute
        total_payment = self.bill + self.tip

        if not hasattr(self.model, 'profit'):
            self.model.profit = 0  # Ensure profit exists

        self.model.profit += total_payment  # Add payment to model's profit
        # print(f"Customer paid: {total_payment}")  # Add debug print
        return total_payment

    def leave_without_paying(self):
        """Leave restaurant due to excessive waiting time"""
        # Find waiters in the model's agent list
        waiters = self.model.agents.select(lambda x: hasattr(x, 'carrying_food'))

        # Notify waiters carrying food for this customer
        for waiter in waiters:
            for i, (customer, food_type) in enumerate(waiter.carrying_food):
                if customer == self:
                    # Mark food as available for reassignment
                    waiter.carrying_food[i] = (None, food_type)
                    # print(
                     #   f"Waiter {waiter.unique_id} notified: Customer {self.unique_id} left, will reassign their {food_type}")

        self.satisfaction = 0
        self.tip = 0
        self.model.customers_left_without_paying += 1
        # print(f"Customer left without paying at minute {self.model.current_minute}. Wait time: {self.waiting_time}")
        self.model.remove_customer(self)

    def leave_restaurant(self):
        """Leave restaurant after dining"""
        payment = self.rate_and_pay()
        self.model.customers_paid += 1
        # print(f"Customer paid ${payment:.2f} at minute {self.model.current_minute}. Wait time: {self.waiting_time}")

        # Clean up references in waiters' carrying lists
        waiters = self.model.agents.select(lambda x: hasattr(x, 'carrying_food'))

        for waiter in waiters:
            for i, (customer, food_type) in enumerate(waiter.carrying_food):
                if customer == self:
                    waiter.carrying_food[i] = (None, food_type)

        # Remove reference to undefined self.waiter
        if self.assigned_waiter:
            for waiter in self.assigned_waiter:
                waiter.update_performance_metrics(self)

        self.model.remove_customer(self)
