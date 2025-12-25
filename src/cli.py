"""
Modern CLI interface using Click with rich output.
"""

import asyncio
import sys
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeRemainingColumn
from rich.live import Live
from rich import box

from src import __version__
from src.models import AttackMode, ProxyType, AttackConfig
from src.proxy_manager import ProxyManager
from src.attack_engine import AttackEngine
from src.logger import logger

console = Console()


def print_banner() -> None:
    """Print application banner."""
    banner = f"""
[bold cyan]╔══════════════════════════════════════════════════════╗
║   HTTP Load Tester - Educational Version {__version__}     ║
║   BTS SIO SISR - Cybersecurity Learning Tool        ║
╚══════════════════════════════════════════════════════╝[/bold cyan]

[yellow]⚠️  EDUCATIONAL PURPOSE ONLY[/yellow]
[dim]Use only on systems you own or have explicit permission to test.[/dim]
"""
    console.print(banner)


@click.group(invoke_without_command=True)
@click.option("--version", is_flag=True, help="Show version and exit")
@click.pass_context
def cli(ctx: click.Context, version: bool) -> None:
    """
    HTTP Load Testing Tool - Educational Version

    A professional load testing tool for authorized security testing and performance analysis.
    """
    if version:
        console.print(f"HTTP Load Tester EDU version {__version__}")
        sys.exit(0)

    if ctx.invoked_subcommand is None:
        print_banner()
        console.print("\n[yellow]Use --help to see available commands[/yellow]\n")


@cli.command()
@click.option(
    "--url", "-u",
    required=True,
    help="Target URL to test (must be whitelisted)",
)
@click.option(
    "--mode", "-m",
    type=click.Choice(["get", "post", "head", "slow", "http2"], case_sensitive=False),
    default="get",
    help="Attack mode",
)
@click.option(
    "--threads", "-t",
    type=int,
    default=100,
    help="Number of concurrent threads (default: 100)",
)
@click.option(
    "--duration", "-d",
    type=int,
    default=60,
    help="Test duration in seconds (default: 60)",
)
@click.option(
    "--proxy-file", "-f",
    type=click.Path(exists=True),
    help="Proxy file path",
)
@click.option(
    "--proxy-type", "-v",
    type=click.Choice(["socks4", "socks5", "http"], case_sensitive=False),
    default="socks5",
    help="Proxy type (default: socks5)",
)
@click.option(
    "--http2",
    is_flag=True,
    help="Use HTTP/2 protocol",
)
@click.option(
    "--simulation",
    is_flag=True,
    default=True,
    help="Run in simulation mode (default: true)",
)
@click.option(
    "--real",
    is_flag=True,
    help="Run real attack (disables simulation mode)",
)
@click.option(
    "--whitelist",
    multiple=True,
    help="Whitelisted domains (can be specified multiple times)",
)
@click.option(
    "--auth-token",
    help="Authorization token for real attacks",
)
@click.option(
    "--validate-proxies",
    is_flag=True,
    help="Validate proxies before attacking",
)
def attack(
    url: str,
    mode: str,
    threads: int,
    duration: int,
    proxy_file: Optional[str],
    proxy_type: str,
    http2: bool,
    simulation: bool,
    real: bool,
    whitelist: tuple,
    auth_token: Optional[str],
    validate_proxies: bool,
) -> None:
    """
    Launch a load test attack on the target URL.

    Examples:

      # Simulation mode (safe, no real requests)
      loadtest attack -u http://example.com --simulation

      # Real attack with authorization (requires token)
      loadtest attack -u http://testserver.local -t 200 -d 30 --real --auth-token YOUR_TOKEN

      # HTTP/2 test with proxies
      loadtest attack -u https://example.com --http2 -f proxies.txt
    """
    print_banner()

    # Determine simulation mode
    simulation_mode = simulation if not real else False

    # Create configuration
    try:
        config = AttackConfig(
            target_url=url,
            mode=AttackMode(mode.lower()),
            threads=threads,
            duration=duration,
            proxy_file=proxy_file or "proxy.txt",
            proxy_type=ProxyType(proxy_type.lower()),
            use_http2=http2 or mode.lower() == "http2",
            simulation_mode=simulation_mode,
            whitelist=list(whitelist) if whitelist else [],
            authorization_token=auth_token,
            require_authorization=not simulation_mode,
        )
    except Exception as e:
        console.print(f"[red]Configuration error: {e}[/red]")
        sys.exit(1)

    # Display configuration
    config_table = Table(title="Attack Configuration", box=box.ROUNDED)
    config_table.add_column("Parameter", style="cyan")
    config_table.add_column("Value", style="green")

    config_table.add_row("Target URL", config.target_url)
    config_table.add_row("Mode", config.mode.value.upper())
    config_table.add_row("Threads", str(config.threads))
    config_table.add_row("Duration", f"{config.duration}s")
    config_table.add_row("HTTP/2", "Yes" if config.use_http2 else "No")
    config_table.add_row(
        "Simulation Mode",
        "[yellow]YES (Safe)[/yellow]" if config.simulation_mode else "[red]NO (Real)[/red]"
    )

    console.print(config_table)

    # Confirm if real mode
    if not simulation_mode:
        console.print("\n[bold red]⚠️  WARNING: Real attack mode enabled![/bold red]")
        if not click.confirm("Do you have authorization to test this target?"):
            console.print("[yellow]Attack cancelled.[/yellow]")
            sys.exit(0)

    # Run attack
    asyncio.run(_run_attack(config, proxy_file, validate_proxies))


