import pandas as pd
import matplotlib.pyplot as plt
from matplotlib import animation
import plotly.express as px
import seaborn as sns
import matplotlib.colors as mcolors
import numpy as np
import datetime
from .utils.environment_definition import EnvironmentDefinition


def minutes_to_time(row):
        hours = row['time'] // 60
        minutes = row['time'] % 60
        return f"{hours:02d}:{minutes:02d}"


def display_mean_step_results(results):
    df = pd.DataFrame(results)
    df = df[df["RunId"] == 0]
    df['hours'] = df.apply(minutes_to_time, axis=1)

    data_grouped = df.groupby(['day','hours']).agg(
        mean_customer_count=('Customer_Count', 'mean'),
        mean_waiters_count=('Waiters_Count', 'mean'),
        mean_waiting_time=('Average_Wait_Time', 'mean'),
        mean_customer_satisfaction=('Average_Customer_Satisfaction', 'mean'),
        mean_revenue=('Revenue', 'mean'),
        mean_tips = ('Tips', 'mean')).reset_index()

    data_grouped['day_hour'] = data_grouped['day'].astype(str) + " " + data_grouped['hours']
    data_grouped['mean_revenue_gradient'] = data_grouped['mean_revenue'].diff()
    data_grouped.loc[data_grouped['mean_revenue_gradient'] < -1000, 'mean_revenue_gradient'] = None

    custom_colors = {
        'mean_tips':'turquoise',
        'mean_customer_count': 'blue',
        'mean_waiting_time': 'red',
        'mean_customer_satisfaction': 'green',
        'mean_revenue': 'purple',
        'mean_waiters_count': 'orange',
        'mean_revenue_gradient': 'purple',
    }

    fig = px.line(data_grouped,
                x='day_hour',
                y=['mean_revenue', 'mean_tips'],
                labels={
                    "value": "money",
                    "day_hour": "time of day"
                },
                title="Revenue",
                color_discrete_map={'mean_revenue': custom_colors['mean_revenue']})

    for day in data_grouped['day'].unique():
        if f"{day} 15:00" in data_grouped['day_hour'].values:
            fig.add_vline(x=f"{day} 15:00", line_dash="dash", line_color="grey")
        if f"{day} 19:00" in data_grouped['day_hour'].values:
            fig.add_vline(x=f"{day} 19:00", line_dash="dash", line_color="grey")
        if f"{day} 23:00" in data_grouped['day_hour'].values:
            fig.add_vline(x=f"{day} 23:00", line_dash="dash", line_color="black")

    fig.update_layout(showlegend=False)
    fig.show()

    fig = px.line(data_grouped,
                x='day_hour',
                y=['mean_customer_count', 'mean_waiters_count', 'mean_revenue_gradient'],
                labels={
                    "value": "Customer and Waiter Count to Revenue Gradient",
                    "day_hour": "time of day"
                },
                title="Customer and Waiter Count to Revenue Gradient",
                color_discrete_map={'mean_customer_count': custom_colors['mean_customer_count'],
                                    'mean_waiters_count': custom_colors['mean_waiters_count'],
                                    'mean_revenue_gradient': custom_colors['mean_revenue_gradient']})

    for day in data_grouped['day'].unique():
        if f"{day} 15:00" in data_grouped['day_hour'].values:
            fig.add_vline(x=f"{day} 15:00", line_dash="dash", line_color="grey")
        if f"{day} 19:00" in data_grouped['day_hour'].values:
            fig.add_vline(x=f"{day} 19:00", line_dash="dash", line_color="grey")
        if f"{day} 23:00" in data_grouped['day_hour'].values:
            fig.add_vline(x=f"{day} 23:00", line_dash="dash", line_color="black")

    fig.update_layout(showlegend=False)
    fig.show()

    fig = px.line(data_grouped,
                x='day_hour',
                y=['mean_waiting_time', 'mean_customer_satisfaction'],
                labels={
                    "value": 'unit',
                    "day_hour": "time of day"
                },
                title="Customer Waiting Time and Satisfaction",
                color_discrete_map={'mean_waiting_time': custom_colors['mean_waiting_time'],
                                    'mean_customer_satisfaction': custom_colors['mean_customer_satisfaction']})

    for day in data_grouped['day'].unique():
        if f"{day} 15:00" in data_grouped['day_hour'].values:
            fig.add_vline(x=f"{day} 15:00", line_dash="dash", line_color="grey")
        if f"{day} 19:00" in data_grouped['day_hour'].values:
            fig.add_vline(x=f"{day} 19:00", line_dash="dash", line_color="grey")
        if f"{day} 23:00" in data_grouped['day_hour'].values:
            fig.add_vline(x=f"{day} 23:00", line_dash="dash", line_color="black")

    fig.update_layout(showlegend=False)
    fig.show()
    return data_grouped

