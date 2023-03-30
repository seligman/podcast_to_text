#!/usr/bin/env python3

import subprocess
import os

for cur in os.listdir("examples"):
    if cur.endswith(".example.json"):
        print(f"Rebuilding {cur}...")
        subprocess.check_call(["python3", "to_text.py", "create_webpage", os.path.join("examples", cur)])
