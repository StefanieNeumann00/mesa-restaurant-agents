from ..utils.order_status import OrderStatus
from ..agents.customer_agent import CustomerAgent
import mesa


class WaiterAgent(mesa.Agent):
    def __init__(self, model):
        super().__init__(model)
        # Initialize waiter properties
        self.model = model  # Current serving status
        self.carrying_food = []  # List of orders currently being carried
        self.max_carry = 4  # Maximum number of food items that can be carried
        self.tips = 0  # Total tips received
        self.avg_rating = 0  # Average rating from customers
        self.ratings_count = 0  # Number of ratings received
        self.served_customers = 0  # Total customers served
        self.target_pos = None  # Target position to move towards
        self.current_pos = None  # Current position of the waiter
        self.previous_pos = None  # Previous position to avoid oscillation
        self.is_available = True
        self.assigned_shifts = []
        self.consecutive_days_worked = 0
        self.is_fulltime = True  # Default to fulltime

    def reset_availability(self):
        """Reset availability based on consecutive days worked"""
        if self.is_fulltime:
            if self.consecutive_days_worked >= 4:
                self.is_available = False
                self.consecutive_days_worked = 0
            else:
                self.is_available = True
        else:  # Part-time
            if self.consecutive_days_worked >= 2:
                self.is_available = False
                self.consecutive_days_worked = 0
            else:
                self.is_available = True

        # Clear shift assignments when resetting availability
        self.assigned_shifts = []

    def can_pick_up_food(self, customer=None, order=None):
        """Check if the waiter can pick up more food and if the order is valid"""
        return len(self.carrying_food) < self.max_carry

    def pick_up_food(self, customer, order):
        """Add an order to the waiter's carrying load"""
        if self.can_pick_up_food():
            self.carrying_food.append((customer, order))
            # print(f"Waiter {self.unique_id} picked up food: {self.carrying_food}")
        #else:
        # print(f"Waiter {self.unique_id} found no food to pick up.")

    def is_ordered(self, agent):
        return (hasattr(agent, "order_status") and
                agent.order_status == OrderStatus.ORDERED)

    def get_best_customer(self):
        """Find the best customer to serve based on food being carried."""
        # print(f"Waiter {self.unique_id} looking for best customer:")
        # print(f"Currently carrying: {[(c.unique_id if c else 'None', o) for c, o in self.carrying_food]}")

        ready_customers = [c for c in self.model.agents.select(agent_type=CustomerAgent)
                           if hasattr(c, "order_status") and
                           c.order_status == OrderStatus.ORDERED and
                           c.pos is not None and
                           not c.assigned_waiter]

        if not ready_customers:
            print("No ready customers found")
            return None

        # First priority: serve customers we have specific food for
        for customer, order in self.carrying_food:
            if customer and customer in ready_customers:
                # print(f"Found matching customer {customer.unique_id} for carried order")
                customer.assigned_waiter = [self]
                return customer

        # Second priority: find customers waiting longest for food types we're carrying
        reassignable_foods = [order for customer, order in self.carrying_food if customer is None]
        if reassignable_foods:
            # Find customers waiting for food types we're carrying
            matching_customers = [
                c for c in ready_customers
                if c.food_preference in reassignable_foods
            ]

            if matching_customers:
                # Get customer with the longest wait time
                best_customer = max(matching_customers, key=lambda c: c.waiting_time)
                # print(f"Reassigning food to customer {best_customer.unique_id} "
                #      f"(waiting time: {best_customer.waiting_time})")
                best_customer.assigned_waiter = [self]  # Reset assignment
                return best_customer

        # Sort by waiting time (descending) and then by distance (ascending)
        ready_customers.sort(key=lambda c: (
            -c.waiting_time,  # Negative to sort descending by waiting time
            self.manhattan_distance(self.pos, c.pos)  # Sort ascending by distance
        ))

        # Third priority: just take the customer that's been waiting longest
        if ready_customers:
            best_customer = ready_customers[0]
            # print(f"Selected customer {best_customer.unique_id} based on wait time "
            #      f"({best_customer.waiting_time}) and distance "
            #      f"({self.manhattan_distance(self.pos, best_customer.pos)})")
            best_customer.assigned_waiter = [self]
            return best_customer

        return None

    def move(self, steps=4):
        """Move towards the target position using A* pathfinding"""
        if not self.target_pos or self.pos == self.target_pos:
            return

        initial_pos = self.pos
        moves_made = 0

        while moves_made < steps:
            valid_moves = self.get_valid_moves_toward_target(self.target_pos)
            if not valid_moves:
                break
            # Store current position before moving
            self.previous_pos = self.pos
            # Take the first move (closest to target)
            new_pos = valid_moves[0]

            # Stop if we reached target or would overshoot
            if new_pos == self.target_pos or self.manhattan_distance(new_pos,
                                                                     self.target_pos) >= self.manhattan_distance(
                    self.pos, self.target_pos):
                self.model.grid.move_agent(self, new_pos)
                break

            self.model.grid.move_agent(self, new_pos)
            moves_made += 1

        if moves_made > 0:
           # print(f"Waiter {self.unique_id} moved from {initial_pos} to {self.pos}")
            return True

        return False

    def get_kitchen_pos(self):
        return self.model.grid.layout['kitchen']

    def get_valid_moves_toward_target(self, target_pos):
        """Get valid moves sorted by distance to target position"""
        # Get possible moves
        possible_moves = self.model.grid.get_neighborhood(
            self.pos, moore=True, include_center=False
        )

        # Filter valid moves (only walkways or kitchen)
        valid_moves = []
        for pos in possible_moves:
            is_walkable = (pos in self.model.grid.layout['walkways'] or
                           pos == self.model.grid.layout['kitchen'])
            if is_walkable:
                valid_moves.append(pos)

        # Sort by distance to target if we have valid moves
        if valid_moves and target_pos:
            return sorted(valid_moves,
                          key=lambda p: self.manhattan_distance(p, target_pos))

        return valid_moves

    def manhattan_distance(self, pos1, pos2):
        """Calculate Manhattan distance between two positions"""
        return abs(pos1[0] - pos2[0]) + abs(pos1[1] - pos2[1])

    def step(self):
        # First handle food delivery if carrying food
        if self.carrying_food:
            # If we already have a target customer, continue serving them
            if not self.target_pos:  # Only find new target if we don't have one
                customer = self.get_best_customer()
                if customer:
                    self.target_pos = customer.pos
                    # print(f"Waiter {self.unique_id} targeting customer {customer.unique_id} at {self.target_pos}")

            if self.target_pos:
                # Move toward current target
                self.move()

                # Check if we have a valid customer to deliver to
                cell_contents = self.model.grid.get_cell_list_contents(self.target_pos)
                customers = [obj for obj in cell_contents if isinstance(obj, CustomerAgent)]
                if customers and self.pos in self.model.grid.get_neighborhood(
                        self.target_pos, moore=True, include_center=False):
                    self.serve_dish(customers[0])
                    self.target_pos = None  # Reset target after serving

        else:
            # No food - handle kitchen operations
            kitchen_pos = self.get_kitchen_pos()
            if self.pos == kitchen_pos:
                if self.model.kitchen.prepared_orders:
                    self.pick_up_prepared_orders()
                    # Immediately find customer after pickup
                    customer = self.get_best_customer()
                    if customer:
                        self.target_pos = customer.pos
                    self.model.release_kitchen_access(self)
            else:
                self.target_pos = kitchen_pos
                self.move()

    def pick_up_prepared_orders(self):
        """Track kitchen order pickup"""
       # print(f"Waiter {self.unique_id} attempting pickup:")
       # print(f"- Kitchen has {len(self.model.kitchen.prepared_orders)} prepared orders")
       # print(f"- Currently carrying: {len(self.carrying_food)}/{self.max_carry} orders")

        orders_picked = 0
        for customer, order in list(self.model.kitchen.prepared_orders.items())[:self.max_carry]:
            if self.can_pick_up_food(customer, order):
                self.carrying_food.append((customer, order))
                del self.model.kitchen.prepared_orders[customer]
                orders_picked += 1
               # print(f"- Picked up order for customer {customer.unique_id}")

       # print(f"- Total orders picked up: {orders_picked}")
       # print(f"- Now carrying: {len(self.carrying_food)} orders")

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
