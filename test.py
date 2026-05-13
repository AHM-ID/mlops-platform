import time

from shared.retrain_queue import RetrainQueueManager

import time
start = time.time()
queue_manager = RetrainQueueManager()
queue_length = queue_manager.get_queue_length()
print(f"Queue length query took {time.time() - start:.2f}s")
