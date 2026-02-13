"""Main entry point for research agent team."""

import sys
import asyncio
from .config import get_config
from .agents import run_manager_agent


def main(query: str | None = None) -> str:
    """
    Run the research agent with a query.

    Args:
        query: The research query. If None, uses default demo query.

    Returns:
        The generated research report as markdown.
    """
    config = get_config()

    # Validate configuration
    errors = config.validate()
    if errors:
        print("Configuration errors:")
        for error in errors:
            print(f"  - {error}")
        print("\nPlease set required environment variables in .env file.")
        sys.exit(1)

    # Use default query if none provided
    if query is None:
        query = "Compare Cisco's observability portfolio (Splunk, AppDynamics) to DataDog and Dynatrace"

    print(f"Research Query: {query}")
    print("-" * 50)

    # Run the manager agent
    result = asyncio.run(run_manager_agent(query))

    return result


def cli():
    """Command line interface entry point."""
    if len(sys.argv) > 1:
        query = " ".join(sys.argv[1:])
    else:
        query = None

    report = main(query)
    print("\n" + "=" * 50)
    print("RESEARCH REPORT")
    print("=" * 50)
    print(report)


if __name__ == "__main__":
    cli()
