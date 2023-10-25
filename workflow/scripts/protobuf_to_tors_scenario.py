import logging
import sys
from argparse import ArgumentParser
from pathlib import Path

from google.protobuf.json_format import MessageToJson, Parse, MessageToDict, ParseDict

if Path(__file__).parent.parent.parent not in sys.path:
    sys.path.append(str(Path(__file__).parent.parent.parent))
    sys.path.append(str(Path(__file__).parent.parent.parent / "protos"))
else:
    sys.path.append("protos")

from protos.scenario_mapf_pb2 import Scenario as MAPFScenario
from protos.agent_pb2 import Agent
from protos.Location_pb2 import Location, TrackPartType, TrackPart
from protos.TrainUnitTypes_pb2 import TrainUnitType, TrainUnitTypes
from protos.Scenario_pb2 import Scenario, Train, TrainUnit

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def has_bumper_connected(gate_track_part: TrackPart, location: Location) -> bool:
    """
    Returns True if the given gate track part has a bumper connected to it.
    """
    # Get all track parts connected to the gate track part
    connected_track_part_ids = list(gate_track_part.aSide) + list(gate_track_part.bSide)
    connected_track_parts = [
        track_part
        for track_part in location.trackParts
        if track_part.id in connected_track_part_ids
    ]
    # Check if any of the connected track parts are bumpers
    for connected_track_part in connected_track_parts:
        if connected_track_part.type == TrackPartType.Bumper:
            return True
    return False


def get_connected_track_of_type(
    track_part: TrackPart, location: Location, track_type: TrackPartType
) -> list[TrackPart]:
    """
    Returns the track parts of the given type connected to the given track part.

    Logs a warning if no track parts of the given type are found.
    """
    # Get all track parts connected to the given track part
    connected_track_part_ids = list(track_part.aSide) + list(track_part.bSide)
    connected_track_parts = [
        track_part
        for track_part in location.trackParts
        if track_part.id in connected_track_part_ids
    ]
    # Filter out track parts that are not of the given type
    connected_track_parts = [
        track_part
        for track_part in connected_track_parts
        if track_part.type == track_type
    ]
    if len(connected_track_parts) < 1:
        logger.warning(
            f"Could not find any track parts of type {track_type} connected to track "
            "part {track_part.name}"
        )
    return connected_track_parts


def find_track_part_by_name(track_part_name: str, location: Location) -> TrackPart:
    """
    Returns the track part with the given name in the given location.

    Raises a ValueError if no track part with the given name is found.
    """
    for track_part in location.trackParts:
        if track_part.name == track_part_name:
            return track_part
    raise ValueError(f"Could not find track part with name {track_part_name}")


def add_train(
    tors_scenario_dict: dict,
    agent: Agent,
    location: Location,
    time: int,
    incoming: str,
) -> Train:
    """
    Adds a train to the given TORS scenario dictionary.
    """
    logger.debug(f"Adding train for agent {agent.name}.")
    train_unit = TrainUnit(
        id=str(agent.name),
        typeDisplayName=agent.type,
    )
    train = Train(
        id=agent.name,
        members=[train_unit],
    )

    # If either of the start or goal track parts are a gate, then we need to
    # find the bumper and its corresponding railway TrackPart
    if "g-" in agent.start_or_end_track:
        # Get all gate TrackParts (all track parts with the names "g-1", "g-2", etc.")
        gate_track_parts = [
            track_part for track_part in location.trackParts if "g-" in track_part.name
        ]
        if len(gate_track_parts) < 1:
            raise ValueError(
                "Could not find any gate track parts when constructing train."
            )
        # Find the gate track with a bumper track part connected to it
        connected_to_bumper = [
            track_part
            for track_part in gate_track_parts
            if has_bumper_connected(track_part, location)
        ]
        if len(connected_to_bumper) != 1:
            raise ValueError(
                "Expected 1 gate track part connected to a bumper, "
                f"but got {len(connected_to_bumper)}"
            )
        gate_track_part = connected_to_bumper[0]
        bumper_track_parts = get_connected_track_of_type(
            gate_track_part, location, TrackPartType.Bumper
        )
        if len(bumper_track_parts) != 1:
            raise ValueError(
                "Expected 1 bumper track part connected to start, "
                f"but got {len(bumper_track_parts)}"
            )
    train.time = time
    key_to_place_train_in_for_gate = "in" if incoming else "out"
    key_to_place_train_in_for_non_gate = "inStanding" if incoming else "outStanding"

    if "g-" in agent.start_or_end_track:
        train.parkingTrackPart = gate_track_part.id
        train.sideTrackPart = bumper_track_parts[0].id
        tors_scenario_dict[key_to_place_train_in_for_gate].append(
            MessageToDict(train, including_default_value_fields=True)
        )
    else:
        # Get the starting track part corresponding to the agent's start
        parking_track_part = find_track_part_by_name(agent.start_or_end_track, location)
        neighboring_track_parts = get_connected_track_of_type(
            parking_track_part, location, TrackPartType.RailRoad
        )
        train.parkingTrackPart = parking_track_part.id
        train.sideTrackPart = neighboring_track_parts[0].id
        tors_scenario_dict[key_to_place_train_in_for_non_gate].append(
            MessageToDict(train, including_default_value_fields=True)
        )

    return tors_scenario_dict


