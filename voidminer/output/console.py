from __future__ import annotations

from rich.console import Console


console = Console()


def info(message: str, silent: bool = False) -> None:
    if not silent:
        console.print(f"[cyan][*][/cyan] {message}")


def success(message: str, silent: bool = False) -> None:
    if not silent:
        console.print(f"[green][+][/green] {message}")


def warn(message: str, silent: bool = False) -> None:
    if not silent:
        console.print(f"[yellow][!][/yellow] {message}")
