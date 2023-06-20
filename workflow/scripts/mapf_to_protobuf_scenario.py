import argparse
import logging
import sys
from pathlib import Path

if Path(__file__).parent.parent.parent not in sys.path:
    sys.path.append(str(Path(__file__).parent.parent.parent))
    sys.path.append(str(Path(__file__).parent.parent.parent / "protos"))
else:
    sys.path.append("protos")

from protos.scenario_mapf_pb2 import Scenario
from protos.agent_pb2 import Agent

logger = logging.getLogger(__name__)


def main():
    """
    Script to convert the custom .scen files to protobuf format.

    Takes in a .scen file to convert.
    """
    parser = argparse.ArgumentParser(
        description="Converts .scen" "files to protobuf format."
    )
    parser.add_argument("scenario_file", help="The .scen file to convert.")
    parser.add_argument(
        "scenario_output", help="The output file to write the graph to."
    )
    args = parser.parse_args()

    scenario_path = Path(args.scenario_file)
    scenario_output = Path(args.scenario_output)

    with open(scenario_path, "r") as scenario_file:
        assert scenario_file.readline().strip() == "version 1 graph"
        graph_filename = scenario_file.readline().strip()
        num_agents = int(scenario_file.readline().strip().split()[1])

        agent_type_mapping = {}
        while (type_assignment := scenario_file.readline().strip()) != "agents starts":
            agent_type, *agent_ids = type_assignment.split()
            for agent_id in agent_ids:
                agent_type_mapping[agent_id] = agent_type

        scenario = Scenario()
        scenario.graph = graph_filename
        for _ in range(num_agents):
            agent_id, start = scenario_file.readline().strip().split()
            agent = Agent()
            agent.name = agent_id
            agent.type = agent_type_mapping[agent_id]
            agent.start_or_end_track = start
            scenario.incoming_agents.append(agent)
        
        assert scenario_file.readline().strip() == "goals"

        for agent in range(num_agents):
            agent_type, goal = scenario_file.readline().strip().split()
            agent = Agent()
            agent.name = "***"
            agent.type = agent_type
            agent.start_or_end_track = goal
            scenario.outgoing_agents.append(agent)

        scenario_output.write_bytes(scenario.SerializeToString())


if __name__ == "__main__":
    main()
