import mesa
from ..agents.customer_agent import CustomerAgent
from ..agents.manager_agent import ManagerAgent
from ..agents.waiter_agent import WaiterAgent
import random

Coordinate = tuple[int, int]

class RestaurantGrid(mesa.space.MultiGrid):

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

    # def debug_print(self):
    #    """Print grid layout for debugging"""
    #    print("\nGrid layout:")
    #    for y in range(self.height):
    #        row = []
    #        for x in range(self.width):
    #            pos = (x, y)
    #            if pos == self.layout.get('kitchen'):
    #                row.append('K')
    #            elif pos in self.layout.get('tables', set()):
    #                row.append('T')
    #            elif pos in self.layout.get('walkways', set()):
    #                row.append('W')
    #            else:
    #                row.append('E')
    #        print(' '.join(row))

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
    
    def place_agent(self, agent: mesa.Agent, pos: Coordinate) -> None:
        """Place the agent at the specified location, and set its pos variable."""
        x, y = pos
        # First check if cell is physically occupied
        if agent.pos is None or agent not in self._grid[x][y]:
            self._grid[x][y].append(agent)
            agent.pos = pos

            if self._empties_built:
                self._empties.discard(pos)
            if isinstance(agent, CustomerAgent):
                self._empties_customers.discard(pos)
            else:
                self._empties_workers.discard(pos)
            self._empty_mask[agent.pos] = True
        else:
            raise Exception("Cell not valid for this agent type: Position " + str(pos) + ", Agent " + str(agent))

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
        self._empty_mask[agent.pos] = False
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
