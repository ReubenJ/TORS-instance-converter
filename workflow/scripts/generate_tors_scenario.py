"""Takes a TORS location json file and generates a scenario file for the location."""
import logging
import random
import sys
from dataclasses import dataclass
from pathlib import Path

import wonderwords

if Path(__file__).parent.parent not in sys.path:
    sys.path.append(str(Path(__file__).parent.parent / "protos"))
else:
    sys.path.append("protos")

from protos.Location_pb2 import Location, TrackPart, TrackPartType
from protos.Scenario_pb2 import Scenario, Train, TrainUnit, ShuntingUnit
from protos.TrainUnitTypes_pb2 import TrainUnitType, TrainUnitTypes

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

@dataclass
class ScenarioGeneratorSettings:
    number_of_trains: int
    minimum_units_per_train: int = 1
    maximum_units_per_train: int = 5
    minimum_length: int = 20
    maximum_length: int = 100
    random_seed: int = 42
    # The proportion of unique train unit types in the scenario. A value of 1 means that
    # all train unit types are unique. A value of 0 means that all train unit types are the same.
    proportion_of_unique_train_unit_types: float = 1
    # Trains that are already in the location when the scenario starts
    proportion_instanding_trains: float = 0
    # Trains that are still in the location when the scenario ends
    proportion_outstanding_trains: float = 0


def generate_tors_scenario(location: Location, output_dir: Path, settings: ScenarioGeneratorSettings):
    """
    Generates a scenario for the given location.

    The scenario is generated according to the given settings.
    """
    # Set the random seed
    random.seed(settings.random_seed)
    # Create the types
    train_unit_types = TrainUnitTypes()
    number_of_train_unit_types = int(settings.number_of_trains * settings.proportion_of_unique_train_unit_types)
    for i in range(number_of_train_unit_types):
        random_prefix = wonderwords.RandomWord().word()
        random_name = wonderwords.RandomWord().word()
        train_unit_type = TrainUnitType(
            displayName=f"{random_prefix}-{random_name}",
            carriages=random.randint(settings.minimum_units_per_train, settings.maximum_units_per_train),
            length=random.randint(settings.minimum_length, settings.maximum_length),
            combineDuration=180,
            splitDuration=120,
            backNormTime=120,
            backAdditionTime=16,
            travelSpeed=0,
            startUpTime=0,
            typePrefix="SLT",
            needsLoco=False,
            isLoco=False,
            needsElectricity=True
        )
        train_unit_types.trainUnitTypes.append(train_unit_type)

    num_instanding_trains = int(settings.number_of_trains * settings.proportion_instanding_trains)
    num_incoming_trains = settings.number_of_trains - num_instanding_trains

