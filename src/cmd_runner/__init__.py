from uvicorn import run

from typer import Typer

from cmd_runner.api import app

cli = Typer()

@cli.command()
def run_server(reload: bool = False, config_file: str = ""):
    """Run the FastAPI server."""
    run("cmd_runner.api:app", host="0.0.0.0", port=8000, reload=reload)


__all__ = ["app"]