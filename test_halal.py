import sys
import os
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from project.core.halal.pipeline import screen_stock
import json

print("Testing AAPL (General Tech - Likely Compliant)")
res1 = screen_stock("AAPL", use_cache=False)
print(json.dumps(res1, indent=2))

print("\nTesting JPM (Banking - Non-Compliant)")
res2 = screen_stock("JPM", use_cache=False)
print(json.dumps(res2, indent=2))
