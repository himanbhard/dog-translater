import os
import sys

# Add project root to sys.path so `src` can be imported during tests.
ROOT = os.path.dirname(os.path.dirname(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
