import click

# mp-spdz imports:
from Compiler.compilerLib import Compiler
from . import synopsis


@click.group()
def cli():
    pass


@cli.command("run")
def run_cli():
    synopsis.run()


def main():
    cli()


if __name__ == "__main__":
    main()
