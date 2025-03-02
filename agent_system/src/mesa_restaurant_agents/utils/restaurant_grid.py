import mesa
from ..agents.customer_agent import CustomerAgent
from ..agents.manager_agent import ManagerAgent
from ..agents.waiter_agent import WaiterAgent
from ..utils.environment_definition import EnvironmentDefinition
import random
import numpy as np

Coordinate = tuple[int, int]

class RestaurantGrid(mesa.space.SingleGrid):

    def __init__(self, width, height, kitchen_pos):
        super().__init__(width, height, True)
        self.layout = {
            'kitchen': kitchen_pos,
            'walkways': set(),
            'tables': set()
        }

        self._setup_restaurant_layout()
        self._empties_workers = self.layout['walkways'].copy()  # Use copy to avoid reference issues
        self._empties_customers = self.layout['tables'].copy()

    def _setup_restaurant_layout(self):
        """Setup restaurant layout with walkways, tables, and kitchen"""
        # First, create sets for all types
        walkways = set()
        tables = set()

        # Define kitchen position
        kitchen_x = (self.width // 2) + 2 if self.width % 2 == 1 else (self.width // 2) + 2
        kitchen_y = (self.height // 2) + 2 if self.height % 2 == 1 else (self.height // 2) + 2
        self.layout['kitchen'] = (kitchen_x, kitchen_y)

        # Fill all positions
        for y in range(self.height):
            for x in range(self.width):
                pos = (x, y)
                # Skip kitchen position
                if pos == self.layout['kitchen']:
                    continue
                # Place tables on odd coordinates
                if x % 2 == 1 and y % 2 == 1:
                    tables.add(pos)
                # All other positions are walkways
                else:
                    walkways.add(pos)

        # Update layout
        self.layout['walkways'] = walkways
        self.layout['tables'] = tables

        # Validate total cell count
        total_cells = len(walkways) + len(tables) + 1  # +1 for kitchen
        if total_cells != self.width * self.height:
            raise ValueError(f"Invalid cell count: {total_cells} vs {self.width * self.height}")

    def debug_print(self):
        """Print grid layout for debugging"""
        print("\nGrid layout:")
        for y in range(self.height):
            row = []
            for x in range(self.width):
                pos = (x, y)
                if pos == self.layout.get('kitchen'):
                    row.append('K')
                elif pos in self.layout.get('tables', set()):
                    row.append('T')
                elif pos in self.layout.get('walkways', set()):
                    row.append('W')
                else:
                    row.append('E')
            print(' '.join(row))

    def position_randomly(self, agent):
        if isinstance(agent, CustomerAgent) and self._empties_customers:
            pos = random.choice(list(self._empties_customers))
            self.place_agent(agent=agent, pos=pos)
            return True
        elif (isinstance(agent, WaiterAgent) or isinstance(agent, ManagerAgent)) and self._empties_workers:
            pos = random.choice(list(self._empties_workers))
            self.place_agent(agent=agent, pos=pos)
            return True
        return False

    def is_cell_empty_for_agent(self, agent, pos):
        if isinstance(agent, CustomerAgent):
            return pos in self._empties_customers
        else:
            return pos in self._empties_workers or pos == self.layout['kitchen']
    
    def place_agent(self, agent: mesa.Agent, pos: Coordinate) -> None:
        """Place the agent at the specified location, and set its pos variable."""
        x, y = pos
        # First check if cell is physically occupied
        if self._grid[x][y] is not None:
            raise Exception("Cell not empty - already occupied by another agent")
        # Then check if position type is valid for this agent
        if self.is_cell_empty_for_agent(agent, pos):
            x, y = pos
            self._grid[x][y] = agent
            if self._empties_built:
                self._empties.discard(pos)
            if isinstance(agent, CustomerAgent):
                self._empties_customers.discard(pos)
            else:
                self._empties_workers.discard(pos)
            self._empty_mask[pos] = False
            agent.pos = pos
        else:
            raise Exception("Cell not valid for this agent type")

    def remove_agent(self, agent: mesa.Agent) -> None:
        """Remove the agent from the grid and set its pos attribute to None."""
        if (pos := agent.pos) is None:
            return
        x, y = pos
        self._grid[x][y] = self.default_val()
        if self._empties_built:
            self._empties.add(pos)
        if isinstance(agent, CustomerAgent):
            self._empties_customers.add(pos)
        else:
            self._empties_workers.add(pos)
        self._empty_mask[agent.pos] = True
        agent.pos = None

    def is_walkway(self, pos):
        """Check if a position is a walkway"""
        return pos in self.layout['walkways']
    
    def is_table(self, pos):
        """Check if a position is a walkway"""
        return pos in self.layout['tables']
    
    def is_kitchen(self, pos):
        """Check if a position is a walkway"""
        return pos == self.layout['kitchen']
    
    def visualize(self):
        environment = np.zeros((self.width, self.height))
        for cell_content, (x, y) in self.coord_iter():
            if cell_content:
                if isinstance(cell_content, CustomerAgent):
                    environment[x][y] = EnvironmentDefinition.CUSTOMER.value
                elif isinstance(cell_content, WaiterAgent):
                    environment[x][y] = EnvironmentDefinition.WAITER.value
                elif isinstance(cell_content, ManagerAgent):
                    environment[x][y] = EnvironmentDefinition.MANAGER.value
            elif self.is_kitchen((x,y)):
                environment[x][y] = EnvironmentDefinition.KITCHEN.value
            elif self.is_walkway((x,y)):
                environment[x][y] = EnvironmentDefinition.FREE.value
            elif self.is_table((x,y)):
                environment[x][y] = EnvironmentDefinition.FREE_TABLE.value

        annot = np.vectorize(EnvironmentDefinition.get_designations().get)(environment)

        return environment, annot

