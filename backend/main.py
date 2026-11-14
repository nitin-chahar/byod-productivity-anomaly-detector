"""
Main CLI entry point for batch simulation of BYOD student activity.
Maintained for backwards compatibility with legacy execution commands.
"""

from simulate import run_simulation

if __name__ == "__main__":
    run_simulation(delay=1.5)
