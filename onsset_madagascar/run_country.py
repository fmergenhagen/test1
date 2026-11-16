"""Run a GEP-OnSSET scenario for one country from a calibrated input file.

usage: python run_country.py <specs.xlsx> <calibrated.csv> <resource_dir> <out_dir>
The resource dir must hold <cc>-2-pv.csv and <cc>-2-wind.csv.
"""
import os, sys, time
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "code"))
specs, csv, res, out = sys.argv[1:5]
os.environ["GEP_RESOURCE_DIR"] = res
os.makedirs(out, exist_ok=True)
from runner import scenario
t = time.time()
scenario(specs, csv, out, out)
print("done in %.0f s" % (time.time() - t))
