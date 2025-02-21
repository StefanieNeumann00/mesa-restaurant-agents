import pandas as pd
import matplotlib.pyplot as plt
import plotly.express as px

def display_mean_step_results(results):
    df = pd.DataFrame(results)
    data_grouped = df.groupby(['Step']).agg(
        mean_customer_count = ('Customer_Count', 'mean'),
        mean_waiting_time = ('Average_Wait_Time', 'mean'),
        mean_customer_satisfaction = ('Average_Customer_Satisfaction', 'mean'),
        mean_profit = ('Profit', 'mean')).reset_index()
    
    # Plotting the data in one plot
    fig, ax1 = plt.subplots(figsize=(15, 10))

    ax1.plot(data_grouped['Step'], data_grouped['mean_customer_count'], marker='o', label='Customer Count')
    ax1.plot(data_grouped['Step'], data_grouped['mean_waiting_time'], marker='o', label='Average Wait Time')
    ax1.plot(data_grouped['Step'], data_grouped['mean_customer_satisfaction'], marker='o', label='Average Customer Satisfaction')
    ax1.plot(data_grouped['Step'], data_grouped['mean_profit'], marker='o', label='Profit')

    ax1.set_title('Model Output Data over Steps')
    ax1.set_xlabel('Step')
    ax1.set_ylabel('Values')
    ax1.legend()

    print(plt.show())
    return data_grouped

def display_first_run_step_results_customer(results):
    df = pd.DataFrame(results)
    data_first_run = df[df["RunId"]==0]
    customer_infos_dict = dict(data_first_run["Customer_Info"])
    customer_infos_list = [{**item, 'step': k} for k, v in customer_infos_dict.items() for item in v]
    customer_infos_df = pd.DataFrame(customer_infos_list)

    plots = ['waiting_time','order_status','satisfaction']

    for plot in plots:
        fig = px.histogram(customer_infos_df, x="step", y=plot,
                    color='customer_nr', barmode='group',
                    height=400, nbins=len(customer_infos_df['step'].unique()))
        print(fig.show())
    return customer_infos_df


def display_first_run_step_results_waiter(results):
    df = pd.DataFrame(results)
    data_first_run = df[df["RunId"]==0]
    waiter_infos_dict = dict(data_first_run["Waiter_Info"])
    waiter_infos_list = [{**item, 'step': k} for k, v in waiter_infos_dict.items() for item in v]
    waiter_infos_df = pd.DataFrame(waiter_infos_list)

    plots = ['busy','tips','avg_rating', 'served_customers']

    for plot in plots:
        fig = px.histogram(waiter_infos_df, x="step", y=plot,
                    color='waiter_nr', barmode='group',
                    height=400, nbins=len(waiter_infos_df['step'].unique()))
        print(fig.show())
    return waiter_infos_df