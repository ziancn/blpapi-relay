"""
FASTAPI application entrypoint.
"""

import logging
from .app import app


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] <%(name)s> - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="localhost", port=8000)
    # uvicorn.run(app, host="0.0.0.0", port=8000)
