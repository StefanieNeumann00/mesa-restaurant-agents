from ..utils.order_status import OrderStatus, food_options
from ..agents.customer_agent import CustomerAgent
import mesa

class WaiterAgent(mesa.Agent):
    def __init__(self, model):
        super().__init__(model)
        # Initialize waiter properties
        self.model = model            # Current serving status
        self.busy = False
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

    def get_next_position(self):
        current_pos = self.pos
        if not self.target_pos:
            return self.get_kitchen_pos()

        # Get neighboring walkway cells
        neighbors = self.model.grid.get_neighborhood(
            current_pos,
            moore=False,  # Use von Neumann neighborhood (no diagonals)
            include_center=False
        )

        # Filter valid moves (only walkways)
        valid_moves = [
            pos for pos in neighbors
            if pos in self.model.layout['walkways']
        ]

        if not valid_moves:
            return current_pos

        # Move towards target using Manhattan distance
        distances = [
            (abs(pos[0] - self.target_pos[0]) +
             abs(pos[1] - self.target_pos[1]), pos)
            for pos in valid_moves
        ]
        return min(distances, key=lambda x: x[0])[1]

    def move(self):
        next_pos = self.get_next_position()
        self.model.grid.move_agent(self, next_pos)

    def get_kitchen_pos(self):
        return self.model.layout['kitchen']

    def step(self):
        if self.carrying_food:  # Have food to deliver
            # Find target customer's table position
            customer = self.get_best_customer()
            if customer:
                table_pos = customer.pos
                self.target_pos = table_pos

                # If next to table, serve food
                if self.pos in self.model.grid.get_neighborhood(
                        table_pos, moore=False, include_center=True
                ):
                    self.serve_dish(customer)
                else:
                    self.move()

        elif self.current_orders:  # Need to get food from kitchen
            self.target_pos = self.get_kitchen_pos()

            # If at kitchen, pick up food
            if self.pos == self.get_kitchen_pos():
                for customer, order in self.current_orders.items():
                    if self.can_pick_up_food():
                        self.pick_up_food(order)
            else:
                self.move()

        else:  # Look for customers to serve
            customer = self.get_best_customer()
            if customer:
                table_pos = customer.pos
                self.target_pos = table_pos

                # If next to table, take order
                if self.pos in self.model.grid.get_neighborhood(
                        table_pos, moore=False, include_center=True
                ):
                    self.take_order(customer)
                else:
                    self.move()

    def serve_dish(self, customer):
        customer.order_status = OrderStatus.SERVED
        customer.assigned_waiter.append(self)
        self.served_customers += 1

    def update_performance_metrics(self, customer):
        tip = customer.tip
        self.tips += tip