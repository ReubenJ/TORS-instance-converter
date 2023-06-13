import argparse
import logging
import sys
from pathlib import Path

sys.path.append("protos")

from protos.graph_pb2 import Graph, Node, NodeType

logger = logging.getLogger(__name__)


def main():
    """
    Script to convert the custom .graph files to protobuf format.

    Takes in a .scen and .graph file to convert. The graph file must match
    the graph mentioned in the .scen file. The .scen file must be in the
    same directory as the .graph file.
    """
    parser = argparse.ArgumentParser(
        description="Converts .graph" "files to protobuf format."
    )
    parser.add_argument("graph", help="The .graph file to convert.")
    parser.add_argument("graph_output", help="The output file to write the graph to.")
    args = parser.parse_args()

    graph_path = Path(args.graph)
    graph_output = Path(args.graph_output)

    with open(graph_path, "r") as graph_file:
        assert graph_file.readline().strip() == "type graph"
        num_nodes = int(graph_file.readline().strip().split()[1])
        assert graph_file.readline().strip() == "map"

        graph = Graph()
        for _ in range(num_nodes):
            match graph_file.readline().split():
                case node, *neighbors:
                    node = node.strip()
                    neighbors = [neighbor.strip() for neighbor in neighbors]
                    node_type = (
                        NodeType.GATE if node.startswith("g-") else NodeType.BRANCH
                    )
                    node = Node(id=node, neighbors=neighbors, type=node_type)
                    graph.nodes.append(node)
                case line:
                    raise Exception(
                        "Invalid graph file. The map section should "
                        "be in the format: node neighbor1 neighbor2 ..."
                        f" neighborN. Found {line}."
                    )

        graph_output.write_bytes(graph.SerializeToString())


if __name__ == "__main__":
    main()
