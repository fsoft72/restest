#!/usr/bin/env python3
"""
Visual test for the dump action's new colored output format.
"""

import sys
sys.path.insert(0, ".")

from lib.engine import RESTest

# Create engine instance
rt = RESTest(base_url="http://localhost", quiet=True)

# Set some test variables
rt.globals["user_id"] = "123"
rt.globals["user_name"] = "John Doe"
rt.globals["item_count"] = 42
rt.globals["total_price"] = 99.99
rt.globals["tags"] = ["admin", "user", "premium"]
rt.globals["metadata"] = {
    "version": "1.0",
    "active": True,
    "count": 100
}

print("=" * 60)
print("Testing dump action with new colored format")
print("=" * 60)

print("\n1. Dump specific variables:")
print("-" * 60)
rt.dump(["user_id", "user_name", "item_count"], do_print=True)

print("\n2. Dump all variables:")
print("-" * 60)
rt.dump(None, do_print=True)

print("\n3. Test undefined variable:")
print("-" * 60)
rt.dump(["undefined_var"], do_print=True)

print("\n" + "=" * 60)
print("Visual test complete!")
print("=" * 60)
