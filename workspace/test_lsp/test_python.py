"""
Test Python file for LSP autocomplete testing.

This file demonstrates LSP features:
- Import autocomplete
- Method autocomplete
- Keyword autocomplete
"""

import os
import sys


def calculate_area(radius: float) -> float:
    """Calculate the area of a circle."""
    import math
    # Type 'math.' here to test autocomplete
    return math.pi * radius ** 2


def process_data(data: list) -> dict:
    """Process a list of data items."""
    result = {}

    # Type 'result.' here to test dict methods autocomplete
    # Type 'data.' here to test list methods autocomplete

    for item in data:
        if isinstance(item, str):
            result[item] = len(item)

    return result


class DataProcessor:
    """Example class for testing autocomplete."""

    def __init__(self, name: str):
        self.name = name
        self.items = []

    def add_item(self, item):
        """Add an item to the processor."""
        # Type 'self.' here to test attribute autocomplete
        self.items.append(item)

    def get_count(self) -> int:
        """Get the number of items."""
        return len(self.items)


if __name__ == "__main__":
    # Test autocomplete here
    processor = DataProcessor("test")
    # Type 'processor.' to see method autocomplete

    # Type 'sys.' to see system module autocomplete
    print(f"Python version: {sys.version}")
