class Kitchen():
    
    def __init__(self, pos):
        self.pos = pos
        self.prepared_orders = {}   # dict {customer:order}
        self.requested_orders = {}  # dict {customer: {"order": order, "order_time": ordered_time}}
        self.prep_time = 10  # Minutes needed to prepare an order

    def add_new_customer_order(self, customer, order, order_minute):
        """Add new order to requested orders"""
        self.requested_orders[customer] = {
            "order": order,
            "order_minute": order_minute
        }

    def add_ready_orders_to_prepared(self, current_minute):
        """Move orders that are ready to prepared orders"""
        to_delete = []

        for customer, value in self.requested_orders.items():
            time_cooking = current_minute - value["order_minute"]
            if time_cooking >= self.prep_time:
                self.prepared_orders[customer] = value["order"]
                to_delete.append(customer)

        for customer in to_delete:
            del self.requested_orders[customer]