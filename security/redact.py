"""Masquage des secrets dans les logs."""
import logging, re

class RedactFilter(logging.Filter):
    def filter(self, record):
        if isinstance(record.msg, str):
            record.msg = re.sub(r"[A-Za-z0-9_\-]{20,}\.[A-Za-z0-9_\-]{5,}\.[A-Za-z0-9_\-]{20,}", "<TOKEN>", record.msg)
        return True

def setup_logging():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    for h in logging.root.handlers:
        h.addFilter(RedactFilter())
