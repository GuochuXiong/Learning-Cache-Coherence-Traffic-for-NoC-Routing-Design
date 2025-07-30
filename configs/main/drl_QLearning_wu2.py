##in ./configs/common/options.py, we can use --l1d_size, --l2_size to change the cache size


import random
import os
from collections import defaultdict, deque
import numpy as np
import matplotlib as mpl
import matplotlib
matplotlib.use('agg')
import matplotlib.pyplot as plt
import csv
from icn_gym_drl_2 import *

import time
import sys


##add this for weight-update
from weight_update import WeightPredictor

import torch
import torch.nn as nn
import torch.optim as optim
from Qnetwork_drl import QNetwork  # Import the Q-network
# Global Parameters
actions = ["Mesh_westfirst", "Pt2Pt", "Crossbar", "Torus", "FatTree", "FlattenedButterfly"]  # Action space,in fact it is mesh topology
a_size = len(actions)  # Number of actions
Q = defaultdict(lambda: np.zeros(a_size))  # Q-Table (will be replaced by the Q-network)
dicts = defaultdict(list)
total_episodes = 3  # Number of episodes

epsilon = 1.0  # Exploration rate
eps_min = 0.01
eps_decay = 0.999

# Initialize lists to store metrics per episode
time_history = []
latency_history = []
CPU_delay_history = []
cache_messages_history = []
packet_delay_history = []
rew_history = []  # Reward history


# Initialize the neural network
num_cores = 4  # Example value; change based on your system
input_size = 8  # Example; adjust based on the number of states in your RL
output_dim = a_size  # Number of possible actions
q_network = QNetwork(input_size, output_dim)  # Instantiate the Q-network
optimizer = optim.Adam(q_network.parameters(), lr=0.001)
criterion = nn.MSELoss()  # Define the loss function

model = WeightPredictor(input_size, num_cores)
optimizer2 = optim.Adam(model.parameters(), lr=0.001)
#criterion = nn.MSELoss()  # Define the loss function if needed for training

'''preprocess data and normalize'''
# Initialize global running statistics
running_means = None
running_stds = None
count = 0

# Function to update Q-values (Not used directly with the Q-network)
def update_Q(Qsa, Qsa_next, reward, alpha=0.01, gamma=1.0):
    """Updates the action-value function estimate using the most recent time step."""
    return Qsa + (alpha * (reward + (gamma * Qsa_next) - Qsa))

# Function to select action using epsilon-greedy policy
def epsilon_greedy_probs(q_values, i_episode, eps=None):
    """Obtains the action probabilities corresponding to epsilon-greedy policy."""
    epsilon = 1.0 / (i_episode + 1)
    if eps is not None:
        epsilon = eps
    policy_s = np.ones(a_size) * epsilon / a_size
    policy_s[np.argmax(q_values)] = 1 - epsilon + (epsilon / a_size)
    return abs(policy_s)

# Reward function
def reward_f(d):
    """Calculate the reward based on various parameters."""
    latency = float(d["average_packet_latency"])
    delay = float(d["total_average_write_hit_time"])
    delay_and_fetch = float(d["total_average_readmiss_time"])
    m_cache_level = float(d["total_cache_level_messages"])
    network_delay = float(d["average_packet_delay"])

    # Scale values to avoid zero and ensure proper scaling
    scale_latency = latency / 1e4
    scale_delay = delay / 1e7
    scale_delay_and_fetch = delay_and_fetch / 1e6
    scale_cache_level = m_cache_level / 1e6
    scale_network_delay = network_delay/10

    return -(round(scale_latency, 2) +
             round(scale_delay, 2) +
             round(scale_delay_and_fetch, 2) +
             round(scale_cache_level, 2) )  # Minimize latency

# Preprocessing and normalization functions
def update_running_stats(state_tensor):
    global running_means, running_stds, count

    if running_means is None or running_stds is None:
        running_means = state_tensor.clone()
        running_stds = torch.zeros_like(state_tensor)
        count = 1
    else:
        count += 1
        new_means = running_means + (state_tensor - running_means) / count
        running_stds = running_stds + (state_tensor - running_means) * (state_tensor - new_means)
        running_means = new_means

