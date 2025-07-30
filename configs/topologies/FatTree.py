##this file is for FatTree, there are two link weights

from m5.params import *
from m5.objects import *
from math import *

from topologies.BaseTopology import SimpleTopology

## Add this for IP mapping
sys.path.append("/home/guochu/gem5/configs")
from network.Network import adjacency_matrices
## End add

# Cria uma topologia Tree com 4 diretórios, um em cada canto da topologia.
class FatTree(SimpleTopology):
    description='FatTree'

    def __init__(self, controllers):
        self.nodes = controllers

    def makeTopology(self, options, network, IntLink, ExtLink, Router):
        nodes = self.nodes

        # 2-ary
        cpu_per_router = 2

        height = int(ceil (log ( (options.num_cpus / ( cpu_per_router / 2) ), 2)))
        #print("Tree height = " + str(height))

        num_routers = 0

        for i in range(height):
            num_routers += 2**i

        #print("Tree number of routers = " + str(num_routers))

        num_rows = height

        ## Define as latencias associadas.
        # default values for link latency and router latency.
        # Can be over-ridden on a per link/router basis
        link_latency = options.link_latency # used by simple and garnet
        router_latency = options.router_latency # only used by garnet
        
        ##add this for weight_update with topologies
       
        link_weight = [int(w) for w in options.link_weight.split(',')]
        if len(link_weight) < 2:
            link_weight += [link_weight[-1]] * (2 - len(link_weight))  # Fill missing weights
        ##end add
        

        # Determina quais nodos são controladores de cache vs diretórios vs DMA
        cache_nodes = []
        dir_nodes = []
        dma_nodes = []
        for node in nodes:
            if node.type == 'L1Cache_Controller' or \
            node.type == 'L2Cache_Controller':
                cache_nodes.append(node)
            elif node.type == 'Directory_Controller':
                dir_nodes.append(node)
            elif node.type == 'DMA_Controller':
                dma_nodes.append(node)

        # O número de linhas deve ser <= ao número de roteadores e divisivel por ele.
        # O número de diretórios deve ser igual a 4.
        assert(num_rows > 0 and num_rows <= num_routers)
        assert(len(dir_nodes) == 4)

        # Cria os roteadores
        routers = [Router(router_id=i, latency = router_latency) \
            for i in range(num_routers)]
        network.routers = routers
        
        ##we add this for task mapping
        # Initialize the adjacency matrix as a square matrix of size num_routers
        # and store it in the global dictionary under the network key.
        adjacency_matrix = [[0 for _ in range(num_routers)] for _ in range(num_routers)]
        adjacency_matrices[network] = adjacency_matrix
        #end add

        # Contador de ID's para gerar ID's únicos das ligações.
        link_count = 0

        # Conecta cada nodo ao seu roteador apropriado
        ext_links = []
        #print("Conectando os nodes aos roteadores\n")
        for (i, n) in enumerate(cache_nodes):
            cntrl_level, router_id = divmod(i, options.num_cpus // cpu_per_router)
            #print("Conectado o node " + str(n) + " ao roteador " + str((num_routers - router_id) - 1) + "\n")
            ext_links.append(ExtLink(link_id=link_count, ext_node=n,
                                    int_node=routers[(num_routers - router_id) - 1],
                                    latency = link_latency))
            link_count += 1

        # Conecta os diretórios aos 4 "cantos" : 1 no inicio, 1 no fim, 2 no centro.
        #print("Diretorio 1 ligado ao roteador " + str(num_routers - (options.num_cpus / cpu_per_router)))
        ext_links.append(ExtLink(link_id=link_count, ext_node=dir_nodes[0],
                                int_node=routers[num_routers - (options.num_cpus // cpu_per_router)],
                                latency = link_latency))
        link_count += 1

        #print("Diretorio 2 ligado ao roteador " + str((num_routers - 2**(height-2)) - 1))
        ext_links.append(ExtLink(link_id=link_count, ext_node=dir_nodes[1],
                                int_node=routers[(num_routers - 2**(height-2)) - 1],
                                latency = link_latency))
        link_count += 1

        #print("Diretorio 3 ligado ao roteador " + str(num_routers - 2**(height-2)))
        ext_links.append(ExtLink(link_id=link_count, ext_node=dir_nodes[2],
                                int_node=routers[(num_routers - 2**(height-2))],
                                latency = link_latency))
        link_count += 1

        #print("Diretorio 4 ligado ao roteador " + str(num_routers - 1))
        ext_links.append(ExtLink(link_id=link_count, ext_node=dir_nodes[3],
                                int_node=routers[num_routers - 1],
                                latency = link_latency))
        link_count += 1

        # Conecta os nodos de DMA ao roteador 0. These should only be DMA nodes.
        for (i, node) in enumerate(dma_nodes):
            assert(node.type == 'DMA_Controller')
            ext_links.append(ExtLink(link_id=link_count, ext_node=node,
                                     int_node=routers[0],
                                     latency = link_latency))

        network.ext_links = ext_links

        # Cria as conexões entre os roteadores em Butterfly
        #print("\nConectando os roteadores entre eles")
        int_links = []
        _out = 0
        fatness = height - 1
        
        added_links = set()  # Track (src, dst) to prevent duplicates


        for i in range(height - 1):
            for j in range(2**i):

                _in = _out * 2 + 1
                weight = link_weight[0]  # Use first weight level

                for f in range(2**fatness):
                    src_id = _out
                    dst_id = _in

                    if (src_id, dst_id) not in added_links:
                        int_links.append(IntLink(
                            link_id=link_count,
                            src_node=routers[src_id],
                            dst_node=routers[dst_id],
                            src_outport="South",
                            dst_inport="North",
                            latency=link_latency,
                            weight=weight
                        ))

                        # ? Update adjacency matrix
                        adjacency_matrix[src_id][dst_id] = weight
                        adjacency_matrix[dst_id][src_id] = weight  # Bidirectional

                        added_links.add((src_id, dst_id))
                        link_count += 1

                    dst_id = _out
                    src_id = _in

                    if (src_id, dst_id) not in added_links:
                        int_links.append(IntLink(
                            link_id=link_count,
                            src_node=routers[src_id],
                            dst_node=routers[dst_id],
                            src_outport="North",
                            dst_inport="South",
                            latency=link_latency,
                            weight=weight
                        ))

                        # ? Update adjacency matrix
                        adjacency_matrix[src_id][dst_id] = weight
                        adjacency_matrix[dst_id][src_id] = weight  # Bidirectional

                        added_links.add((src_id, dst_id))
                        link_count += 1

                _in = _out * 2 + 2
                weight = link_weight[1]  # Use second weight level

                for f in range(2**fatness):
                    src_id = _out
                    dst_id = _in

                    if (src_id, dst_id) not in added_links:
                        int_links.append(IntLink(
                            link_id=link_count,
                            src_node=routers[src_id],
                            dst_node=routers[dst_id],
                            src_outport="South",
                            dst_inport="North",
                            latency=link_latency,
                            weight=weight
                        ))

                        # ? Update adjacency matrix
                        adjacency_matrix[src_id][dst_id] = weight
                        adjacency_matrix[dst_id][src_id] = weight  # Bidirectional

                        added_links.add((src_id, dst_id))
                        link_count += 1

                    dst_id = _out
                    src_id = _in

                    if (src_id, dst_id) not in added_links:
                        int_links.append(IntLink(
                            link_id=link_count,
                            src_node=routers[src_id],
                            dst_node=routers[dst_id],
                            src_outport="North",
                            dst_inport="South",
                            latency=link_latency,
                            weight=weight
                        ))

                        # ? Update adjacency matrix
                        adjacency_matrix[src_id][dst_id] = weight
                        adjacency_matrix[dst_id][src_id] = weight  # Bidirectional

                        added_links.add((src_id, dst_id))
                        link_count += 1

                _out += 1

            fatness -= 1

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
        file_path = os.path.join(outdir, "FatTree_adjacency_matrix.txt")
        with open(file_path, "w") as f:
            for row in adjacency_matrix:
                f.write(" ".join(map(str, row)) + "\n")
    #end add