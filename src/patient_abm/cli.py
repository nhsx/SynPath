import sys

import click

from patient_abm.simulation.run import simulate
from patient_abm.simulation.template import parse_config


def print_and_exit(msg: str, code: int = 1, prefix="ERROR: ") -> None:
    """Print error message and exit with given code."""
    click.echo(f"\n{prefix}{msg}\n", err=True)
    sys.exit(code)


@click.group()
def cli():
    pass


@cli.group(name="simulation")
def simulate_group():
    """CLI group to simulate patient pathway"""


@simulate_group.command(name="run")
@click.option(
    "--config_path",
    required=True,
    help="Path to config file",
)
def run_simulation_command(config_path: str):
    """Run simulation by running the simulaion for one patient at a time,
    looping over patients.

    - Loads and validates the config json file
    - Initializes the patients, environments, intelligence layer and
    other variables as per the specification in the config file
    - Runs the simulation by looping over patients, with logging
    - Saves the outputs in the config file save_dir

    Parameters
    ----------
    config_path : str
        Path to simulation config file
    """

    print(f"Parsing config from {config_path}")
    config = parse_config(config_path)

    print("Starting simulation")
    simulate(config)
