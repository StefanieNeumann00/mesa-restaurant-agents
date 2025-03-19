import pandas as pd
import matplotlib.pyplot as plt
from matplotlib import animation
import plotly.express as px
import seaborn as sns
import matplotlib.colors as mcolors
import numpy as np
from .utils.environment_definition import EnvironmentDefinition


def display_mean_step_results(results):
    df = pd.DataFrame(results)

    # Convert steps to time of day
    df['Time'] = df['Step'].apply(lambda x: pd.Timestamp('2024-01-01 11:00:00') + pd.Timedelta(minutes=x * 5))

    data_grouped = df.groupby(['Time']).agg(
        mean_customer_count=('Customer_Count', 'mean'),
        mean_waiting_time=('Average_Wait_Time', 'mean'),
        mean_customer_satisfaction=('Average_Customer_Satisfaction', 'mean'),
        mean_profit=('Profit', 'mean')).reset_index()

    # Plotting the data in one plot
    fig, ax1 = plt.subplots(figsize=(15, 10))

    ax1.plot(data_grouped['Time'], data_grouped['mean_customer_count'], marker='o', label='Customer Count')
    ax1.plot(data_grouped['Time'], data_grouped['mean_waiting_time'], marker='o', label='Average Wait Time')
    ax1.plot(data_grouped['Time'], data_grouped['mean_customer_satisfaction'], marker='o',
             label='Average Customer Satisfaction')
    ax1.plot(data_grouped['Time'], data_grouped['mean_profit'], marker='o', label='Profit')

    ax1.set_title('Model Output Data over Steps')
    ax1.set_xlabel('Time of Day')
    ax1.set_ylabel('Values')
    ax1.legend()

    plt.xticks(rotation=45)
    plt.tight_layout()  # Adjust layout to prevent label cutoff
    plt.show()
    return data_grouped


def display_first_run_step_results_customer(results):
    df = pd.DataFrame(results)
    data_first_run = df[df["RunId"] == 0]

    # Convert steps to time
    data_first_run['Time'] = data_first_run['Step'].apply(
        lambda x: pd.Timestamp('2024-01-01 11:00:00') + pd.Timedelta(minutes=x * 5))

    customer_infos_dict = dict(zip(data_first_run["Time"], data_first_run["Customer_Info"]))
    customer_infos_list = [{**item, 'time': k} for k, v in customer_infos_dict.items() for item in v]
    customer_infos_df = pd.DataFrame(customer_infos_list)

    plots = ['waiting_time', 'order_status', 'satisfaction']

    for plot in plots:
        fig = px.histogram(customer_infos_df, x="time", y=plot,
                           color='customer_nr', barmode='group',
                           height=400, nbins=len(customer_infos_df['time'].unique()))
        fig.update_xaxes(title_text='Time of Day')
        print(fig.show())
    return customer_infos_df


def display_first_run_step_results_waiter(results):
    df = pd.DataFrame(results)
    data_first_run = df[df["RunId"] == 0]

    data_first_run['Time'] = data_first_run['Step'].apply(
        lambda x: pd.Timestamp('2024-01-01 11:00:00') + pd.Timedelta(minutes=x * 5))

    waiter_infos_dict = dict(zip(data_first_run["Time"], data_first_run["Waiter_Info"]))
    waiter_infos_list = [{**item, 'time': k} for k, v in waiter_infos_dict.items() for item in v]
    waiter_infos_df = pd.DataFrame(waiter_infos_list)

    waiter_infos_df

    plots = ['tips', 'served_customers']
    for plot in plots:
        fig = px.histogram(waiter_infos_df, x="time", y=plot,
                            color='waiter_nr', barmode='group',
                            height=400, nbins=len(waiter_infos_df['time'].unique()))
        print(fig.show())
    return waiter_infos_df


class GridAnimator:
    def __init__(self, results):
        df = pd.DataFrame(results)
        data_first_run = df[df["RunId"] == 0]
        self.step_data = data_first_run.to_dict('records')
        self.grid_width = results[0]['grid_width']  # Set based on your model parameters
        self.grid_height = results[0]['grid_height']
        self.count = 0
        self.fig, self.ax = plt.subplots(figsize=(10, 10))
        self.init_ani()

    def _create_grid_frame(self, step_data):
        """Convert lightweight grid state to visualization format"""
        # Initialize grid with FREE value
        grid = np.ones((self.grid_width, self.grid_height)) * EnvironmentDefinition.FREE.value
        agent_counts = np.zeros((self.grid_width, self.grid_height))
        waiter_nrs = np.zeros((self.grid_width, self.grid_height))

        # Handle GridState first (agents and static objects)
        for cell in reversed(step_data['GridState']):
            x, y = cell['pos']
            # Skip if coordinates are out of bounds
            if x >= self.grid_width or y >= self.grid_height:
                continue

            cell_type = cell['type']
            if cell_type == 'Table':
                grid[x][y] = EnvironmentDefinition.FREE_TABLE.value
            elif cell_type == 'Kitchen':
                grid[x][y] = EnvironmentDefinition.KITCHEN.value

        # Then add agents in a second pass to ensure they're not overwritten
        for cell in step_data['GridState']:
            x, y = cell['pos']
            # Skip if coordinates are out of bounds
            if x >= self.grid_width or y >= self.grid_height:
                continue

            cell_type = cell['type']
            if cell_type== 'CustomerAgent':
                grid[x][y] = EnvironmentDefinition.CUSTOMER.value
                agent_counts[x][y] += 1
            elif cell_type == 'WaiterAgent':
                grid[x][y] = EnvironmentDefinition.WAITER.value
                agent_counts[x][y] += 1
                waiter_nrs[x][y] = cell['nr']
            elif cell_type == 'ManagerAgent':
                grid[x][y] = EnvironmentDefinition.MANAGER.value
                agent_counts[x][y] += 1

        return grid, agent_counts, waiter_nrs

    def visualize_grid(self, step_data):
        grid, agent_counts, waiter_nrs = self._create_grid_frame(step_data)
        #annot = np.vectorize(EnvironmentDefinition.get_designations().get)(grid)
        annot = np.empty_like(grid, dtype=object)
        for x in range(self.grid_width):
            for y in range(self.grid_height):
                annot[x][y] = EnvironmentDefinition.get_designations().get(grid[x][y], "")
                if agent_counts[x][y] > 1:
                    annot[x][y] += f"({int(agent_counts[x][y])})"
                elif waiter_nrs[x][y] > 0:
                    annot[x][y] += f"{int(waiter_nrs[x][y])}"
        cmap = mcolors.ListedColormap(['#F5F5F5', '#DEB887', '#FFFFFF', '#4169E1', '#FF8C00', '#8B0000'])
        sns.heatmap(grid, ax=self.ax, cmap=cmap, annot=annot, cbar=False, square=True, fmt="")

    def init_ani(self):
        self.ax.clear()
        self.visualize_grid(self.step_data[0])
        self.count += 1
        return self.ax

    def animate(self, i):
        self.ax.clear()
        self.visualize_grid(self.step_data[i])
        return self.ax

    def animate_first_run(self):
        ani = animation.FuncAnimation(
            self.fig,
            self.animate,
            init_func=self.init_ani,
            frames=len(self.step_data) - 1,
            repeat=False
        )
        return ani
