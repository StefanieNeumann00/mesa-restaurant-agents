from ..utils.order_status import OrderStatus, food_options
from ..agents.customer_agent import CustomerAgent
import mesa
import heapq

class WaiterAgent(mesa.Agent):
    def __init__(self, model):
        super().__init__(model)
        # Initialize waiter properties
        self.model = model               # Current serving status
        self.carrying_food = []          # List of orders currently being carried
        self.max_carry = 2               # Maximum number of food items that can be carried
        self.tips = 0                    # Total tips received
        self.avg_rating = 0              # Average rating from customers
        self.ratings_count = 0           # Number of ratings received
        self.served_customers = 0        # Total customers served
        self.target_pos = None           # Target position to move towards

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
        """Returns the first customer with a pending order"""
        customers_ordered = [
            agent for agent in self.model.agents
            if isinstance(agent, CustomerAgent) and agent.order_status == OrderStatus.ORDERED
        ]
        return customers_ordered[0] if customers_ordered else None

    def get_next_position(self):
        """Get next position that is empty and within movement constraints"""
        possible_moves = self.model.grid.get_neighborhood(
            self.pos,
            moore=False,  # allow diagonal movement
            include_center=False  # Do not include current position
        )

        # print(f"All possible moves from {self.pos}: {possible_moves}")
        # print(f"Moves that are walkways: {[m for m in possible_moves if m in self.model.grid.layout['walkways']]}")

        if not self.target_pos:
            return self.get_kitchen_pos()

            # # Debug prints to check walkways
            # print(f"Current pos: {self.pos}")
            # print(f"Possible moves: {possible_moves}")
            # print(f"Target pos: {self.target_pos}")
            # print(f"Walkways available: {[pos for pos in possible_moves if pos in self.model.grid.layout['walkways']]}")

        # Filter valid moves (only walkways)
        valid_moves = [
            pos for pos in possible_moves
            if self.model.grid.is_cell_empty(pos) and pos in self.model.grid.layout['walkways']
        ]

        # print(f"Valid moves: {valid_moves}")

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
            # print(f"Chosen move: {next_pos}")
            return next_pos

        return self.pos  # Stay in place if no valid moves

    def move(self):
        next_pos = self.get_next_position()
        self.model.grid.move_agent(self, next_pos)

    def get_kitchen_pos(self):
        return self.model.grid.layout['kitchen']

    def step(self):
        if not self.carrying_food:
            # Priority 1: Pick up prepared orders from kitchen
            print(f"Waiter {self.unique_id} heading to kitchen at {self.pos}")
            self.target_pos = self.get_kitchen_pos()
            if self.pos == self.target_pos and self.model.kitchen.prepared_orders:
                print(
                    f"Waiter {self.unique_id} at kitchen. Orders available: {len(self.model.kitchen.prepared_orders)}")
                self.pick_up_prepared_orders()
                print(f"Waiter {self.unique_id} picked up: {len(self.carrying_food)} orders")
            else:
                self.move()
        else:
            # Priority 2: Deliver food to customers
            customer = self.get_best_customer()
            if customer:
                print(f"Waiter {self.unique_id} carrying food, heading to customer at {customer.pos}")
                self.target_pos = customer.pos
                if self.is_adjacent_to_target():
                    self.serve_dish(customer)
                else:
                    self.move()
            else:
                print(f"Waiter {self.unique_id} has food but no customer to serve")

    def pick_up_prepared_orders(self):
        """Track kitchen order pickup"""
        print(f"Waiter {self.unique_id} attempting pickup:")
        print(f"- Kitchen has {len(self.model.kitchen.prepared_orders)} prepared orders")
        print(f"- Currently carrying: {len(self.carrying_food)}/{self.max_carry} orders")

        orders_picked = 0
        for customer, order in list(self.model.kitchen.prepared_orders.items())[:self.max_carry]:
            if self.can_pick_up_food():
                self.carrying_food.append((customer, order))
                del self.model.kitchen.prepared_orders[customer]
                orders_picked += 1
                print(f"- Picked up order for customer {customer.unique_id}")

        print(f"- Total orders picked up: {orders_picked}")
        print(f"- Now carrying: {len(self.carrying_food)} orders")

    def is_adjacent_to_target(self):
        return self.pos in self.model.grid.get_neighborhood(
            self.target_pos, moore=False, include_center=True
        )

    def serve_dish(self, target_customer):
        """Serve food to customer"""
        for customer, order in self.carrying_food:
            if customer == target_customer:
                customer.order_status = OrderStatus.SERVED
                customer.assigned_waiter.append(self)
                self.served_customers += 1
                print(f"Waiter {self.unique_id} served customer at minute "
                      f"{self.model.current_minute}. Customer waited {customer.waiting_time} minutes.")
                self.carrying_food.remove(customer, order)  # Remove customer from carrying list
                return True
        return False

    def update_performance_metrics(self, customer):
        tip = customer.tip
        self.tips += tip