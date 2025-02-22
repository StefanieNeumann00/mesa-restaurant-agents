from ..utils.order_status import OrderStatus, food_options
from ..agents.customer_agent import CustomerAgent
import mesa
import heapq

class WaiterAgent(mesa.Agent):
    def __init__(self, model):
        super().__init__(model)
        # Initialize waiter properties
        self.model = model            # Current serving status
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
        """Get next position that is empty and within movement constraints"""
        possible_moves = self.model.grid.get_neighborhood(
            self.pos,
            moore=True,  # allow diagonal movement
            include_center=False  # Do not include current position
        )

        if not self.target_pos:
            return self.get_kitchen_pos()

        print(f"Current pos: {self.pos}")
        print(f"Possible moves: {possible_moves}")
        print(f"Target pos: {self.target_pos}")

        # Filter valid moves (only walkways)
        valid_moves = [
            pos for pos in possible_moves
            if self.model.grid.is_cell_empty(pos) and pos in self.model.grid.layout['walkways']
        ]

        print(f"Valid moves: {valid_moves}")

        # Include edge positions if no valid moves found
        if not valid_moves:
            valid_moves = [
                pos for pos in possible_moves
                if self.model.grid.is_cell_empty(pos)
            ]

        if valid_moves:
            # Move towards target using Manhattan distance
            distances = [
                (abs(pos[0] - self.target_pos[0]) +
                 abs(pos[1] - self.target_pos[1]), pos)
                for pos in valid_moves
            ]
            next_pos = min(distances, key=lambda x: x[0])[1]
            print(f"Chosen move: {next_pos}")
            return next_pos

        return self.pos  # Stay in place if no valid moves

    def move(self):
        next_pos = self.get_next_position()
        self.model.grid.move_agent(self, next_pos)

    def get_kitchen_pos(self):
        return self.model.grid.layout['kitchen']

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

        else:  # Need to get food from kitchen
            self.target_pos = self.get_kitchen_pos()

            # If at kitchen, pick up food
            if self.pos == self.get_kitchen_pos():
                for customer, order in self.model.kitchen.prepared_orders.items():
                    if self.can_pick_up_food():
                        self.pick_up_food(order)
            else:
                self.move()

    def serve_dish(self, customer):
        customer.order_status = OrderStatus.SERVED
        customer.assigned_waiter.append(self)
        self.served_customers += 1

    def update_performance_metrics(self, customer):
        tip = customer.tip
        self.tips += tip