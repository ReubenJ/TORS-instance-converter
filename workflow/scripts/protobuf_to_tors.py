import logging
from argparse import ArgumentParser

import networkx as nx
from google.protobuf.json_format import MessageToJson

from protos.scenario_mapf_pb2 import Scenario as MAPFScenario
from protos.Location_pb2 import Location, TrackPart, TrackPartType
from protos.Scenario_pb2 import Scenario, Train, TrainUnit
from protos.TrainUnitTypes_pb2 import TrainUnitType

from pathlib import Path

logger = logging.getLogger(__name__)


def reduce_degree(graph: nx.Graph):
    """
    Reduces the maximum degree of a graph to be 3.

    This is done by adding a new node that connects two of the
    neighbors of the offending node that has a degree greater than 3.
    """

    # Split up nodes with degree > 3
    for offender in [n for n, d in graph.degree() if d > 3]:
        neighbors = list(graph.neighbors(offender))
        # Remove the offender from the graph
        graph.remove_node(offender)
        prev_node = neighbors[0]
        # Add a new node for each neighbor of the offender
        # each new node should be connected to the previous new node
        # starting with the first neighbor of the offender
        for i, neighbor in enumerate(neighbors[1:]):
            new_node = f"{offender}.{i}"
            graph.add_node(new_node)
            graph.add_edge(prev_node, new_node)
            graph.add_edge(new_node, neighbor)
            prev_node = new_node

    return graph


def create_track_parts(location_graph: nx.Graph, args):
    tors_id_start = 1

    return (
        TrackPart(
            id=tors_id,
            type=TrackPartType.RailRoad,
            name=node,
            aSide=[],
            bSide=[],
            length=args.length,
            parkingAllowed=True,
            sawMovementAllowed=True,
            isElectrified=True,
        )
        for tors_id, node in enumerate(location_graph.nodes, tors_id_start)
    )


def main():
    parser = ArgumentParser(
        description="Converts .scen.pb files to TORS protobuf format."
    )
    parser.add_argument("scen", help="The .scen.pb file to convert.")
    parser.add_argument(
        "--length", help="The length of the track parts.", default=100, type=int
    )
    parser.add_argument(
        "--max-carriages",
        help="The maximum number of carriages per train.",
        default=3,
        type=int,
    )
    parser.add_argument(
        "--time-between-arrivals",
        help="The time between arrivals.",
        default=100,
        type=int,
    )
    parser.add_argument(
        "--time-between-departures",
        help="The time between departures.",
        default=100,
        type=int,
    )
    parser.add_argument(
        "--output-directory",
        help="The directory to output the files to.",
        default=Path("."),
        type=Path,
    )
    args = parser.parse_args()

    scen_path = args.scen

    with open(scen_path, "rb") as scen_file:
        mapf_scenario = MAPFScenario()
        mapf_scenario.ParseFromString(scen_file.read())
    mapf_graph = mapf_scenario.graph

    tors_location = Location()

    adjacency_list = [" ".join([node.id, *node.neighbors]) for node in mapf_graph.nodes]
    location_graph = nx.adjlist.parse_adjlist(
        adjacency_list, nodetype=str, create_using=nx.Graph
    )

    location_graph = reduce_degree(location_graph)

    track_parts = create_track_parts(location_graph, args)
    tors_location.trackParts.extend(track_parts)

    names = [track.name for track in tors_location.trackParts]
    for edge in location_graph.edges:
        first_track = tors_location.trackParts[names.index(edge[0])]
        second_track = tors_location.trackParts[names.index(edge[1])]
        if len(first_track.aSide) == 0:
            first_track.aSide.append(second_track.id)
        else:
            first_track.bSide.append(second_track.id)
        if len(second_track.aSide) == 0:
            second_track.aSide.append(first_track.id)
        else:
            second_track.bSide.append(first_track.id)

        for track in [first_track, second_track]:
            if len(track.bSide) == 2:
                track.type = TrackPartType.Switch

    # write the location to a file as json
    with open(args.output_directory / "location.json", "w") as location_file:
        location_file.write(
            MessageToJson(tors_location, including_default_value_fields=True)
        )

    tors_scenario = Scenario(
        startTime=0,
        endTime=3000,
    )

    # Get types of agents
    agent_types = set(agent.type for agent in mapf_scenario.agents)
    print(agent_types)
    # Create a TrainUnitType for each agent type
    for i, agent_type in enumerate(agent_types):
        n_carriages = (i % args.max_carriages) + 1
        new_type = TrainUnitType(
            displayName=agent_type,
            carriages=n_carriages,
            length=n_carriages * 20,
            combineDuration=180,
            splitDuration=120,
            backNormTime=120,
            backAdditionTime=16,
            travelSpeed=0,
            startUpTime=0,
            typePrefix=str(agent_type),
            needsLoco=False,
            needsElectricity=False,
        )
        tors_scenario.trainUnitTypes.append(new_type)
    print(getattr(tors_scenario, "in"))

    # Create incoming/outgoing from the agents
    for i, agent in enumerate(mapf_scenario.agents):
        # first create a TrainUnit object for each agent
        new_train_unit = TrainUnit(
            id=agent.name,
            typeDisplayName=agent.type,
        )
        # first create a Train object for each agent
        new_train = Train(
            id=agent.name,
            time=i * args.time_between_arrivals,
            members=[new_train_unit],
        )
        # add the train to the incoming list
        tors_scenario.incoming.append(new_train)
    print(tors_location.trackParts)


if __name__ == "__main__":
    main()
