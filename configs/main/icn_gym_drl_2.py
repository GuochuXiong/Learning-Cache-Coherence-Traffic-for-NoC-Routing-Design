import random
import os
from collections import defaultdict, deque
import numpy as np
import matplotlib as mpl
import matplotlib
matplotlib.use('agg')
import matplotlib.pyplot as plt
#import csv
# import time as ti
# import pandas as pd
from extract_network_stats import parse_stats, write_dicts_to_file

##add this to integrate with custom routing
#def get_action(state, i_episode):
   #policy_s = epsilon_greedy_probs(Q[state], i_episode)
   #action_index = np.random.choice(np.arange(a_size), p=abs(policy_s))
   #return actions[action_index]
   
#def get_rl_action(state):
    #global rew_history
    #i_episode = len(rew_history) + 1
    #return get_action(state, i_episode)
##end add

##add these to make fs.py run
import subprocess
import telnetlib
import time
import socket

def is_port_open(host, port):
    """Check if the specified port is open."""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.connect((host, port))
        s.shutdown(socket.SHUT_RDWR)
        return True
    except Exception:
        return False
    finally:
        s.close()
        
def is_file_stable(file_path, wait_time=10, min_size=100):
    """
    Check if a file is stable by monitoring its size over a short period.
    Also ensures the file is not empty and meets a minimum size requirement.
    
    Args:
        file_path (str): Path to the file to check.
        wait_time (int): Time to wait between size checks (in seconds).
        min_size (int): Minimum size of the file in bytes to consider it valid.

    Returns:
        bool: True if the file is stable and meets the size requirement, False otherwise.
    """
    if not os.path.exists(file_path):
        return False

    # Check if the file is not empty and meets the minimum size requirement
    initial_size = os.path.getsize(file_path)
    if initial_size < min_size:
        #print(f"File {file_path} is smaller than the minimum size of {min_size} bytes.")
        return False

    # Wait for a while and then check the size again
    time.sleep(wait_time)
    final_size = os.path.getsize(file_path)

    # File is considered stable if the size hasn't changed
    is_stable = initial_size == final_size
    #if not is_stable:
        #print(f"File {file_path} is still being written to (size changed).")
    
    return is_stable

def wait_for_port(host, port, timeout=300):
    """Wait up to `timeout` seconds for `port` to become available."""
    start_time = time.time()
    while time.time() - start_time < timeout:
        if is_port_open(host, port):
            print(f"? Port {port} is now open!")
            return True
        print(f"? Waiting for port {port} to open...")
        time.sleep(180)
    print(f"? Port {port} did not open within {timeout} seconds.")
    return False

def run_gem5_simulation(action, mesh_rows, weights):
    """Run the gem5 simulation with the given topology and mesh_rows."""
    
    os_command = (
        f"bash -l -c '/home/guochu/gem5/build/X86_MESI_Two_Level/gem5.opt "
        f"--outdir=/data/guochu/gem5/2paper/4c_routing/ferret/mem_768MB "
        f"/home/guochu/gem5/configs/deprecated/example/fs_drl_attention.py "
        f"--kernel=/home/guochu/gem5/parsec_full_system_images/binaries/x86_64-vmlinux-2.6.28.4-smp "
        f"--disk=/home/guochu/gem5/parsec_full_system_images/disks/x86root-parsec.img "
        f"--script=/home/guochu/gem5/parsec_full_system_images/benchmarks/ferret_4c_simsmall.rcS "
        f"--network=garnet --num-cpus=4 --num-dirs=4 --ruby --num-l2caches=4 "
        f"--l1d_size=64kB --l2_size=2MB  --mem-size=768MB --topology={action} {mesh_rows} --link-weight={weights}'"
    )

    print(f"?? Running gem5 with command:\n{os_command}")

    sim_process = subprocess.Popen(os_command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    return sim_process

def connect_to_telnet():
    """Connect to gem5 via telnet in tmux session."""
    
    # Ensure tmux session exists
    subprocess.run("tmux new-session -d -s 15", shell=True)

    # Wait until port 3456 is available
    if wait_for_port('localhost', 3462):
        tmux_command = "tmux send-keys -t 15 'telnet localhost 3462' C-m"
        subprocess.run(tmux_command, shell=True)
        print("? Telnet connection initiated in tmux session.")

def terminate_simulation(sim_process):
    """Terminate the gem5 simulation process."""
    try:
        sim_process.terminate()
        sim_process.wait(timeout=10)
        print("? gem5 simulation terminated successfully.")
    except subprocess.TimeoutExpired:
        print("?? gem5 simulation did not terminate in time, force killing it.")
        os.kill(sim_process.pid, 9)

def ICN_env(action, weights):
    """Run gem5 simulation and connect to telnet."""
    mesh_rows = "--mesh-rows=2" if action in ["Mesh_westfirst", "Torus", "FlattenedButterfly"] else ""


    # Start gem5
    sim_process = run_gem5_simulation(action, mesh_rows, weights)

    # Wait for gem5 to open port 3456
    if wait_for_port('localhost', 3462):
        connect_to_telnet()
    
    # Wait for gem5 to finish
    sim_process.wait()


    # (Proceed with extracting stats, etc.)
    stats_file = "/data/guochu/gem5/2paper/4c_routing/ferret/mem_768MB/stats.txt"
    while not os.path.exists(stats_file) or not is_file_stable(stats_file):
        time.sleep(30)
    
    output_file = "/data/guochu/gem5/2paper/4c_routing/ferret/mem_768MB/network_stats.txt"
  
    #os_command2 = "/home/guochu/gem5/configs/RL_routing/extract_network_stats.sh"
    
    #if not os.access(os_command2, os.X_OK):
        #print(f"Making {os_command2} executable.")
        #os.chmod(os_command2, 0o755)

    #os.system(os_command2)
    
    # Run the extract script
    #result = subprocess.run(os_command2, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    #if result.returncode != 0:
        #print(f"Error executing {os_command2}: {result.stderr.decode()}")
        #return None
        
    # Check if the output file exists
    #network_stats_file = "/data/guochu/gem5/16c_routing/network_stats_vips.txt"
    #if not os.path.exists(network_stats_file):
        #print(f"Error: {network_stats_file} not found.")
        #return None
    
    # Parse the statistics file
    #dicts = {}
        
        
    #with open(network_stats_file, "r") as fd:
        #for line in fd:
            #line_ele = line.split(" ")
            #if len(line_ele) > 3:
                #my_line = line_ele
                #key = my_line[0]
                #val = my_line[2]
                #dicts[key].append(val)
    # print(dicts)
    dicts = parse_stats(stats_file,num_cores=4)
    write_dicts_to_file(dicts, output_file)
    
    # After collecting data, terminate the simulation
    terminate_simulation(sim_process)
    
    

    return dicts
    
# Example Usage
#dicts= ICN_env("Mesh_westfirst", "2,1,2,2")