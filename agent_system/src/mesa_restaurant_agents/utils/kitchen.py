class Kitchen():
    
    def __init__(self, pos):
        self.pos = pos
        self.prepared_orders = {} #dict {customer:order}
        self.requested_orders = {} #dict {customer: {"order": order, "order_time": ordered_time}}

    def add_new_customer_order(self, customer, order, order_time):
        self.requested_orders[customer] = {"order": order, "order_time": order_time}

    def add_ready_orders_to_prepared(self, current_time):
        to_delete = []

        for customer, value in self.requested_orders.items():
            if ((current_time - value["order_time"]).total_seconds() % 3600) // 60 == 10:
                self.prepared_orders[customer] = value["order"]
                to_delete.append(customer)

        for customer in to_delete:
            del self.requested_orders[customer]