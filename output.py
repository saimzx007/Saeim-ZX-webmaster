#!/usr/bin/env python3
"""
Output handling: console printing and file saving.
"""

import json
import aiofiles
from typing import Dict, Optional
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

console = Console()

def print_result(url: str, status: int, size: int, content_type: str = '', verbose: bool = False, silent: bool = False):
    """
    Print a single result to the console with appropriate formatting.
    In normal mode, only interesting status codes (200,403,301,302,401,500) are shown.
    In verbose mode, all status codes including 404 are shown.
    """
    if silent:
        return

    # Determine color and icon based on status
    if status == 200:
        color = "green"
        icon = "✅"
        show = True
    elif status == 403:
        color = "red"
        icon = "🔒"
        show = True
    elif status in (301, 302):
        color = "yellow"
        icon = "🔄"
        show = True
    elif status == 401:
        color = "yellow"
        icon = "🔑"
        show = True
    elif status == 500:
        color = "red"
        icon = "💥"
        show = True
    elif status == 404:
        if verbose:
            color = "dim"
            icon = "❌"
            show = True
        else:
            show = False
    else:
        # For other status codes, only show in verbose mode
        if verbose:
            color = "white"
            icon = "📄"
            show = True
        else:
            show = False

    if show:
        console.print(f"  {icon} [{color}]{status:<4}[/{color}] {size:<7}  {url}")

def print_summary(stats: dict, found_urls: set, base_url: str, elapsed: float, silent: bool = False):
    """Print a summary table after scan completion."""
    if silent:
        return

    rps = stats['total'] / elapsed if elapsed > 0 else 0

    summary_table = Table(show_header=False, box=None)
    summary_table.add_column("Metric", style="cyan")
    summary_table.add_column("Value", style="white")

    summary_table.add_row("Target", base_url)
    summary_table.add_row("Time", f"{elapsed:.2f} s")
    summary_table.add_row("Requests", str(stats['total']))
    summary_table.add_row("Found", f"[green]{stats['found']}[/green]")
    summary_table.add_row("Errors", f"[red]{stats['errors']}[/red]")
    summary_table.add_row("Speed", f"{rps:.2f} req/sec")

    console.print("\n" + "="*60)
    console.print(Panel(summary_table, title="📊 Scan Summary", border_style="green"))
    console.print("="*60)

    if found_urls:
        console.print("\n[bold green]📌 Discovered URLs:[/bold green]")
        for url in sorted(found_urls)[:20]:  # Show first 20
            console.print(f"  • {url}")
        if len(found_urls) > 20:
            console.print(f"  ... and {len(found_urls)-20} more")
        console.print()

async def save_result(url: str, status: int, size: int, output_file: str):
    """
    Append a result to the output file. Supports .txt, .json, .csv based on extension.
    """
    ext = output_file.split('.')[-1].lower()
    try:
        if ext == 'json':
            # JSON Lines format
            entry = json.dumps({"url": url, "status": status, "size": size})
            async with aiofiles.open(output_file, 'a') as f:
                await f.write(entry + '\n')
        elif ext == 'csv':
            # Write header if file is new
            import os
            file_exists = os.path.isfile(output_file)
            async with aiofiles.open(output_file, 'a') as f:
                if not file_exists:
                    await f.write("url,status,size\n")
                await f.write(f'"{url}",{status},{size}\n')
        else:
            # Default text format
            async with aiofiles.open(output_file, 'a') as f:
                await f.write(f"{status} {size} {url}\n")
    except Exception as e:
        # Fail silently to not interrupt scan
        pass

def debug(msg: str):
    """Print debug message if enabled."""
    console.print(f"[dim][🐛 DEBUG][/] {msg}")

def error(msg: str):
    """Print error message."""
    console.print(f"[red][❌ ERROR][/] {msg}")