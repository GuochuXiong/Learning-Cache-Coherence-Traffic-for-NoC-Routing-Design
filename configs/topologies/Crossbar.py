# Copyright (c) 2010 Advanced Micro Devices, Inc.
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

##add this for IP mapping
import sys
sys.path.append("/home/guochu/gem5/configs")
from network.Network import adjacency_matrices
##end add


##in this file, we also add some codes to generate the adjacency matrix for task mapping


class Crossbar(SimpleTopology):
    description = "Crossbar"

    def makeTopology(self, options, network, IntLink, ExtLink, Router):
        # default values for link latency and router latency.
        # Can be over-ridden on a per link/router basis
        link_latency = options.link_latency  # used by simple and garnet
        router_latency = options.router_latency  # only used by garnet

        # Create an individual router for each controller plus one more for
        # the centralized crossbar.  The large numbers of routers are needed
        # because external links do not model outgoing bandwidth in the
        # simple network, but internal links do.
        # For garnet, one router suffices, use CrossbarGarnet.py
        
        
        ##add this for weight update in topology
        # Check if weights are provided, otherwise, use default.
        if options.link_weight:
            link_weight = list(map(int, options.link_weight.split(',')))
        else:
            link_weight = [1] * len(self.nodes)  # Default weights, assuming uniform weights.
            
        
        print(len(self.nodes))
        print(len(self.nodes) == 24)
        ##end add
        
        

        routers = [Router(router_id=i) for i in range(len(self.nodes) + 1)]
        xbar = routers[
            len(self.nodes)
        ]  # the crossbar router is the last router created
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
            for (i, n) in enumerate(self.nodes)
        ]
        network.ext_links = ext_links

        link_count = len(self.nodes)

        int_links = []
        for i in range(len(self.nodes)):
            int_links.append(
                IntLink(
                    link_id=(link_count + i),
                    src_node=routers[i],
                    dst_node=xbar,
                    latency=link_latency,
                    
                    
                    ##add this for weight_update
                    weight=link_weight[i % len(link_weight)],  # Apply weight from link_weight
                    ##end add
                )
            )
            
            #add this for task mapping
            adjacency_matrix[routers[i].router_id][xbar.router_id] = link_weight[i % len(link_weight)]
            #end add

        link_count += len(self.nodes)

        for i in range(len(self.nodes)):
            int_links.append(
                IntLink(
                    link_id=(link_count + i),
                    src_node=xbar,
                    dst_node=routers[i],
                    latency=link_latency,
                    
                    
                    
                    ##add this for weight_update
                    weight=link_weight[i % len(link_weight)],  # Apply weight from link_weight
                    ##end add
                )
            )
            
            
            #add this for task mapping
            adjacency_matrix[xbar.router_id][routers[i].router_id] = link_weight[i % len(link_weight)]\
            #end add
                        

        network.int_links = int_links
        
        
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
        file_path = os.path.join(outdir, "Crossbar_adjacency_matrix.txt")
        with open(file_path, "w") as f:
            for row in adjacency_matrix:
                f.write(" ".join(map(str, row)) + "\n")
    #end add
