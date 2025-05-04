# src/__main__.py

import sys
from .main import _run_cli_mode, _BOTTLE_AVAILABLE, HOST, PORT, DEBUG_MODE, run as _bottle_run

if __name__ == "__main__":
    if len(sys.argv) > 1:
        _run_cli_mode()
    elif _BOTTLE_AVAILABLE:
        print(f"Starting web server on http://{HOST}:{PORT}  debug={DEBUG_MODE}")
        _bottle_run(host=HOST, port=PORT, debug=DEBUG_MODE, reloader=DEBUG_MODE)
    else:
        print("No arguments provided and Bottle is not installed. Exiting.")
        sys.exit(1)
