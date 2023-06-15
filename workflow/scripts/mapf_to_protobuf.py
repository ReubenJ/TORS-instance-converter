import argparse
import logging
import sys
from pathlib import Path

if Path(__file__).parent.parent.parent not in sys.path:
    sys.path.append(str(Path(__file__).parent.parent.parent))
    sys.path.append(str(Path(__file__).parent.parent.parent / "protos"))
else:
    sys.path.append("protos")

from protos.agent_pb2 import Agent
from protos.graph_pb2 import Graph, Node, NodeType
from protos.scenario_mapf_pb2 import Scenario

logger = logging.getLogger(__name__)


def main():
    """
    Script to convert the custom .graph and .scen files to protobuf format.

    Takes in a .scen and .graph file to convert. The graph file must match
    the graph mentioned in the .scen file. The .scen file must be in the
    same directory as the .graph file.
    """
    parser = argparse.ArgumentParser(
        description="Converts .graph and .scen " "files to protobuf format."
    )
    parser.add_argument("scen", help="The .scen file to convert.")
    parser.add_argument("graph", help="The .graph file to convert.")
    parser.add_argument("scenario_output", help="The output file to write the scenario to.")
    parser.add_argument("graph_output", help="The output file to write the graph to.")
    args = parser.parse_args()

    scen_path = Path(args.scen)
    graph_path = Path(args.graph)
    scenario_output = Path(args.scenario_output)
    graph_output = Path(args.graph_output)

    with open(scen_path, "r") as scen_file, open(graph_path, "r") as graph_file:
        assert scen_file.readline().strip() == "version 1 graph"
        assert scen_file.readline().strip() == graph_path.name

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

        scenario = Scenario()
        scenario.graph.CopyFrom(graph)
        num_agents = int(scen_file.readline().strip().split()[1])
        assert scen_file.readline().strip() == "types"

        while read := scen_file.readline().strip():
            if read == "agents starts":
                break
            match read.split():
                case type, *agents:
                    type = type.strip()
                    agents = [agent.strip() for agent in agents]
                    for agent in agents:
                        agent = Agent(name=agent, type=type)
                        scenario.agents.append(agent)
                case line:
                    raise Exception(
                        "Invalid scen file. The types section should "
                        f"be in the format: agent type. Found {line}."
                    )

        for _ in range(num_agents):
            match scen_file.readline().split():
                case agent, start:
                    agent = agent.strip()
                    start = start.strip()
                    # Get agent with matching name
                    agent = scenario.agents[
                        [a.name for a in scenario.agents].index(agent)
                    ]
                    agent.start = start
                    # scenario.agents.append(agent)
                case line:
                    raise Exception(
                        "Invalid scen file. The agents starts section "
                        f"should be in the format: agent start. Found {line}."
                    )

        assert scen_file.readline().strip() == "goals"
        for _ in range(num_agents):
            match scen_file.readline().split():
                case agent, goal:
                    agent = agent.strip()
                    goal = goal.strip()
                    # Get agent with matching name
                    agent = scenario.agents[
                        [a.name for a in scenario.agents].index(agent)
                    ]
                    agent.goal = goal

                case line:
                    raise Exception(
                        "Invalid scen file. The goals section "
                        f"should be in the format: agent goal. Found {line}."
                    )


        scenario_output.write_bytes(scenario.SerializeToString())
        graph_output.write_bytes(graph.SerializeToString())


if __name__ == "__main__":
    main()
