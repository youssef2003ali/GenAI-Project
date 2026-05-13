"""Run the FastAPI backend with configurable host and port from .env or defaults.

Usage:
    python run_backend.py                          # uses HOST/PORT from .env
    python run_backend.py --port 8080              # override port
    python run_backend.py --host 127.0.0.1 --port 9000
"""

import argparse
import uvicorn
from packages.shared.src.acs_shared.settings import settings

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Run the ACS backend')
    parser.add_argument('--host', default=settings.host, help='Bind address (default: %(default)s)')
    parser.add_argument('--port', type=int, default=settings.port, help='Bind port (default: %(default)s)')
    parser.add_argument('--reload', action='store_true', help='Enable hot-reload for development')
    args = parser.parse_args()

    print(f'Starting backend on {args.host}:{args.port}')
    uvicorn.run(
        'packages.backend.main:app',
        host=args.host,
        port=args.port,
        reload=args.reload,
    )
