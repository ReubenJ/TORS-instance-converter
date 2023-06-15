import logging
from argparse import ArgumentParser
from pathlib import Path

import networkx as nx
from google.protobuf.json_format import MessageToJson
import sys

if Path(__file__).parent.parent.parent not in sys.path:
    sys.path.append(str(Path(__file__).parent.parent.parent))
    sys.path.append(str(Path(__file__).parent.parent.parent / "protos"))
else:
    sys.path.append("protos")


from protos.graph_pb2 import Graph
from protos.Location_pb2 import Location, TrackPart, TrackPartType


logging.basicConfig(level=logging.WARN)
logger = logging.getLogger(__name__)


def reduce_degree(graph: nx.Graph):
    """
    Reduces the maximum degree of a graph to be 3.

    This is done by adding a new node that connects two of the
    neighbors of the offending node that has a degree greater than 3.
    """
    offenders = [n for n, d in graph.degree() if d > 3]
    logger.debug(f"Degree of nodes: {graph.degree()}")
    logger.info(f"Found {len(offenders)} nodes with degree > 3.")

    # Split up nodes with degree > 3
    for offender in offenders:
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


def remove_extra_gate_nodes(graph: nx.Graph):
    """
    Removes all gate nodes from the graph except for the first two.

    This is done by counting the number of gate nodes in the graph.
    If there are more than two gate nodes, the extra gate nodes are removed
    from the graph. Gate nodes' names start with "g-".
    """
    gate_nodes = [node for node in graph.nodes if node.startswith("g-")]
    logger.debug(f"Gate nodes: {gate_nodes}")
    if len(gate_nodes) > 2:
        # Sort the gate nodes by their name
        gate_nodes.sort(key=lambda node: int(node.split("-")[-1]))
        logger.debug(f"Sorted gate nodes: {gate_nodes}")
        # Remove all but the last two gate nodes (these are the ones connected to the
        # rest of the yard)
        for node in gate_nodes[:-2]:
            graph.remove_node(node)
    else:
        logger.warning(
            "There are less than two gate nodes in the graph. "
            "This might cause errors in the TORS simulator."
        )
    return graph


def process_switch(track, tors_location):
    if len(track.bSide) == 2:
        assert len(track.aSide) == 1, "Switch has more than one track on A side"
        track.type = TrackPartType.Switch
        logger.debug("Track id %s is a switch", track.id)
        # # check that the two tracks on the B side of the switch are from
        # # different branches

        # # first, get the full track object for both tracks on the B side
        # b_side_tracks = [
        #     track_part
        #     for track_part in tors_location.trackParts
        #     if track_part.id in track.bSide
        # ]
        # # then, check that the two tracks are from different branches



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
        description="Converts .graph.pb files to TORS protobuf format."
    )
    parser.add_argument("graph", help="The .graph.pb file to convert.")
    parser.add_argument("output", help="The output file to write to.", type=Path)
    parser.add_argument(
        "--length", help="The length of the track parts.", default=100, type=int
    )
    args = parser.parse_args()

    graph_path = args.graph

    with open(graph_path, "rb") as graph_file:
        mapf_graph = Graph()
        mapf_graph.ParseFromString(graph_file.read())

    tors_location = Location()

    adjacency_list = [" ".join([node.id, *node.neighbors]) for node in mapf_graph.nodes]
    location_graph = nx.adjlist.parse_adjlist(
        adjacency_list, nodetype=str, create_using=nx.Graph
    )

    location_graph = remove_extra_gate_nodes(location_graph)

    location_graph = reduce_degree(location_graph)

    track_parts = create_track_parts(location_graph, args)
    tors_location.trackParts.extend(track_parts)

    names = [track.name for track in tors_location.trackParts]
    # Add the edges to the track parts
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


    for track in tors_location.trackParts:
        process_switch(track, tors_location)

    # Add an exit bumper if carrousel style
    # Get the ends of the branches
    # Each branch track is named "b-<branch number>-p-<position in branch>"
    # The end of each branch number is the track with the highest position in the branch
    # First get the number of branches
    branch_numbers = set(
        [
            track.name.split("-")[1]
            for track in tors_location.trackParts
            if track.name.startswith("b-")
        ]
    )
    logger.debug(f"Branch numbers: {branch_numbers}")
    # Then get the end of each branch
    branch_ends = [
        max(
            [
                track
                for track in tors_location.trackParts
                if track.name.startswith(f"b-{branch_number}")
            ],
            key=lambda track: int(track.name.split("-")[-1]),
        )
        for branch_number in branch_numbers
    ]
    logger.debug(f"Branch ends: {branch_ends}")
    end_of_lowest_branch = min(
        branch_ends, key=lambda track: int(track.name.split("-")[-1])
    )
    # Turn the end of the lowest branch into a switch, add a railroad track to the other
    # side of the switch, and add a bumper track to the end of the railroad track
    end_of_lowest_branch.type = TrackPartType.Switch
    # Create a new railroad track part to connect to the switch
    new_railroad_track = TrackPart(
        id=len(tors_location.trackParts) + 1,
        type=TrackPartType.RailRoad,
        name=f"end-{end_of_lowest_branch.name}",
        aSide=[end_of_lowest_branch.id],
        bSide=[],
        length=args.length,
        parkingAllowed=True,
        sawMovementAllowed=True,
        isElectrified=True,
    )
    # The (now switch) at the end of the lowest should have the single neighbor
    # side of the switch be the new railroad track part and the double neighbor
    # side of the switch be the end of the lowest branch and the other railroad
    # track part from the second to last branch
    current_a = end_of_lowest_branch.aSide.pop()
    end_of_lowest_branch.aSide.append(new_railroad_track.id)
    end_of_lowest_branch.bSide.append(current_a)
    tors_location.trackParts.append(new_railroad_track)

    # Add bumper tracks to track parts with only one neighbor
    # Get trackParts with only one neighbor
    one_neighbor_tracks = [
        track for track in tors_location.trackParts if len(track.bSide) == 0
    ]
    for track in one_neighbor_tracks:
        # Create a new bumper track part
        bumper_track = TrackPart(
            id=len(tors_location.trackParts) + 1,
            type=TrackPartType.Bumper,
            name=f"bumper-{track.name}",
            aSide=[track.id],
            bSide=[],
            length=0,
            parkingAllowed=False,
            sawMovementAllowed=False,
            isElectrified=False,
        )
        # Add the bumper track to the bSide of the track
        track.bSide.append(bumper_track.id)
        # Add the bumper track to the location
        tors_location.trackParts.append(bumper_track)

    # write the location to a file as json
    with open(args.output, "w") as location_file:
        location_file.write(
            MessageToJson(tors_location, including_default_value_fields=True)
        )


if __name__ == "__main__":
    main()
