#In Torus, the East connects to the West, and the North connects to the South, so only two distinct weights are needed.

from m5.params import *
from m5.objects import *
from m5.util import fatal
import os
import sys

from topologies.BaseTopology import SimpleTopology

## Add this for IP mapping
sys.path.append("/home/guochu/gem5/configs")
from network.Network import adjacency_matrices
## End add



class Torus(SimpleTopology):
    description='Torus'

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
        link_latency = options.link_latency # used by simple and garnet
        router_latency = options.router_latency # only used by garnet
        
        
        link_weight = [int(w) for w in options.link_weight.split(',')]
        if len(link_weight) < 2:
            raise ValueError("Error: `--link-weight` must have at least two values (East-West, North-South).")



        # There must be an evenly divisible number of cntrls to routers
        # Also, obviously the number or rows must be <= the number of routers
        cntrls_per_router, remainder = divmod(len(nodes), num_routers)
        assert(num_rows > 0 and num_rows <= num_routers)
        num_columns = int(num_routers / num_rows)
        assert(num_columns * num_rows == num_routers)

        # Create the routers in the mesh
        routers = [Router(router_id=i, latency = router_latency) \
            for i in range(num_routers)]
        network.routers = routers
        
        
        # ? Initialize adjacency matrix
        adjacency_matrix = [[0 for _ in range(num_routers)] for _ in range(num_routers)]
        adjacency_matrices[network] = adjacency_matrix

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
        for (i, n) in enumerate(network_nodes):
            cntrl_level, router_id = divmod(i, num_routers)
            assert(cntrl_level < cntrls_per_router)
            ext_links.append(ExtLink(link_id=link_count, ext_node=n,
                                    int_node=routers[router_id],
                                    latency = link_latency))
            link_count += 1

        # Connect the remainding nodes to router 0.  These should only be
        # DMA nodes.
        for (i, node) in enumerate(remainder_nodes):
            # assert(node.type == 'DMA_Controller')
            assert(i < remainder)
            ext_links.append(ExtLink(link_id=link_count, ext_node=node,
                                    int_node=routers[0],
                                    latency = link_latency))
            link_count += 1

        network.ext_links = ext_links

        # Create the mesh links.
        # Create the torus links.
        
        int_links = []
        added_links = set()  # ? Track added links to avoid duplicates


        # East output to West input links (weight = 1)
        for row in range(num_rows):
            for col in range(num_columns):
                east_out = col + (row * num_columns)
                west_in = (col + 1) % num_columns + (row * num_columns)  # Wrap-around horizontally

                # ? Ensure only one link per pair (avoid West-East duplicates)
                if (east_out, west_in) not in added_links:
                    int_links.append(IntLink(
                        link_id=link_count,
                        src_node=routers[east_out],
                        dst_node=routers[west_in],
                        src_outport="East",
                        dst_inport="West",
                        latency=link_latency,
                        weight=link_weight[0]
                    ))
                    adjacency_matrix[east_out][west_in] = link_weight[0]
                    adjacency_matrix[west_in][east_out] = link_weight[0]  # Bidirectional
                    added_links.add((east_out, west_in))  # ? Mark link as added
                    link_count += 1

        # North output to South input links (weight = 2)
        for col in range(num_columns):
            for row in range(num_rows):
                north_out = col + (row * num_columns)
                south_in = col + ((row + 1) % num_rows) * num_columns  # Wrap-around vertically

                # ? Ensure only one link per pair (avoid South-North duplicates)
                if (north_out, south_in) not in added_links:
                    int_links.append(IntLink(
                        link_id=link_count,
                        src_node=routers[north_out],
                        dst_node=routers[south_in],
                        src_outport="North",
                        dst_inport="South",
                        latency=link_latency,
                        weight=link_weight[1]
                    ))
                    adjacency_matrix[north_out][south_in] = link_weight[1]
                    adjacency_matrix[south_in][north_out] = link_weight[1]  # Bidirectional
                    added_links.add((north_out, south_in))  # ? Mark link as added
                    link_count += 1

        network.int_links = int_links


        ## ? Save adjacency matrix
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
