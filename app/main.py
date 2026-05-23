"""
FASTAPI application entrypoint.
"""

import argparse
import logging
from .app import app


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--debug", action="store_true")

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.INFO,
        format="%(asctime)s [%(levelname)s] <%(name)s> - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    import uvicorn
    uvicorn.run(app, host="localhost", port=8000)
    # uvicorn.run(app, host="0.0.0.0", port=8000)
