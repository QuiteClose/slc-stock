import logging
import sys


def setup_logging(level: int = logging.INFO):
    fmt = "%(asctime)s %(levelname)s %(name)s — %(message)s"
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(fmt, datefmt="%Y-%m-%d %H:%M:%S"))

    root = logging.getLogger("slc_stock")
    root.setLevel(level)
    if not root.handlers:
        root.addHandler(handler)

    return root
