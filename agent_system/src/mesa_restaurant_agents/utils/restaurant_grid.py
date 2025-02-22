import mesa
Coordinate = tuple[int, int]
from ..agents.customer_agent import CustomerAgent
from ..agents.manager_agent import ManagerAgent
from ..agents.waiter_agent import WaiterAgent
from ..utils.environment_definition import EnvironmentDefinition
import random
import numpy as np

class RestaurantGrid(mesa.space.SingleGrid):

    def __init__(self, width, height, kitchen_pos):
        super().__init__(width, height, True)
        self.grid_width = width
        self.grid_height = height
        self.layout = {
            'kitchen': kitchen_pos,
            'walkways': set(),
            'tables': set()
        }

        self._setup_restaurant_layout()
        self._empties_workers = self.layout['walkways']
        self._empties_customers = self.layout['tables']

    def _setup_restaurant_layout(self):
        for x in range(self.grid_width):
            for y in range(self.grid_height):
                pos = (x, y)
                # Tables are placed on odd coordinates, not on edges
                if (y % 2 != 0 and x % 2 != 0 and
                        x != self.grid_width - 1 and y != self.grid_height - 1 and (x,y) != self.layout['kitchen']):
                    self.layout['tables'].add(pos)
                else:
                    self.layout['walkways'].add(pos)

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

    def is_cell_empty(self, agent, pos):
        if isinstance(agent, CustomerAgent):
            return pos in self._empties_customers
        else:
            return pos in self._empties_workers
    
    def place_agent(self, agent: mesa.Agent, pos: Coordinate) -> None:
        """Place the agent at the specified location, and set its pos variable."""
        if self.is_cell_empty(agent, pos):
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
            raise Exception("Cell not empty")

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
            if len(cell_content) > 0:
                if isinstance(cell_content[0], CustomerAgent):
                    environment[x][y] = EnvironmentDefinition.CUSTOMER.value
                elif isinstance(cell_content[0], WaiterAgent):
                    environment[x][y] = EnvironmentDefinition.WAITER.value
                elif isinstance(cell_content[0], ManagerAgent):
                    environment[x][y] = EnvironmentDefinition.MANAGER.value
            elif self.is_walkway((x,y)):
                environment[x][y] = EnvironmentDefinition.FREE.value
            elif self.is_table((x,y)):
                environment[x][y] = EnvironmentDefinition.FREE_TABLE.value
            elif self.is_kitchen((x,y)):
                environment[x][y] = EnvironmentDefinition.KITCHEN.value

        annot = np.vectorize(EnvironmentDefinition.get_designations().get)(environment)

        return environment, annot

