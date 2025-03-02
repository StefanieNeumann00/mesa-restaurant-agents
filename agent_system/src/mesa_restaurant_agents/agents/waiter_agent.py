from ..utils.order_status import OrderStatus
from ..agents.customer_agent import CustomerAgent
import mesa


class WaiterAgent(mesa.Agent):
    def __init__(self, model):
        super().__init__(model)
        # Initialize waiter properties
        self.model = model  # Current serving status
        self.carrying_food = []  # List of orders currently being carried
        self.max_carry = 2  # Maximum number of food items that can be carried
        self.tips = 0  # Total tips received
        self.avg_rating = 0  # Average rating from customers
        self.ratings_count = 0  # Number of ratings received
        self.served_customers = 0  # Total customers served
        self.target_pos = None  # Target position to move towards
        self.current_pos = None  # Current position of the waiter

    def can_pick_up_food(self, customer, order):
        """Check if the waiter can pick up more food and if the order is valid"""
        if len(self.carrying_food) >= self.max_carry:
            return False
        return True

    def pick_up_food(self, customer, order):
        """Add an order to the waiter's carrying load"""
        if self.can_pick_up_food():
            self.carrying_food.append((customer, order))
            return True
        return False

    def is_ordered(self, agent):
        return (hasattr(agent, "order_status") and
                agent.order_status == OrderStatus.ORDERED)

    def get_best_customer(self):
        """Find the best customer to serve based on food being carried."""
        if not self.carrying_food:
            return None

        # Get all customer agents
        customers = self.model.agents.select(agent_type=CustomerAgent)
        customers = [c for c in customers if c.pos is not None]

        # First priority: serve customers we have specific food for
        for customer, order in self.carrying_food:
            if customer and customer in customers and not customer.assigned_waiter:
                customer.assigned_waiter.append(self)
                return customer

            # Second priority: find customers waiting longest for food types we're carrying
        reassignable_foods = [order for customer, order in self.carrying_food if customer is None]
        if reassignable_foods:
            waiting_customers = [
                agent for agent in customers
                if (self.is_ordered(agent) and
                    agent.food_preference in reassignable_foods and
                    not agent.assigned_waiter)
            ]

            # Return customer with the longest waiting time
            if waiting_customers:
                customer = max(waiting_customers, key=lambda c: c.waiting_time)
                customer.assigned_waiter.append(self)
                return customer

        return None

    def get_next_position(self):
        """Get next position that is empty and within movement constraints"""
        possible_moves = self.model.grid.get_neighborhood(
            self.pos,
            moore=True,  # allow diagonal movement
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
            if self.model.grid.is_cell_empty(pos) and (pos in self.model.grid.layout['walkways'] or
                                                       pos == self.model.grid.layout['kitchen'])
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

    def move(self, steps=8):
        """Move towards target position, avoiding obstacles"""
        initial_pos = self.pos
        for _ in range(steps):
            next_pos = self.get_next_position()
            if next_pos == self.pos:  # No valid moves left
                break
            self.model.grid.move_agent(self, next_pos)
        print(f"Waiter {self.unique_id} moved from {initial_pos} to {self.pos}")

    def get_kitchen_pos(self):
        return self.model.grid.layout['kitchen']

    def step(self):
        if not self.carrying_food:
            # Priority 1: Pick up prepared orders from kitchen
            kitchen_pos = self.get_kitchen_pos()
            print(f"Waiter {self.unique_id} heading to kitchen at {kitchen_pos}, current pos: {self.pos}")
            self.target_pos = kitchen_pos

            if self.pos == kitchen_pos:
                # Already at kitchen, try to pick up orders
                if self.model.kitchen.prepared_orders:
                    print(
                        f"Waiter {self.unique_id} at kitchen. Orders available: {len(self.model.kitchen.prepared_orders)}")
                    self.pick_up_prepared_orders()
                    print(f"Waiter {self.unique_id} picked up: {len(self.carrying_food)} orders")
                    # Release kitchen access when done
                    self.model.release_kitchen_access(self)
            else:
                # Need to move to the kitchen
                next_pos = self.get_next_position()
                # Check if next move is to kitchen
                if next_pos == kitchen_pos:
                    # Try to reserve kitchen access
                    if self.model.reserve_kitchen_access(self):
                        # We have permission to enter kitchen
                        self.model.grid.move_agent(self, next_pos)
                    else:
                        # Kitchen is occupied, stay in place
                        print(f"Waiter {self.unique_id} waiting for kitchen access")
                else:
                    # Normal movement (not to kitchen)
                    self.move()
        else:
            # Priority 2: Deliver food to customers
            customer = self.get_best_customer()
            if customer and customer.pos is not None:  # Check if customer and pos exist
                print(f"Waiter {self.unique_id} carrying food, heading to customer at {customer.pos}")
                self.target_pos = customer.pos

                # Direct check if adjacent to customer
                if self.pos in self.model.grid.get_neighborhood(
                        customer.pos, moore=False, include_center=True
                ):
                    self.serve_dish(customer)
                else:
                    self.move()
            else:
                print(f"Waiter {self.unique_id} has food but no customer to serve")
                # Option: Find another customer or return to kitchen
                self.target_pos = self.get_kitchen_pos()
                self.move()

    def pick_up_prepared_orders(self):
        """Track kitchen order pickup"""
        print(f"Waiter {self.unique_id} attempting pickup:")
        print(f"- Kitchen has {len(self.model.kitchen.prepared_orders)} prepared orders")
        print(f"- Currently carrying: {len(self.carrying_food)}/{self.max_carry} orders")

        orders_picked = 0
        for customer, order in list(self.model.kitchen.prepared_orders.items())[:self.max_carry]:
            if self.can_pick_up_food(customer, order):
                self.carrying_food.append((customer, order))
                del self.model.kitchen.prepared_orders[customer]
                orders_picked += 1
                print(f"- Picked up order for customer {customer.unique_id}")

        print(f"- Total orders picked up: {orders_picked}")
        print(f"- Now carrying: {len(self.carrying_food)} orders")

    def serve_dish(self, target_customer):
        """Serve food to customer, including reassigned """
        # Try to serve food originally for this customer
        for i, (customer, order) in enumerate(self.carrying_food):
            if customer == target_customer:
                customer.order_status = OrderStatus.SERVED
                customer.assigned_waiter.append(self)
                self.served_customers += 1
                print(f"Waiter {self.unique_id} served customer at minute "
                      f"{self.model.current_minute}. Customer waited {customer.waiting_time} minutes.")
                self.carrying_food.remove((customer, order))  # Remove customer from carrying list
                return True

        # Try to serve reassigned food
        for i, (customer, order) in enumerate(self.carrying_food):
            if customer is None and order == target_customer.food_preference:
                target_customer.order_status = OrderStatus.SERVED
                target_customer.assigned_waiter.append(self)
                self.served_customers += 1
                print(f"Waiter {self.unique_id} served reassigned {order} to customer at minute "
                      f"{self.model.current_minute}. Customer waited {target_customer.waiting_time} minutes.")
                self.carrying_food.pop(i)
                return True

        return False

    def update_performance_metrics(self, customer):
        tip = customer.tip
        self.tips += tip
