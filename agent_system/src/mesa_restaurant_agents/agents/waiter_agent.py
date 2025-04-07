from ..utils.order_status import OrderStatus
from ..agents.customer_agent import CustomerAgent
from ..utils.order_status import food_options

import mesa


class WaiterAgent(mesa.Agent):
    def __init__(self, model):
        super().__init__(model)
        # Initialize waiter properties
        self.carrying_food = []  # List of orders currently being carried
        self.max_carry = 4  # Maximum number of food items that can be carried
        self.tips = 0  # Total tips received
        self.served_customers = 0  # Total customers served
        self.target_pos = None  # Target position to move towards
        self.previous_pos = None  # Previous position to avoid oscillation
        self.is_available = True

    def __str__(self):
        if hasattr(self, 'display_name'):
            return f"Waiter {self.display_name}"
        else:
            return f"Waiter {self.unique_id}"

    def can_pick_up_food(self, customer=None, order=None):
        """Check if the waiter can pick up more food and if the order is valid"""
        return len(self.carrying_food) < self.max_carry

    def move(self, steps=8):
        """Move towards the target position using A* pathfinding"""
        if not self.target_pos or self.pos == self.target_pos:
            return

        initial_pos = self.pos
        moves_made = 0

        while moves_made < steps:
            if self.pos == self.target_pos:
                break

            valid_moves = self.get_valid_moves_toward_target(self.target_pos)
            if not valid_moves:
                break

            # Store current position before moving
            self.previous_pos = self.pos
            # Take the first move (closest to target)
            new_pos = valid_moves[0]

            self.model.grid.move_agent(self, new_pos)
            moves_made += 1

            # Stop if we reached target
            if new_pos == self.target_pos:
                break

        if moves_made > 0:
            print(f"Waiter {self.unique_id} moved from {initial_pos} to {self.pos}, steps: {moves_made}")
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

            # Sort by distance to target if we have valid moves
            if is_walkable and pos != self.previous_pos:
                valid_moves.append(pos)

        # Sort by Manhattan distance to target
        if valid_moves and target_pos:
            return sorted(valid_moves, key=lambda p: self.manhattan_distance(p, target_pos))

        return valid_moves

    def manhattan_distance(self, pos1, pos2):
        """Calculate Manhattan distance between two positions"""
        if pos1 and pos2:
            return abs(pos1[0] - pos2[0]) + abs(pos1[1] - pos2[1])
        return 1000

    def step(self):
        """Main step function for the waiter agent"""
        # Carrying food - focus on delivery
        if len(self.carrying_food) > 0:
            # Already carrying food - prioritize delivery
            if self.target_pos is None:
                # Find the customer we're carrying food for
                for customer, order in self.carrying_food:
                    if customer is not None:
                        customer_pos = getattr(customer, 'pos', None)
                        if customer_pos:
                            self.target_pos = customer_pos
                            break

                # Second priority: find customer for reassignable food
                if self.target_pos is None:
                    target_customer = self.find_best_customer_for_existing_food()
                    if target_customer:
                        self.target_pos = target_customer.pos
                        print(
                            f"Waiter {self.unique_id} targeting customer {target_customer.unique_id} for reassignment")

            # Debug current state - moved here after target calculation
            print(f"DEBUG: Waiter {self.unique_id} step - available={self.is_available}, "
                  f"carrying_food={len(self.carrying_food)}, target_pos={self.target_pos}")

            # If we have a target, move toward it
            if self.target_pos:
                self.move()

                # Check if we're near the target to serve food
                cell_contents = self.model.grid.get_cell_list_contents([self.target_pos])
                customers = [obj for obj in cell_contents if isinstance(obj, CustomerAgent)]

                if customers and self.pos in self.model.grid.get_neighborhood(
                        self.target_pos, moore=True, include_center=False):
                    # Try to serve food
                    served = self.serve_dish(customers[0])

                    # Only reset target if we've served all food or need a new target
                    if served and not self.carrying_food:
                        self.target_pos = None  # Go back to kitchen
                    elif served:
                        # We served but still have food - find next target immediately
                        self.target_pos = None
                        self.step()  # Recursively find next target
                        return

        else:
            # No food - handle kitchen operations
            if self.pos == self.get_kitchen_pos():
                self.pick_up_prepared_orders()
                # If we got food, find a target immediately
                if self.carrying_food:
                    self.target_pos = None
                    self.step()  # Recursively find next target
            else:
                # Not at kitchen and not carrying food - go to kitchen
                self.target_pos = self.get_kitchen_pos()
                self.move()

    def find_best_customer_for_existing_food(self):
        """Find the best customer to serve with food we're already carrying"""
        # First, check if assigned customers still exist and update food status
        for i, (customer, order) in enumerate(self.carrying_food):
            if customer is not None:
                # Check if customer is still in the model and still waiting for food
                customer_exists = customer in self.model.agents.select(agent_type=CustomerAgent)

                if not customer_exists or customer.order_status not in [OrderStatus.ORDERED, OrderStatus.DELIVERING]:
                    print(
                        f"DEBUG: Waiter {self.unique_id} marking {order} as reassignable - customer "
                        f"{customer.unique_id if hasattr(customer, 'unique_id') else 'None'} no longer valid")
                    self.carrying_food[i] = (None, order)  # Mark as reassignable

        # Count reassignable food
        reassignable_food = [(i, order) for i, (cust, order) in enumerate(self.carrying_food) if cust is None]
        print(
            f"DEBUG: Waiter {self.unique_id} has {len(reassignable_food)} "
            f"reassignable food items: {[f[1] for f in reassignable_food]}")

        # If food not reassignable after checking, discard stuck food items
        if len(reassignable_food) == 0 and len(self.carrying_food) > 0:
            print(
                f"DEBUG: Waiter {self.unique_id} discarding undeliverable food: {[order for _, order in self.carrying_food]}")
            self.carrying_food = []
            self.target_pos = None
            return None

        ready_customers = [c for c in self.model.agents.select(agent_type=CustomerAgent)
                           if c.order_status in [OrderStatus.ORDERED, OrderStatus.DELIVERING]
                           and not c.assigned_waiter]

        print(f"DEBUG: Found {len(ready_customers)} potential customers for reassignment")

        if not ready_customers:
            return None

        customer_scores = []
        matched_orders = {}  # Keep track of which order matched which customer

        for customer in ready_customers:
            # Check if customer's preference matches any reassignable food
            for i, order in reassignable_food:
                if order == customer.food_preference:
                    waiting_score = customer.waiting_time / 3
                    distance = self.manhattan_distance(self.pos, customer.pos)

                    # Lower distance penalty to ensure matches happen
                    distance_penalty = min(distance / 50, waiting_score * 0.3)

                    # High base score to prioritize any match
                    score = 100 + waiting_score - distance_penalty

                    customer_scores.append((customer, score, i, order))
                    break

        if customer_scores:
            customer_scores.sort(key=lambda x: x[1], reverse=True)
            best_customer, _, i, matched_order = customer_scores[0]
            best_customer.assigned_waiter = [self]

            # Update the carrying_food list with new customer
            self.carrying_food[i] = (best_customer, matched_order)

            print(f"DEBUG: Waiter {self.unique_id} found customer {best_customer.unique_id} for {matched_order}")
            return best_customer

        # No matches found - food is likely undeliverable
        print(f"DEBUG: Waiter {self.unique_id} couldn't find matching customers for reassignable food")
        return None

    def pick_up_prepared_orders(self):
        """Track kitchen order pickup"""
        orders_picked = 0
        available_slots = self.max_carry - len(self.carrying_food)

        if available_slots <= 0:
            return 0

        # Sort orders by customer waiting time (prioritize longest waiting customers)
        prioritized_orders = sorted(
            self.model.kitchen.prepared_orders.items(),
            key=lambda item: item[0].waiting_time if hasattr(item[0], 'waiting_time') else 0,
            reverse=True
        )

        for customer, order in prioritized_orders[:available_slots]:
            if self.can_pick_up_food(customer, order):
                # Update customer status to DELIVERING when food is picked up
                if customer.order_status == OrderStatus.ORDERED:
                    customer.order_status = OrderStatus.DELIVERING
                    customer.assigned_waiter = [self]

                self.carrying_food.append((customer, order))
                del self.model.kitchen.prepared_orders[customer]
                orders_picked += 1
                print(f"DEBUG: Waiter {self.unique_id} picked up {order} for customer {customer.unique_id}")

        return orders_picked

    def _mark_customer_served(self, customer):
        """Common code for marking a customer as served"""
        if customer:
            customer.order_status = OrderStatus.SERVED
            customer.assigned_waiter.append(self)
            self.served_customers += 1
            self.model.total_orders_served += 1

    def serve_dish(self, target_customer):
        """Serve food to customer, including reassigned """
        # First check if customer is in the right state to receive food
        if target_customer.order_status not in [OrderStatus.ORDERED, OrderStatus.DELIVERING]:
            print(f"Cannot serve to customer {target_customer.unique_id} with status {target_customer.order_status}")
            return False

        # Try to serve food originally for this customer
        for i, (customer, order) in enumerate(self.carrying_food):
            if customer == target_customer:
                # Only serve if customer is still waiting for food
                if customer is not None and customer.order_status in [OrderStatus.ORDERED, OrderStatus.DELIVERING]:
                    self._mark_customer_served(customer)

                    # Get price info for debug output
                    price = food_options.get(order, {}).get("price", 0)
                    print(f"DEBUG: Waiter {self.unique_id} served customer {customer.unique_id} - "
                          f"Order: {order}, Price: ${price:.2f}")

                    self.carrying_food.pop(i)  # Remove customer and order from carrying list
                    return True

                # Food can't be served to original customer, mark for reassignment
                print(f"DEBUG: Marking {order} for reassignment")
                self.carrying_food[i] = (None, order)
                continue

        # Try to serve reassigned food
        for i, (customer, order) in enumerate(self.carrying_food):
            if customer is None and order == target_customer.food_preference:
                # Only serve if customer is still waiting for food
                if target_customer.order_status in [OrderStatus.ORDERED, OrderStatus.DELIVERING]:
                    self._mark_customer_served(target_customer)

                    # Get price info for debug output
                    price = food_options.get(order, {}).get("price")
                    print(
                        f"DEBUG: Waiter {self.unique_id} served reassigned {order} "
                        f"to customer {target_customer.unique_id} - "
                        f"Price: ${price:.2f}")

                    # Remove the served food from carrying
                    self.carrying_food.pop(i)
                    return True

        return False

    def update_performance_metrics(self, customer):
        tip = customer.tip
        self.tips += tip
