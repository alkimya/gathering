"""Test file for pylsp hover functionality."""
import sys
import os
from pathlib import Path

def greet(name: str) -> str:
    """
    Greet someone with a friendly message.
    
    Args:
        name: The person's name to greet
        
    Returns:
        A greeting string
    """
    return f"Hello, {name}!"

# Hover over 'sys' should show module documentation
print(sys.version)

# Hover over 'greet' should show the docstring
result = greet("World")

# Hover over 'Path' should show pathlib documentation
home = Path.home()
