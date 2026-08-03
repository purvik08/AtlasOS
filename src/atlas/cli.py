import asyncio
import platform

import click
import psutil

from atlas.config.settings import AtlasConfig
from atlas.runtime.application import AtlasApplication


@click.group()
def cli():
    """Atlas OS Command Line Interface."""
    pass


@cli.command()
async def start_async():
    config = AtlasConfig()
    app = AtlasApplication(config)
    await app.run_forever()


@cli.command(name="start")
def start():
    asyncio.run(start_async())


if __name__ == "__main__":
    cli()


@cli.command()
def doctor():
    print("\nAtlas OS Diagnostics")
    print("----------------------")
    print(f"CPU Usage : {psutil.cpu_percent()}%")
    print(f"RAM Usage : {psutil.virtual_memory().percent}%")


@cli.command()
def version():
    """Show version."""
    print("Atlas OS")
    print("Version : 0.1.0")
    print("Python  :", platform.python_version())
    print("System  :", platform.system())
