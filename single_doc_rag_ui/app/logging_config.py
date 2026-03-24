import logging
from collections import deque
from datetime import datetime

log_queue = deque(maxlen=100)

class MemoryHandler(logging.Handler):
    def emit(self, record):
        try:
            msg = self.format(record)
            log_queue.append({
                "timestamp": datetime.fromtimestamp(record.created).strftime("%H:%M:%S"),
                "level": record.levelname,
                "message": record.getMessage(),
                "name": record.name.split('.')[-1]
            })
        except Exception:
            pass

def setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    
    memory_handler = MemoryHandler()
    formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")
    memory_handler.setFormatter(formatter)
    
    root_logger = logging.getLogger()
    root_logger.addHandler(memory_handler)