async def _run_attack(
    config: AttackConfig,
    proxy_file: Optional[str],
    validate_proxies: bool,
) -> None:
    """Run the attack asynchronously."""

    # Setup proxy manager if needed
    proxy_manager = None
    if proxy_file:
        console.print("\n[cyan]Loading proxies...[/cyan]")
        proxy_manager = ProxyManager(proxy_type=config.proxy_type)

        try:
            count = await proxy_manager.load_from_file(Path(proxy_file))
            console.print(f"[green]✓[/green] Loaded {count} proxies")

            # Validate if requested
            if validate_proxies:
                console.print("[cyan]Validating proxies...[/cyan]")
                with Progress(
                    SpinnerColumn(),
                    TextColumn("[progress.description]{task.description}"),
                    BarColumn(),
                    TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                    console=console,
                ) as progress:
                    task = progress.add_task("Validating...", total=count)
                    working = await proxy_manager.validate_proxies()
                    progress.update(task, completed=count)

                console.print(f"[green]✓[/green] {working} working proxies")
        except Exception as e:
            console.print(f"[red]Proxy error: {e}[/red]")
            return

    # Create attack engine
    engine = AttackEngine(config, proxy_manager)

    # Progress display
    console.print("\n[bold green]Starting attack...[/bold green]\n")

    # Live stats display
    with Live(console=console, refresh_per_second=2) as live:
        # Update callback
        def update_display(_stats=None):
            stats = engine.get_stats()

            stats_table = Table(title="Live Statistics", box=box.DOUBLE)
            stats_table.add_column("Metric", style="cyan", width=30)
            stats_table.add_column("Value", style="yellow", width=20)

            stats_table.add_row("Total Requests", str(stats.total_requests))
            stats_table.add_row("Successful", f"[green]{stats.successful_requests}[/green]")
            stats_table.add_row("Failed", f"[red]{stats.failed_requests}[/red]")
            stats_table.add_row("Success Rate", f"{stats.success_rate:.2f}%")
            stats_table.add_row("Requests/sec", f"{stats.requests_per_second:.2f}")

            if stats.avg_response_time > 0:
                stats_table.add_row("Avg Response Time", f"{stats.avg_response_time*1000:.2f}ms")

            if proxy_manager:
                proxy_stats = proxy_manager.get_stats()
                stats_table.add_row("Active Proxies", str(proxy_stats["active"]))

            live.update(stats_table)

        engine.on_stats_update = update_display

        # Start attack
        try:
            final_stats = await engine.start()
        except KeyboardInterrupt:
            console.print("\n[yellow]Attack interrupted by user[/yellow]")
            await engine.stop()
            final_stats = engine.get_stats()
        except Exception as e:
            console.print(f"\n[red]Attack failed: {e}[/red]")
            logger.error("attack_failed", error=str(e), exc_info=True)
            return

    # Final results
    _display_final_results(final_stats)


