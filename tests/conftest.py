import os

# Ensure headless Qt initialization for CI and local non-GUI environments.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
