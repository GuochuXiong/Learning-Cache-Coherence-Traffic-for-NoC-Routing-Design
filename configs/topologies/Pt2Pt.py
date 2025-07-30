# Copyright (c) 2011 Advanced Micro Devices, Inc.
#               2011 Massachusetts Institute of Technology
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are
# met: redistributions of source code must retain the above copyright
# notice, this list of conditions and the following disclaimer;
# redistributions in binary form must reproduce the above copyright
# notice, this list of conditions and the following disclaimer in the
# documentation and/or other materials provided with the distribution;
# neither the name of the copyright holders nor the names of its
# contributors may be used to endorse or promote products derived from
# this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from topologies.BaseTopology import SimpleTopology

from m5.objects import *
from m5.params import *


##In this file, we add codes to generate adjacency matrix for task mapping
##add this for IP mapping
import sys
sys.path.append("/home/guochu/gem5/configs")
from network.Network import adjacency_matrices
##end add


class Pt2Pt(SimpleTopology):
    description = "Pt2Pt"

    def __init__(self, controllers):
        self.nodes = controllers

    def makeTopology(self, options, network, IntLink, ExtLink, Router):
        nodes = self.nodes

        # default values for link latency and router latency.
        # Can be over-ridden on a per link/router basis
        link_latency = options.link_latency  # used by simple and garnet
        router_latency = options.router_latency  # only used by garnet
        
        print(len(nodes))
        print(len(nodes) == 132)
        
        
        
        ##add this for weight update in topology
        # Check if weights are provided, otherwise, use default.
        if options.link_weight:
            link_weight = list(map(int, options.link_weight.split(',')))
        else:
            link_weight = [1] * len(nodes)  # Default weights, assuming uniform weights.
        ##end add
        
        
        
        
        

        # Create an individual router for each controller,
        # and connect all to all.
        # Since this is a high-radix router, router_latency should
        # accordingly be set to a higher value than the default
        # (which is 1 for mesh routers)
        routers = [
            Router(router_id=i, latency=router_latency)
            for i in range(len(nodes))
        ]
        network.routers = routers
        
        
        ##add this for task mapping
        # Initialize adjacency matrix
        num_routers = len(routers)
        ## Initialize adjacency matrix for task mapping
        adjacency_matrix = [[0 for _ in range(num_routers)] for _ in range(num_routers)]
        adjacency_matrices[network] = adjacency_matrix
        
        if adjacency_matrix is None:
            fatal("Error: Adjacency matrix was not initialized in `network.py`.")
        #end add
        
        

        ext_links = [
            ExtLink(
                link_id=i,
                ext_node=n,
                int_node=routers[i],
                latency=link_latency,
            )
            for (i, n) in enumerate(nodes)
        ]
        network.ext_links = ext_links

        link_count = len(nodes)
        int_links = []
        for i in range(len(nodes)):
            for j in range(len(nodes)):
                if i != j:
                
                
                    ##add this for weight update in topology
                    weight = link_weight[i % len(link_weight)]  # Apply weight based on the source router index.
                    ##end add
                    
                    
                    
                
                    link_count += 1
                    int_links.append(
                        IntLink(
                            link_id=link_count,
                            src_node=routers[i],
                            dst_node=routers[j],
                            latency=link_latency,
                            
                            
                            
                            ##add this for weight update in topology
                            weight=weight,
                            ##end add
                            
                            
                            
                        )
                    )
                    
                    
                    ##add this for task mapping
                    # Update adjacency matrix
                    adjacency_matrix[routers[i].router_id][routers[j].router_id] = weight
                    #end add

        network.int_links = int_links
        
        
        ##add this for task mapping
        # Optionally store adjacency matrix in the network object for future use
        #network.adjacency_matrix = adjacency_matrix
        
        
        # Save adjacency matrix to file
        # Determine the output directory.
        output_directory = getattr(options, "outdir", None)
        if output_directory is None:
        # If outdir is not defined, try output_dir, then fallback to current directory.
           output_directory = getattr(options, "output_dir", os.getcwd())

        # Save the constructed adjacency matrix to file.

        self.save_adjacency_matrix(adjacency_matrix, output_directory)

    @staticmethod
    def save_adjacency_matrix(adjacency_matrix, outdir):
        file_path = os.path.join(outdir, "Pt2Pt_adjacency_matrix.txt")
        with open(file_path, "w") as f:
            for row in adjacency_matrix:
                f.write(" ".join(map(str, row)) + "\n")
    #end add