def log_transform(value):
    value_tensor = torch.tensor(value, dtype=torch.float32)
    return torch.log(value_tensor + 1e-5)  # Adding a small constant to avoid log(0)

def preprocess_state(dicts):
    global running_means, running_stds, count

    state_values = [
        torch.tensor(dicts['average_packet_delay'], dtype=torch.float32),

        torch.tensor(dicts['average_packet_latency'], dtype=torch.float32),

        torch.tensor(dicts['average_link_utilization'], dtype=torch.float32),
        log_transform(dicts['packets_injected']),
        log_transform(dicts['packets_received']),
        log_transform(dicts['total_cache_level_messages']),
        log_transform(dicts['total_average_write_hit_time']),
        log_transform(dicts['total_average_readmiss_time'])
    ]
    
    state_tensor = torch.stack(state_values)
    update_running_stats(state_tensor)
    
    if count > 1:
        normalized_state_tensor = (state_tensor - running_means) / (torch.sqrt(running_stds / (count - 1)) + 1e-5)
    else:
        normalized_state_tensor = state_tensor

    return normalized_state_tensor

def save_stats_to_csv(all_stats, total_episodes):
    # Define the columns to be saved in the CSV
    csv_columns = [
        'average_packet_delay', 
        'average_packet_network_latency', 
        'average_packet_latency', 
        'average_packet_queueing_latency', 
        'average_flit_network_latency', 
        'average_flit_latency', 
        'average_flit_queueing_latency', 
        'average_link_utilization', 
        'packets_injected', 
        'packets_received', 
        'flits_injected', 
        'flits_received', 
        'external_link_utilization', 
        'internal_link_utilization', 
        'total_cache_level_messages', 
        'total_average_write_hit_time', 
        'total_average_readmiss_time'
    ]
    
    csv_file = f'/home/guochu/gem5/output/RL_routing_2_paper/Tables/4_ferret_mem_768MB_{total_episodes}.csv'
    
    try:
        with open(csv_file, 'w', newline='') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=csv_columns)
            writer.writeheader()
            for stats in all_stats:  # Iterate over each dictionary in all_stats
                writer.writerow({key: stats.get(key, None) for key in csv_columns})
    except IOError:
        print("I/O error")
        
# Function to write the final action to a file
def write_final_action_to_file(action, filename):
    with open(filename, 'w') as file:
        file.write(f"Final Action: {action}")

# Function to plot and save the statistics separately
def plot_and_save_statistics(latency_history, CPU_delay_history, cache_level_messages_history, packet_delay_history, total_episodes):
    plt.figure(figsize=(8, 6))
    plt.plot(range(len(latency_history)), latency_history, label='Average Packet Latency', marker="", linestyle="-")
    plt.xlabel('Training Episodes')
    plt.ylabel('Latency')
    plt.title('Average Packet Latency')
    plt.legend()
    plt.savefig(f'/home/guochu/gem5/output/RL_routing_2_paper/Figures/4_ferret_mem_768MB_{total_episodes}_latency.png', bbox_inches='tight')
    plt.close()
    
    plt.figure(figsize=(8, 6))
    plt.plot(range(len(CPU_delay_history)), CPU_delay_history, label='CPU Delay', marker="", linestyle="-")
    plt.xlabel('Training Episodes')
    plt.ylabel('CPU delay')
    plt.title('Average CPU delay')
    plt.legend()
    plt.savefig(f'/home/guochu/gem5/output/RL_routing_2_paper/Figures/4_ferret_mem_768MB_{total_episodes}_CPU_delay.png', bbox_inches='tight')
    plt.close()
    
    plt.figure(figsize=(8, 6))
    plt.plot(range(len(cache_level_messages_history)), cache_level_messages_history, label='Total Messages Driven by Cache Coherence', marker="", linestyle="-")
    plt.xlabel('Training Episodes')
    plt.ylabel('Cache Level Messages')
    plt.title('Total Cache Level Messages')
    plt.legend()
    plt.savefig(f'/home/guochu/gem5/output/RL_routing_2_paper/Figures/4_ferret_mem_768MB_{total_episodes}_cache_level_messages.png', bbox_inches='tight')
    plt.close()

    plt.figure(figsize=(8, 6))
    plt.plot(range(len(packet_delay_history)), packet_delay_history, label='Average Packet Delay', marker="", linestyle="-")
    plt.xlabel('Training Episodes')
    plt.ylabel('Average packet delay')
    plt.title('Average Packet Delay')
    plt.legend()
    plt.savefig(f'/home/guochu/gem5/output/RL_routing_2_paper/Figures/4_ferret_mem_768MB_{total_episodes}_average_network_delay.png', bbox_inches='tight')
    plt.close()


