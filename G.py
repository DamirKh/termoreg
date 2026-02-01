
print("Globals loading...")
from primitives.queue import Queue

MAIN_IF = ""
IN_QUEUE = Queue(maxsize=10)
OUT_QUEUE = Queue(maxsize=100)
DEVICES = {}

INPUT_TAG = {}
OUTPUT_TAG = {}