def display_first_run_step_results_customer(results):
    df = pd.DataFrame(results)
    data_first_run = df[df["RunId"] == 0]
    data_first_run['hours'] = data_first_run.apply(minutes_to_time, axis=1)
    data_first_run['day_hour'] = data_first_run['day'].astype(str) + " " + data_first_run['hours']

    customer_infos_dict = dict(zip(data_first_run["day_hour"], data_first_run["Customer_Info"]))
    customer_infos_list = [{**item, 'time': k} for k, v in customer_infos_dict.items() for item in v]
    customer_infos_df = pd.DataFrame(customer_infos_list)

    plots = ['waiting_time', 'satisfaction']

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
    data_first_run['hours'] = data_first_run.apply(minutes_to_time, axis=1)
    data_first_run['day_hour'] = data_first_run['day'].astype(str) + " " + data_first_run['hours']

    waiter_infos_dict = dict(zip(data_first_run['day_hour'], data_first_run['Waiter_Info']))

    waiter_infos_list = [{**item, 'time': k, 'day': k.split()[0], 'hours': k.split()[1]} for k, v in waiter_infos_dict.items() for item in v]
    waiter_infos_df = pd.DataFrame(waiter_infos_list)

    waiter_infos_df['hours'] = pd.to_datetime(waiter_infos_df['hours'], format='%H:%M').dt.time

    reset_times = ['11:00', '15:00', '19:00', '23:00']
    reset_times = [pd.to_datetime(time, format='%H:%M').time() for time in reset_times]

    def reset_tips_served_customers(df):
        for counter in range(len(reset_times)):
            
            if counter == 0:
                continue

            for day in df['day'].unique():
                day_rows = df[df['day'] == day]
                before_reset = day_rows[(day_rows['hours'] < reset_times[counter]) & (day_rows['hours'] >= reset_times[counter-1])]

                if (counter == (len(reset_times)-1)) and (str((int(day)+1)) in df['day'].unique()):
                    next_day = str(int(day) + 1)
                    day_rows = df[(df['day'] == next_day) | (df['time'] == day + " 23:00")]
                    after_reset = day_rows[((day_rows['hours'] >= reset_times[0]) & (day_rows['hours'] < reset_times[1])) | (day_rows['time'] == day + " 23:00")]
                else:
                    after_reset = day_rows[(day_rows['hours'] >= reset_times[counter]) & (day_rows['hours'] < reset_times[counter+1] if counter+1 < len(reset_times) else True)]            
                
                for waiter in df['waiter_nr'].unique():
                    waiter_before_reset = before_reset[before_reset['waiter_nr'] == waiter]
                    waiter_after_reset = after_reset[after_reset['waiter_nr'] == waiter]
                    
                    if not waiter_before_reset.empty and not waiter_after_reset.empty:
                        df.loc[waiter_after_reset.index, 'tips'] -= waiter_before_reset['tips'].max()
                        df.loc[waiter_after_reset.index, 'served_customers'] -= waiter_before_reset['served_customers'].max()
        return df

    waiter_infos_df = reset_tips_served_customers(waiter_infos_df)

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
        self.grid_height = results[0]['grid_height'] if results[0]['grid_height'] % 2 != 0 else results[0]['grid_height'] + 1  # make sure grid_height is uneven
        self.grid_width = results[0]['grid_width'] if results[0]['grid_width'] % 2 != 0 else results[0]['grid_width'] + 1  # make sure grid_width is uneven
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

    def minutes_to_time(self, minutes):
        hours = minutes // 60
        remaining_minutes = minutes % 60
        
        time = datetime.time(hour=hours, minute=remaining_minutes)
        return time

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

        day = step_data['day']
        time = self.minutes_to_time(step_data['time'])
        shift = step_data['shift']
        
        self.ax.text(0.5, 1.05, f"Day {day}: {time}, Shift {shift}", transform=self.ax.transAxes, fontsize=12, ha='center', va='bottom')

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
            interval=25,
            repeat=False
        )
        return ani
