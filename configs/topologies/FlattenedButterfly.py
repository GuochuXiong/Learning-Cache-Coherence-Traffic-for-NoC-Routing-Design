#Choosing link_weight:
#For small networks (e.g., 4×4) ? Use "1,2".
#For larger networks (e.g., 8×8) ? Use "1,2,3".
#For more complex topologies ? Use "1,2,3,4".

#1st-hop (neighboring routers) ? Weight 1, 2nd-hop (further connections) ? Weight 2

from m5.params import *
from m5.objects import *
import os
import sys
import math
import os
import sys
import math
from m5.util import fatal
from topologies.BaseTopology import SimpleTopology

## Add this for IP mapping
sys.path.append("/home/guochu/gem5/configs")
from network.Network import adjacency_matrices
## End add

from m5.params import *
from m5.objects import *

class FlattenedButterfly(SimpleTopology):
    description = "FlattenedButterfly"

    def __init__(self, controllers):
        self.nodes = controllers

    def makeTopology(self, options, network, IntLink, ExtLink, Router):
        nodes = self.nodes
        link_latency = options.link_latency  # Used by simple and garnet
        router_latency = options.router_latency  # Only used by garnet
        num_routers = options.num_cpus
        num_rows = options.mesh_rows

        # Ensure a valid router configuration
        assert num_rows <= num_routers
        num_columns = int(num_routers / num_rows)
        assert num_columns * num_rows == num_routers

        # ? Initialize adjacency matrix
        adjacency_matrix = [[0 for _ in range(num_routers)] for _ in range(num_routers)]
        adjacency_matrices[network] = adjacency_matrix  # Store matrix for reference

        # ? Ensure at least 2 link weights are provided
        link_weight = [int(w) for w in options.link_weight.split(",")]
        if len(link_weight) < 2:
            link_weight += [link_weight[-1]] * (2 - len(link_weight))  # Fill missing weights

        # ? Create routers
        routers = [Router(router_id=i, latency=router_latency) for i in range(num_routers)]
        network.routers = routers

        # ? Connect nodes to routers
        cntrls_per_router, remainder = divmod(len(nodes), num_routers)
        network_nodes = []
        remainder_nodes = []

        for node_index in range(len(nodes)):
            if node_index < (len(nodes) - remainder):
                network_nodes.append(nodes[node_index])
            else:
                remainder_nodes.append(nodes[node_index])

        # ? Connect each CPU node to an appropriate router
        ext_links = []
        link_count = 0

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

        # ? Connect the remaining nodes (DMA controllers) to router 0
        for i, node in enumerate(remainder_nodes):
            assert node.type == "DMA_Controller"  # Ensure these are DMA controllers
            assert i < remainder
            ext_links.append(
                ExtLink(
                    link_id=link_count,
                    ext_node=node,
                    int_node=routers[0],  # DMA controllers connected to router 0
                    latency=link_latency,
                )
            )
            link_count += 1

        network.ext_links = ext_links

        # ? Create internal links
        int_links = []
        added_links = set()

        # ? West-East Links
        for row in range(num_rows):
            for col in range(num_columns):
                west_in = col + (row * num_columns)

                for i in range(col + 1 + (row * num_columns), (row * num_columns + num_columns)):
                    east_out = i

                    if (east_out, west_in) not in added_links:
                        int_links.append(IntLink(
                            link_id=link_count,
                            src_node=routers[east_out],
                            dst_node=routers[west_in],
                            src_outport="East",
                            dst_inport="West",
                            latency=1,
                            weight=link_weight[0]
                        ))

                        # ? Update adjacency matrix
                        adjacency_matrix[east_out][west_in] = link_weight[0]
                        adjacency_matrix[west_in][east_out] = link_weight[0]  # Bidirectional

                        added_links.add((east_out, west_in))
                        link_count += 1

        # ? East-West Links
        for row in range(num_rows):
            for col in range(num_columns):
                west_out = col + (row * num_columns)

                for i in range(col + 1 + (row * num_columns), (row * num_columns + num_columns)):
                    east_in = i

                    if (west_out, east_in) not in added_links:
                        int_links.append(IntLink(
                            link_id=link_count,
                            src_node=routers[west_out],
                            dst_node=routers[east_in],
                            src_outport="West",
                            dst_inport="East",
                            latency=1,
                            weight=link_weight[0]
                        ))

                        # ? Update adjacency matrix
                        adjacency_matrix[west_out][east_in] = link_weight[0]
                        adjacency_matrix[east_in][west_out] = link_weight[0]  # Bidirectional

                        added_links.add((west_out, east_in))
                        link_count += 1

        # ? North-South Links
        for col in range(num_columns):
            for row in range(num_rows):
                north_out = col + (row * num_columns)
                i = col
                while i < north_out:
                    south_in = i
                    i += num_columns

                    if (north_out, south_in) not in added_links:
                        int_links.append(IntLink(
                            link_id=link_count,
                            src_node=routers[north_out],
                            dst_node=routers[south_in],
                            src_outport="North",
                            dst_inport="South",
                            latency=1,
                            weight=link_weight[1]
                        ))

                        # ? Update adjacency matrix
                        adjacency_matrix[north_out][south_in] = link_weight[1]
                        adjacency_matrix[south_in][north_out] = link_weight[1]  # Bidirectional

                        added_links.add((north_out, south_in))
                        link_count += 1

        # ? South-North Links
        for col in range(num_columns):
            for row in range(num_rows):
                north_in = col + (row * num_columns)
                i = col
                while i < north_in:
                    south_out = i
                    i += num_columns

                    if (south_out, north_in) not in added_links:
                        int_links.append(IntLink(
                            link_id=link_count,
                            src_node=routers[south_out],
                            dst_node=routers[north_in],
                            src_outport="South",
                            dst_inport="North",
                            latency=1,
                            weight=link_weight[1]
                        ))

                        # ? Update adjacency matrix
                        adjacency_matrix[south_out][north_in] = link_weight[1]
                        adjacency_matrix[north_in][south_out] = link_weight[1]  # Bidirectional

                        added_links.add((south_out, north_in))
                        link_count += 1

        network.int_links = int_links

        # ? Save adjacency matrix to file
        output_directory = getattr(options, "outdir", os.getcwd())  # Default to current directory
        self.save_adjacency_matrix(adjacency_matrix, output_directory)

    @staticmethod
    def save_adjacency_matrix(adjacency_matrix, outdir):
        """Save the constructed adjacency matrix to a file for debugging."""
        os.makedirs(outdir, exist_ok=True)  # Ensure the directory exists
        file_path = os.path.join(outdir, "FlattenedButterfly_adjacency_matrix.txt")
        with open(file_path, "w") as f:
            for row in adjacency_matrix:
                f.write(" ".join(map(str, row)) + "\n")