# Function to simulate RL
def simulate_rl(initial_dicts, total_episodes=3):
    global epsilon

    # Initialize the state with initial dicts
    sim_state = preprocess_state(initial_dicts)
    all_stats = []  # List to collect statistics for each episode
    
    for i_episode in range(1, total_episodes + 1):
        rewardsum = 0

        for _ in range(3):  # Simulate multiple steps per episode
            q_state = sim_state

            # Step 1: Predict Q-values using the Q-network
            q_values = q_network(q_state.unsqueeze(0))  # No .detach() here

            # Step 2: Select an action using epsilon-greedy policy
            policy_s = epsilon_greedy_probs(q_values.detach().numpy().flatten(), i_episode)
            action_index = np.random.choice(np.arange(a_size), p=abs(policy_s))
            action = actions[action_index]

            # Step 3: Predict the weights using the WeightPredictor
            action_tensor = torch.tensor([action_index], dtype=torch.float32)
            predicted_weights = model(q_state.unsqueeze(0), action_tensor)  # No .detach() here
            
            original_weights =  torch.tensor(predicted_weights, dtype=torch.float32, requires_grad=True)

            #weights_str = ','.join(map(str, predicted_weights.detach().numpy().flatten()))
            weights_str = ','.join(map(str, predicted_weights.detach().flatten().tolist()))

            # Step 4: Simulate the environment with the selected action and observe the next state and reward
            dicts = ICN_env(actions[action_index], weights_str)
            reward = reward_f(dicts)
            rewardsum += reward

            # Step 5: Observe the next state
            next_sim_state = preprocess_state(dicts)

            # Step 6: Update the Q-value for the state-action pair
            next_q_values = q_network(next_sim_state.unsqueeze(0)).max(1)[0].item()  # No .detach() here
            target = reward + 0.99 * next_q_values  # Discount factor gamma=0.99

            optimizer.zero_grad()
            current_q_value = q_network(q_state.unsqueeze(0))[0, action_index]
            loss_q_network = criterion(current_q_value, torch.tensor([target], dtype=torch.float32))
            loss_q_network.backward()
            optimizer.step()
            
                        
            # Update the Q-table using the `update_Q` function
            Q[q_state][action_index] = update_Q(
                Q[q_state][action_index],
                np.max(Q[next_sim_state]),
                reward,
                .01,  # Learning rate (alpha)
                0.80  # Discount factor (gamma)
            )

            # Train the WeightPredictor model
            optimizer2.zero_grad()
            loss_weight_predictor = -reward * original_weights.mean()  # Ensure predicted_weights is a floating-point tensor
            loss_weight_predictor.backward()
            optimizer2.step()

            sim_state = next_sim_state
           

        rew_history.append(rewardsum)
        all_stats.append(dicts)  # Collect the statistics for this episode
        
            # Save the collected statistics to a CSV file after all episodes
        save_stats_to_csv(all_stats, total_episodes)


        # Record metrics from dicts
        latency_history.append(dicts['average_packet_latency'])
        CPU_delay_history.append(dicts['total_average_write_hit_time'])
        cache_messages_history.append(dicts['total_cache_level_messages'])
        packet_delay_history.append(dicts['average_packet_delay'])

        if epsilon > eps_min:
            epsilon *= eps_decay

    final_action = actions[action_index]
    write_final_action_to_file(final_action, os.path.join(final_action_dir, 'final_action_4_ferret_mem_768MB.txt'))
    plot_and_save_statistics(latency_history, CPU_delay_history, cache_messages_history, packet_delay_history, total_episodes)
    
    """
    # Save the final Q-network model
    model_save_path = os.path.join(model_save_dir, 'final_q_network_16_vips.pth')
    torch.save(q_network.state_dict(), model_save_path)
    
    # Save Q-network and history
    model_save_path = os.path.join(model_save_dir, 'mix_weight_predictor_model_64_ferret.pth')
    torch.save(model.state_dict(), model_save_path)
    """




