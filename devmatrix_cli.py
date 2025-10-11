#!/usr/bin/env python3
"""
Devmatrix CLI Entry Point

This is the main entry point for the devmatrix command-line interface.
"""

import sys
from src.cli.main import cli

if __name__ == "__main__":
    sys.exit(cli())
