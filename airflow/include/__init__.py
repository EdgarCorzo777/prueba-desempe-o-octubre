import sys
import os

# Expose include as both top-level 'include' and 'airflow.include'
# to ensure compatibility across all Airflow container versions and runners
if "include" in sys.modules:
    sys.modules["airflow.include"] = sys.modules["include"]
