# Copyright (c) 2010 Advanced Micro Devices, Inc.
#               2016 Georgia Institute of Technology
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

# Creates a generic Mesh assuming an equal number of cache
# and directory controllers.
# West-first routing is enforced (using link weights)
# to guarantee deadlock freedom.
# The network randomly chooses between links with the same
# weight for messages within unordered virtual networks.
# Within ordered virtual networks, a fixed link direction
# is always chosen based on which appears first inside the
# routing table.


##in this file, we also add some codes to generate the adjacency matrix for task mapping

import sys
sys.path.append("/home/guochu/gem5/configs")
from network.Network import adjacency_matrices



class Mesh_westfirst(SimpleTopology):
    description = "Mesh_westfirst"

    def __init__(self, controllers):
        self.nodes = controllers

    # Makes a generic mesh
    # assuming an equal number of cache and directory cntrls

    def makeTopology(self, options, network, IntLink, ExtLink, Router):
        nodes = self.nodes

        num_routers = options.num_cpus
        num_rows = options.mesh_rows

        # default values for link latency and router latency.
        # Can be over-ridden on a per link/router basis
        link_latency = options.link_latency  # used by simple and garnet
        router_latency = options.router_latency  # only used by garnet
        
        
        
        
        ##add this for weight_update with topologies
       
        link_weight = [int(w) for w in options.link_weight.split(',')]
        assert len(link_weight) == 4, "Weights must have exactly four elements."
        ##end add
        
        
        
        

        # There must be an evenly divisible number of cntrls to routers
        # Also, obviously the number or rows must be <= the number of routers
        cntrls_per_router, remainder = divmod(len(nodes), num_routers)
        assert num_rows > 0 and num_rows <= num_routers
        num_columns = int(num_routers / num_rows)
        assert num_columns * num_rows == num_routers

        # Create the routers in the mesh
        routers = [
            Router(router_id=i, latency=router_latency)
            for i in range(num_routers)
        ]
        network.routers = routers
        
        
        ##we add this for task mapping
        # Initialize the adjacency matrix as a square matrix of size num_routers
        # and store it in the global dictionary under the network key.
        adjacency_matrix = [[0 for _ in range(num_routers)] for _ in range(num_routers)]
        adjacency_matrices[network] = adjacency_matrix
        #end add
        
        

        # link counter to set unique link ids
        link_count = 0

        # Add all but the remainder nodes to the list of nodes to be uniformly
        # distributed across the network.
        network_nodes = []
        remainder_nodes = []
        for node_index in range(len(nodes)):
            if node_index < (len(nodes) - remainder):
                network_nodes.append(nodes[node_index])
            else:
                remainder_nodes.append(nodes[node_index])

        # Connect each node to the appropriate router
        ext_links = []
        for i, n in enumerate(network_nodes):
            cntrl_level, router_id = divmod(i, num_routers)
            assert cntrl_level < cntrls_per_router
            ext_links.append(
                ExtLink(
                    link_id=link_count,
                    ext_node=n,
                    int_node=routers[router_id],
                    latency=link_latency,
                )
            )
            link_count += 1

        # Connect the remainding nodes to router 0.  These should only be
        # DMA nodes.
        for i, node in enumerate(remainder_nodes):
            assert node.type == "DMA_Controller"
            assert i < remainder
            ext_links.append(
                ExtLink(
                    link_id=link_count,
                    ext_node=node,
                    int_node=routers[0],
                    latency=link_latency,
                )
            )
            link_count += 1

        network.ext_links = ext_links

        # Create the mesh links.
        int_links = []

        # East output to West input links (weight = 2)
        for row in range(num_rows):
            for col in range(num_columns):
                if col + 1 < num_columns:
                    east_out = col + (row * num_columns)
                    west_in = (col + 1) + (row * num_columns)
                    int_links.append(
                        IntLink(
                            link_id=link_count,
                            src_node=routers[east_out],
                            dst_node=routers[west_in],
                            latency=link_latency,
                            #weight=2,
                            
                            #revise to this
                            weight=link_weight[0],
                            ##end add
                        )
                    )
                    
                    #add this for task mapping
                    adjacency_matrix[east_out][west_in] = link_weight[0]
                    #end add
                    
                    
                    link_count += 1

        # West output to East input links (weight = 1)
        for row in range(num_rows):
            for col in range(num_columns):
                if col + 1 < num_columns:
                    east_in = col + (row * num_columns)
                    west_out = (col + 1) + (row * num_columns)
                    int_links.append(
                        IntLink(
                            link_id=link_count,
                            src_node=routers[west_out],
                            dst_node=routers[east_in],
                            latency=link_latency,
                            #weight=1,
                            
                            #revise to this
                            weight=link_weight[1],
                            ##end add
                        )
                    )
                    
                    
                    #add this for task mapping
                    adjacency_matrix[west_out][east_in] = link_weight[1]
                    #end add
                    
                    
                    link_count += 1

        # North output to South input links (weight = 2)
        for col in range(num_columns):
            for row in range(num_rows):
                if row + 1 < num_rows:
                    north_out = col + (row * num_columns)
                    south_in = col + ((row + 1) * num_columns)
                    int_links.append(
                        IntLink(
                            link_id=link_count,
                            src_node=routers[north_out],
                            dst_node=routers[south_in],
                            latency=link_latency,
                            #weight=2,
                            
                            
                            #revise to this
                            weight=link_weight[2],
                            ##end add
                        )
                    )
                    
                    #add this for task mapping
                    adjacency_matrix[north_out][south_in] = link_weight[2]
                    #end add
                    
                    
                    link_count += 1

        # South output to North input links (weight = 2)
        for col in range(num_columns):
            for row in range(num_rows):
                if row + 1 < num_rows:
                    north_in = col + (row * num_columns)
                    south_out = col + ((row + 1) * num_columns)
                    int_links.append(
                        IntLink(
                            link_id=link_count,
                            src_node=routers[south_out],
                            dst_node=routers[north_in],
                            latency=link_latency,
                            #weight=2,
                            
                            
                            #revise to this
                            weight=link_weight[3],
                            ##end add
                        )
                    )
                    
                    #add this for task mapping
                    adjacency_matrix[south_out][north_in] = link_weight[3]
                    #end add
                    
                    
                    
                    link_count += 1

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
        file_path = os.path.join(outdir, "Mesh_adjacency_matrix.txt")
        with open(file_path, "w") as f:
            for row in adjacency_matrix:
                f.write(" ".join(map(str, row)) + "\n")
    #end add