# Main script to run the simulation
table_save_dir = '/home/guochu/gem5/output/RL_routing_2_paper/Tables/'
os.makedirs(table_save_dir, exist_ok=True)


final_action_dir = '/home/guochu/gem5/output/RL_routing_2_paper/final_action/'
os.makedirs(final_action_dir, exist_ok=True)

duration_dir = '/home/guochu/gem5/output/RL_routing_2_paper/Duration/'
os.makedirs(duration_dir, exist_ok=True)

q_table_dir = '/home/guochu/gem5/output/RL_routing_2_paper/Q_Table/'
os.makedirs(q_table_dir, exist_ok=True)

reward_history_dir = '/home/guochu/gem5/output/RL_routing_2_paper/reward/'
os.makedirs(reward_history_dir, exist_ok=True)

model_save_dir = '/home/guochu/gem5/output/RL_routing_2_paper/model/'
os.makedirs(model_save_dir, exist_ok=True)

start_time = time.time()
initial_dicts = ICN_env(action=actions[0], weights='2,1,2,2')

"""
def read_dicts_from_file(file_path):
    dicts = {}
    with open(file_path, 'r') as f:
        for line in f:
            key, value = line.strip().split(':')
            dicts[key] = float(value)  # Convert value to float, assuming all values are numeric
    return dicts
    
file_path = "/data/guochu/gem5/2paper/16c_routing/vips/network_stats.txt"

# Extract initial_dicts from the file
initial_dicts = read_dicts_from_file(file_path)
"""
simulate_rl(initial_dicts=initial_dicts, total_episodes=3)  ##change 45 to 2

end_time = time.time()
total_duration = end_time - start_time

duration_file_path = os.path.join(duration_dir, '4_ferret_time_mem_768MB.txt')
with open(duration_file_path, 'w') as duration_file:
    duration_file.write(f"Total learning process duration: {total_duration:.2f} seconds")



def write_q_table_to_file(Q, filename=os.path.join(q_table_dir, 'q_table_4_ferret_mem_768MB.txt')):
    with open(filename, 'w') as file:
        file.write('Q-Table:\n')
        for state, actions in Q.items():
            if isinstance(actions, (list, np.ndarray)):
                file.write(f"State {state}: {' '.join(map(str, actions))}\n")
            else:
                file.write(f"State {state}: {actions}\n")

def write_reward_history_to_file(rew_history, filename=os.path.join(reward_history_dir, 'reward_history_4_ferret_mem_768MB.txt')):
    with open(filename, 'w') as file:
        file.write('Reward History:\n')
        for reward in rew_history:
            file.write(str(reward) + '\n')
            
total_episodes = 3

write_q_table_to_file(Q)
write_reward_history_to_file(rew_history)

# Plot and save reward history
fig, ax = plt.subplots(figsize=(10, 4))
plt.title('Reward Learning')
plt.plot(range(len(rew_history)), rew_history, label='Reward', marker="", linestyle="-")
plt.xlabel('Training Episodes')
plt.ylabel('Reward')
plt.savefig(f'/home/guochu/gem5/output/RL_routing_2_paper/Figures/4_ferret_mem_768MB_{total_episodes}_ICN.png', bbox_inches='tight')

'''
# Save collected stats to CSV
csv_columns = [
    'average_network_delay', 
    'average_packet_network_latency', 
    'average_packet_latency', 
    'average_packet_queueing_latency', 
    'average_flit_network_latency', 
    'average_flit_latency', 
    'average_flit_queueing_latency', 
    'average_link_utilization', 
    'packets_injected', 
    'packets_received', 
    'flits_injected', 
    'flits_received', 
    'external_link_utilization', 
    'internal_link_utilization', 
    'total_cache_level_messages', 
    'total_average_write_hit_time', 
    'total_average_readmiss_time'
]
csv_file = f'/home/guochu/gem5/output/RL_routing/Tables/mix_QL_vips_{total_episodes}.csv'

try:
    with open(csv_file, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(csv_columns)
        for i in range(len(dicts['average_network_delay'])):
            writer.writerow([dicts[key][i] for key, value in dicts.items()])
except IOError:
    print("I/O error")
  '''  
