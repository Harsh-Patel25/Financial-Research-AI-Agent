import sys
import os

# To allow unmodified backend code (which imports 'app.main', 'app.services', etc.)
# to run while structured inside the 'backend' folder, we inject the backend directory
# into the sys.path when the backend package is initialized.

current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)
