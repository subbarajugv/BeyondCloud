"""
Pytest configuration for BeyondCloud Python Backend
"""
import sys
from pathlib import Path

# Add the backend-python directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))