def _display_final_results(stats) -> None:
    """Display final attack results."""
    console.print("\n")

    results = Table(title="Final Results", box=box.DOUBLE_EDGE)
    results.add_column("Metric", style="bold cyan", width=30)
    results.add_column("Value", style="bold yellow", width=25)

    results.add_row("Session ID", stats.session_id)
    results.add_row("Target", stats.target_url)
    results.add_row("Mode", stats.mode.value.upper())
    results.add_row("Duration", f"{stats.duration:.2f}s")
    results.add_row("Total Requests", str(stats.total_requests))
    results.add_row("Successful", f"[green]{stats.successful_requests}[/green]")
    results.add_row("Failed", f"[red]{stats.failed_requests}[/red]")
    results.add_row("Success Rate", f"{stats.success_rate:.2f}%")
    results.add_row("Requests/sec", f"{stats.requests_per_second:.2f}")
    results.add_row("Avg Response Time", f"{stats.avg_response_time*1000:.2f}ms")

    if stats.status_codes:
        codes = ", ".join(f"{code}: {count}" for code, count in stats.status_codes.items())
        results.add_row("Status Codes", codes)

    console.print(results)
    console.print("\n[green]✓ Attack completed successfully[/green]\n")


@cli.command()
@click.option(
    "--type", "-v",
    type=click.Choice(["socks4", "socks5", "http"], case_sensitive=False),
    default="socks5",
    help="Proxy type to download",
)
@click.option(
    "--output", "-o",
    type=click.Path(),
    default="proxy.txt",
    help="Output file path (default: proxy.txt)",
)
@click.option(
    "--validate",
    is_flag=True,
    help="Validate proxies after download",
)
def download(type: str, output: str, validate: bool) -> None:
    """Download proxies from public sources."""
    print_banner()

    console.print(f"[cyan]Downloading {type.upper()} proxies...[/cyan]\n")

    asyncio.run(_download_proxies(ProxyType(type.lower()), Path(output), validate))


async def _download_proxies(proxy_type: ProxyType, output_file: Path, validate: bool) -> None:
    """Download proxies asynchronously."""
    manager = ProxyManager(proxy_type)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Downloading from sources...", total=None)
        count = await manager.download_proxies(output_file)
        progress.update(task, completed=100)

    console.print(f"\n[green]✓[/green] Downloaded {count} proxies to {output_file}")

    if validate and count > 0:
        console.print("\n[cyan]Validating proxies...[/cyan]")

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            console=console,
        ) as progress:
            task = progress.add_task("Validating...", total=count)
            working = await manager.validate_proxies()
            progress.update(task, completed=count)

        console.print(f"[green]✓[/green] {working}/{count} proxies are working")

        # Save working proxies
        await manager._save_proxies(output_file)
        console.print(f"[green]✓[/green] Saved {working} working proxies to {output_file}")


@cli.command()
@click.argument("proxy_file", type=click.Path(exists=True))
@click.option(
    "--type", "-v",
    type=click.Choice(["socks4", "socks5", "http"], case_sensitive=False),
    default="socks5",
    help="Proxy type",
)
@click.option(
    "--timeout",
    type=int,
    default=5,
    help="Validation timeout in seconds (default: 5)",
)
def validate(proxy_file: str, type: str, timeout: int) -> None:
    """Validate a list of proxies."""
    print_banner()

    console.print(f"[cyan]Validating proxies from {proxy_file}...[/cyan]\n")

    asyncio.run(_validate_proxies(Path(proxy_file), ProxyType(type.lower()), timeout))


async def _validate_proxies(file_path: Path, proxy_type: ProxyType, timeout: int) -> None:
    """Validate proxies from file."""
    from src.config import settings
    settings.proxy_check_timeout = timeout

    manager = ProxyManager(proxy_type)
    count = await manager.load_from_file(file_path)

    console.print(f"Loaded {count} proxies")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TimeRemainingColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("Validating...", total=count)
        working = await manager.validate_proxies()
        progress.update(task, completed=count)

    console.print(f"\n[green]✓[/green] {working}/{count} proxies are working ({working/count*100:.1f}%)")

    # Save working proxies
    output_file = file_path.parent / f"{file_path.stem}_validated{file_path.suffix}"
    await manager._save_proxies(output_file)
    console.print(f"[green]✓[/green] Saved working proxies to {output_file}")


def main() -> None:
    """Main entry point."""
    try:
        cli()
    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted by user[/yellow]")
        sys.exit(130)
    except Exception as e:
        console.print(f"\n[red]Fatal error: {e}[/red]")
        logger.error("fatal_error", error=str(e), exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
