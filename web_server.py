#!/usr/bin/env python3

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.web.app import run

if __name__ == "__main__":
    print("""
    ╔══════════════════════════════════════════════════════╗
    ║   HTTP Load Tester EDU - Web Dashboard              ║
    ║   Starting server...                                 ║
    ╚══════════════════════════════════════════════════════╝

    Dashboard will be available at: http://127.0.0.1:8080

    Press Ctrl+C to stop the server.
    """)

    run()