def calculate_arrival_times(
    mapf_scenario: MAPFScenario,
    time_between_trains: int,
) -> list[int]:
    """
    Calculates the arrival times for the given MAPF scenario.

    The arrival order of the agents is determined by their starting point.
    There are (usually) multiple gate tracks, and the agents are ordered by
    the gate track they start at. If one agent starts at gate track g-1 and another
    starts at gate track g-2, then the agent starting at g-2 will arrive first.

    The arrival times are calculated by adding some multiple of the time between
    trains to the start time of the scenario (0).

    Example:
    - Start time: 0
    - Time between trains: 100
    - Trains and their start tracks:
        - Agent 1: g-1
        - Agent 2: g-3
        - Agent 3: b-1-p-5
        - Agent 4: g-2

    - Arrival times:
        - Agent 1: 300
        - Agent 2: 100
        - Agent 3: 0
        - Agent 4: 200

    Returns:
        A list of arrival times for each agent in the given MAPF scenario.
    """
    logger.debug("Calculating arrival times.")
    arrival_times = {}
    gate_agents = [
        agent
        for agent in mapf_scenario.incoming_agents
        if "g-" in agent.start_or_end_track
    ]
    gate_agents.sort(key=lambda agent: int(agent.start_or_end_track.split("-")[1]))
    for i, agent in enumerate(gate_agents):
        arrival_times[agent.name] = (i + 1) * time_between_trains
    non_gate_agents = [
        agent
        for agent in mapf_scenario.incoming_agents
        if "g-" not in agent.start_or_end_track
    ]
    for i, agent in enumerate(non_gate_agents):
        arrival_times[agent.name] = 0

    logger.debug(f"Arrival times: {arrival_times}")

    arrival_times_list = []
    for agent in mapf_scenario.incoming_agents:
        arrival_times_list.append(arrival_times[agent.name])

    return arrival_times_list


def calculate_departure_times(
    mapf_scenario: MAPFScenario,
    time_between_trains: int,
    total_time: int,
) -> list[int]:
    """
    Calculates the departure times for the given MAPF scenario.

    The departure order of the agents is determined by their goal point.
    There are (usually) multiple gate tracks, and the agents are ordered by
    the gate track they end at. If one agent ends at gate track g-1 and another
    ends at gate track g-2, then the agent ending at g-2 will depart last.

    The departure times are calculated by subtracting some multiple of the time between
    trains from the total time.

    Example:
    - Total time: 1000
    - Time between trains: 100
    - Trains and their goal tracks:
        - Agent 1: g-1
        - Agent 2: g-3
        - Agent 3: b-1-p-5
        - Agent 4: g-2

    - Departure times:
        - Agent 1: 1000 - 2 * 100 = 800
        - Agent 2: 1000 - 1 * 100 = 900
        - Agent 3: 1000
        - Agent 4: 1000 - 3 * 100 = 700

    Return:
    - A list of departure times, where the index of the departure time corresponds
      to the index of the agent in the MAPF scenario.
    """
    logger.debug(f"Calculating departure times. Total time: {total_time}")
    sort_order = sorted(
        range(len(mapf_scenario.outgoing_agents)),
        key=lambda k: (
            mapf_scenario.outgoing_agents[k].start_or_end_track.split("-")[1]
        ),
    )
    logger.debug(f"Sort order: {sort_order}")
    departure_times = []
    for i, agent in enumerate(mapf_scenario.outgoing_agents):
        if "g-" in agent.start_or_end_track:
            logger.debug(f"Agent {agent.name} is a gate agent.")
            departure_times.append(total_time - (i + 1) * time_between_trains)
        else:
            logger.debug(f"Agent {agent.name} is not a gate agent.")
            departure_times.append(total_time)
    
    logger.debug(f"Departure times: {departure_times}")

    departure_times_list = []
    for i in sort_order:
        departure_times_list.append(departure_times[i])

    return departure_times_list


