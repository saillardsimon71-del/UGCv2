import runpy
import sys
from pathlib import Path

folder = Path(__file__).resolve().parent / 'productions/UGCV2-FROZEN-RECIPE-20261030'
sys.path.insert(0, str(folder))
if __name__ == '__main__':
    runpy.run_path(str(folder / 'source_production.py'), run_name='__main__')
else:
    # Preserve the existing importable production API from the repository root.
    globals().update({k: v for k, v in runpy.run_path(str(folder/'production.py')).items()
                      if not k.startswith('__')})
