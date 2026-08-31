"""Command-line interface for Prospect."""

import typer

from prospect_ai import __version__

app = typer.Typer(help="Prospect: Semantic cache & reverse proxy for LLM inference")


@app.command()
def version() -> None:
    """Show version."""
    typer.echo(f"prospect {__version__}")


@app.command()
def start(
    port: int = typer.Option(8080, help="Port to listen on"),
    similarity_threshold: float = typer.Option(0.92, help="Semantic similarity threshold"),
    backend: str = typer.Option("memory", help="Cache backend (memory, sqlite-vec, redis)"),
) -> None:
    """Start Prospect proxy server."""
    typer.echo(
        f"Starting Prospect on port {port} "
        f"(similarity_threshold={similarity_threshold}, backend={backend})"
    )
    typer.echo("Phase 1: Server implementation in progress")


@app.command()
def stats() -> None:
    """Show cache statistics."""
    typer.echo("Cache Statistics:")
    typer.echo("Phase 1: Stats aggregation in progress")


if __name__ == "__main__":
    app()