def main():
    parser = ArgumentParser(
        description="Converts .scen.pb files to TORS protobuf/json format."
    )
    parser.add_argument("scenario", help="The .scen.pb file to convert.")
    parser.add_argument("location", help="The corresponding location .json file.")
    parser.add_argument("output", help="The output file to write to.", type=Path)
    parser.add_argument(
        "--length", help="The length of the trains.", default=100, type=int
    )
    parser.add_argument(
        "--n-carriages", help="The number of carriages per train.", default=1, type=int
    )
    parser.add_argument(
        "--time-between-trains", help="The time between trains.", default=100, type=int
    )
    parser.add_argument(
        "--total-time", help="The total time of the scenario.", default=None, type=int
    )
    args = parser.parse_args()

    scenario_path: Path = args.scenario
    location_path: Path = args.location
    output_path: Path = args.output
    n_carriages: int = args.n_carriages
    time_between_trains: int = args.time_between_trains
    length: int = args.length
    total_time: int = args.total_time

    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Check if the total time is set, if not, calculate it, if it is, check if it is
    # possible to fit all the trains in the scenario in the given time
    with open(scenario_path, "rb") as graph_file:
        mapf_scenario = MAPFScenario()
        mapf_scenario.ParseFromString(graph_file.read())
    # Need to multiply by 2 because we need to account for the inbound and outbound
    rough_total_time = (
        time_between_trains * len(mapf_scenario.incoming_agents) * 2
    ) + 500
    if total_time is None:
        total_time = rough_total_time
    elif total_time < rough_total_time:
        raise ValueError(
            f"Total time is set to {total_time}, but the scenario probably needs at "
            "least {rough_total_time} time units to complete."
        )

    with open(scenario_path, "rb") as graph_file:
        mapf_scenario = MAPFScenario()
        mapf_scenario.ParseFromString(graph_file.read())

    with open(location_path, "r") as location_file:
        location = Location()
        Parse(location_file.read(), location)

    # Create all the train unit types
    tors_train_unit_types = TrainUnitTypes()
    tors_train_unit_types.types.extend(
        [
            TrainUnitType(
                displayName=agent.type,
                carriages=n_carriages,
                length=n_carriages * length,
                combineDuration=180,
                splitDuration=120,
                backNormTime=120,
                backAdditionTime=16,
                travelSpeed=0,
                startUpTime=0,
                typePrefix=str(agent.type),
                needsLoco=False,
                needsElectricity=False,
            )
            for agent in mapf_scenario.incoming_agents
        ]
    )

    tors_scenario = Scenario()
    for unit_type in tors_train_unit_types.types:
        tors_scenario.trainUnitTypes.append(unit_type)
    tors_scenario.endTime = total_time
    # Convert scenario to dictionary so we can add the incoming trains
    # because the protobuf definition uses the field name "in" which is a reserved
    # keyword in python
    tors_scenario_dict = MessageToDict(
        tors_scenario, including_default_value_fields=True
    )

    arrival_times = calculate_arrival_times(mapf_scenario, time_between_trains)
    departure_times = calculate_departure_times(
        mapf_scenario, time_between_trains, total_time
    )

    for agent, arrival_time in zip(mapf_scenario.incoming_agents, arrival_times):
        tors_scenario_dict = add_train(
            tors_scenario_dict,
            agent,
            location,
            arrival_time,
            incoming=True,
        )
    for agent, departure_time in zip(mapf_scenario.outgoing_agents, departure_times):
        tors_scenario_dict = add_train(
            tors_scenario_dict,
            agent,
            location,
            departure_time,
            incoming=False,
        )
    tors_scenario = ParseDict(tors_scenario_dict, Scenario())

    # write the location to a file as json
    with open(output_path, "w") as output_file:
        output_file.write(
            MessageToJson(tors_scenario, including_default_value_fields=True)
        )


if __name__ == "__main__":
    main()
