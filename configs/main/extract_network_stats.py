import os

def parse_stats(file_path, num_cores):
    # Initialize variables to accumulate sums and count the number of dumps
    sums = {
        "packets_injected": 0.0,
        "packets_received": 0.0,
        "flits_injected": 0.0,
        "flits_received": 0.0,
        "external_link_utilization": 0.0,
        "internal_link_utilization": 0.0,
        "total_cache_level_messages": 0.0,
        "total_NoCWriteHitDuration": 0.0,
        "total_NoCReadMissDuration": 0.0,
        "cache_level_messages" : 0,
        "average_packet_delay":0.0,
        "vnet_0_delay": 0.0,
        "vnet_0_samples": 0,
        "vnet_0_total_delay": 0.0,
        "vnet_1_delay": 0.0,
        "vnet_1_samples": 0,
        "vnet_1_total_delay": 0.0,
        "vnet_2_delay": 0.0,
        "vnet_2_samples": 0,
        "vnet_2_total_delay": 0.0
        #"total_energy": 0.0,
        #"total_power": 0.0
        #"total_writehit_counter":0,
        #"total_readmiss_counter":0
        #"network_delay":0.0
        
    }
    latencies = {
        "average_packet_queueing_latency": 0.0,
        "average_packet_network_latency": 0.0,
        "average_packet_latency": 0.0,
        "average_flit_queueing_latency": 0.0,
        "average_flit_network_latency": 0.0,
        "average_flit_latency": 0.0,
        "average_hops": 0.0,
        "average_link_utilization": 0.0,
        "average_network_delay":0.0
    }
    
    
    dump_count = 0  # To track the number of dumps

    total_writehit_counter = 0
    total_readmiss_counter = 0

    # Temporary variables to hold the counters
    writehit_counters = {}
    readmiss_counters = {}


    

    with open(file_path, 'r') as f:
        for line in f:
                if "Begin Simulation Statistics" in line:
                    dump_count += 1  # Increment the dump count
            
                # Sum the values for each metric
                if "system.ruby.network.packets_injected::total" in line:
                    sums["packets_injected"] += float(line.split()[1])
                elif "system.ruby.network.packets_received::total" in line:
                    sums["packets_received"] += float(line.split()[1])
                elif "system.ruby.network.flits_injected::total" in line:
                    sums["flits_injected"] += float(line.split()[1])
                elif "system.ruby.network.flits_received::total" in line:
                    sums["flits_received"] += float(line.split()[1])
                elif "system.ruby.network.ext_in_link_utilization" in line:
                    sums["external_link_utilization"] += float(line.split()[1])
                elif "system.ruby.network.int_link_utilization" in line:
                    sums["internal_link_utilization"] += float(line.split()[1])
                elif "L1Dcache.total_cache_level_messages" in line:
                    sums["cache_level_messages"] +=int(line.split()[1])
                
                        

                    
                #calculate the network delay
                '''
                elif ("system.ruby.delayVCHist.vnet_0::mean" in line or "system.ruby.delayVCHist.vnet_1::mean" in line or "system.ruby.delayVCHist.vnet_2::mean" in line):
                    latencies["average_network_delay"] += float(line.split()[1])  
                '''
                if "system.ruby.delayVCHist.vnet_0::mean" in line:
                    sums["vnet_0_delay"] = float(line.split()[1])
                elif "system.ruby.delayVCHist.vnet_0::total " in line:
                    sums["vnet_0_samples"] = int(line.split()[1])
                    sums["vnet_0_total_delay"] = sums["vnet_0_delay"] * sums["vnet_0_samples"]

                elif "system.ruby.delayVCHist.vnet_1::mean" in line:
                    sums["vnet_1_delay"] = float(line.split()[1])
                elif "system.ruby.delayVCHist.vnet_1::total " in line:
                    sums["vnet_1_samples"] = int(line.split()[1])
                    sums["vnet_1_total_delay"] = sums["vnet_1_delay"] * sums["vnet_1_samples"]

                elif "system.ruby.delayVCHist.vnet_2::mean" in line:
                    sums["vnet_2_delay"] = float(line.split()[1])
                elif "system.ruby.delayVCHist.vnet_2::total " in line:
                    sums["vnet_2_samples"] = int(line.split()[1])
                    sums["vnet_2_total_delay"] = sums["vnet_2_delay"] * sums["vnet_2_samples"]
                    
                    
                                        
                elif "system.ruby.network.average_packet_queueing_latency" in line:
                    latencies["average_packet_queueing_latency"] += float(line.split()[1])
                elif "system.ruby.network.average_packet_network_latency" in line:
                    latencies["average_packet_network_latency"] += float(line.split()[1])
                elif "system.ruby.network.average_packet_latency" in line:
                    latencies["average_packet_latency"] += float(line.split()[1])
                    
                elif "system.ruby.network.average_flit_queueing_latency" in line:
                    latencies["average_flit_queueing_latency"] += float(line.split()[1])
                elif "system.ruby.network.average_flit_network_latency" in line:
                    latencies["average_flit_network_latency"] += float(line.split()[1])
                elif "system.ruby.network.average_flit_latency" in line:
                    latencies["average_flit_latency"] += float(line.split()[1])
                elif "system.ruby.network.average_hops" in line:
                    latencies["average_hops"] += float(line.split()[1])
                elif "system.ruby.network.avg_link_utilization" in line:
                    latencies["average_link_utilization"] += float(line.split()[1])

                    
                    
                #for i in range(num_cores):  # Assuming 4 cores, you can adjust this as needed
                    #if f"system.ruby.l1_cntrl{i}" in line:
                        #if "L1Dcache.totalNoCWriteHitDuration" in line:
                            #duration = float(line.split()[1])
                            #if duration > 0:
                                #sums["total_NoCWriteHitDuration"] += duration
                                # Fetch the next lines to find the corresponding counter

                                #next_line = next(f)
                                #if f"system.ruby.l1_cntrl{i}" in next_line and "L1Dcache.NoCwriteHitCounter" in next_line:
                                #if "L1Dcache.NoCwriteHitCounter" in next_line:
                                    #sums["total_writehit_counter"] += int(next_line.split()[1])
                                    #sums["total_writehit_counter"] += int(line.split()[1])
                                    #total_writehit_counter += int(next_line.split()[1])
                                

                            #print(f"Core {i}: WriteHit Duration = {duration}, Counter = {sums['total_writehit_counter']}")

                        
                        #elif "L1Dcache.totalNoCReadMissDuration" in line:
                            #duration = float(line.split()[1])
                            #if duration > 0:
                                #sums["total_NoCReadMissDuration"] += duration
                                
                                #print(f"Core {i}: WriteMiss Duration = {duration}")
                                # Fetch the next lines to find the corresponding counter

                                #next_line = next(f)
                                #if f"system.ruby.l1_cntrl{i}" in next_line and "L1Dcache.NoCreadMissCounter" in next_line:
                                #if f"system.ruby.l1_cntrl{i}" in line and "L1Dcache.NoCreadMissCounter" in line:
                                    #sums["total_readmiss_counter"] += int(next_line.split()[1])
                                    #sums["total_readmiss_counter"] += int(line.split()[1])
                                    #total_readmiss_counter += int(line.split()[1])


                                #print(f"Core {i}: WriteHit Duration = {duration}, Counter = {sums['total_writehit_counter']}")

                for i in range(num_cores):
                    if f"system.ruby.l1_cntrl{i}" in line:
                        if "L1Dcache.NoCwriteHitCounter" in line:
                            writehit_counters[i] = int(line.split()[1])
                        elif "L1Dcache.NoCreadMissCounter" in line:
                            readmiss_counters[i] = int(line.split()[1])


                        # Process durations
                        elif "L1Dcache.totalNoCWriteHitDuration" in line:
                            duration = float(line.split()[1])
                            if duration > 0 and i in writehit_counters:
                                sums["total_NoCWriteHitDuration"] += duration
                                total_writehit_counter += writehit_counters[i]
                        elif "L1Dcache.totalNoCReadMissDuration" in line:
                            duration = float(line.split()[1])
                            if duration > 0 and i in readmiss_counters:
                                sums["total_NoCReadMissDuration"] += duration
                                total_readmiss_counter += readmiss_counters[i]
                                
                                
  

    # Calculate the average for each latency metric using the total dump count
    sums["average_packet_delay"] = (sums["vnet_0_total_delay"] + sums["vnet_1_total_delay"] + sums["vnet_2_total_delay"]) #/sums["packets_received"]
    averages = {}
    for key in latencies:
       averages[key] = latencies[key] / dump_count if dump_count > 0 else 0
    '''
        if key == "average_network_delay":
            averages[key] = latencies[key] / (3 * dump_count) if dump_count > 0 else 0
        else:
    '''
        

    # Adjust average network delay calculation by dividing by (3 * dump_count)
    #averages["average_network_delay"] /= (3 * dump_count) 
    
    
    # Add the sums directly for metrics that don't need averaging
    averages.update({
        "packets_injected": sums["packets_injected"],
        "packets_received": sums["packets_received"],
        "flits_injected": sums["flits_injected"],
        "flits_received": sums["flits_received"],
        "external_link_utilization": sums["external_link_utilization"],
        "internal_link_utilization": sums["internal_link_utilization"],
        "total_cache_level_messages": sums["cache_level_messages"],
        #"total_NoCWriteHitDuration": sums["total_NoCWriteHitDuration"],
        #"total_NoCWriteMissDuration": sums["total_NoCWriteMissDuration"],
        #"total_NoCReadMissDuration": sums["total_NoCReadMissDuration"]
        "total_average_write_hit_time": (round(sums["total_NoCWriteHitDuration"]/total_writehit_counter,2) if total_writehit_counter > 0 else 0),
        "total_average_readmiss_time": (round(sums["total_NoCReadMissDuration"]/total_readmiss_counter,2) if total_readmiss_counter > 0 else 0),
        "average_packet_delay": sums["average_packet_delay"],
        #"total_energy (pJ)": sums["total_energy"],
        #"average_power (mW)": sums["total_power"] / (num_cores * 2) if num_cores > 0 else 0,
    })

    return averages

# Example usage:
stats_file_path = "/data/guochu/gem5/mesh_mesi_vips/stats.txt"
averages = parse_stats(stats_file_path, num_cores=16)

# Now you can print the averages or use them as needed
#for key, avg in averages.items():
    #print(f"{key}: {avg}")

def write_dicts_to_file(averages, output_file):
    with open(output_file, 'w') as f:
        for key, avg in averages.items():
            f.write(f"{key}: {avg}\n")

output_file = "/data/guochu/gem5/2paper/16c_routing/vips/network_stats.txt"
write_dicts_to_file(averages, output_file)