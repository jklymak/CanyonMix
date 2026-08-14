# make a short script that parses ../results/{runname}/input/STDOUT.0000 and finds the latest time, and checks advcfl_uvel_max and advcfl_wvel_max latest values:

#(PID.TID 0000.0001) %MON time_secondsf                =   9.8208000000000E+05
#(PID.TID 0000.0001) %MON advcfl_uvel_max              =   6.3251104256454E-02
#(PID.TID 0000.0001) %MON advcfl_wvel_max              =   1.6769195422873E-01

import os
import re
from pathlib import Path

def parse_stdout(runname):
    stdout_path = Path('..') / 'results' / runname / 'input' / 'STDOUT.0000'

    if not stdout_path.exists():
        print(f"STDOUT file not found for runname: {runname}")
        return

    latest_time = None
    advcfl_uvel_max = None
    advcfl_wvel_max = None

    with open(stdout_path, 'r') as f:
        for line in f:
            # Match lines that contain time and advcfl values
            time_match = re.search(r'time_secondsf\s*=\s*(\d+\.\d+E[+-]\d+)', line)
            uvel_match = re.search(r'advcfl_uvel_max\s*=\s*(\d+\.\d+E[+-]\d+)', line)
            wvel_match = re.search(r'advcfl_wvel_max\s*=\s*(\d+\.\d+E[+-]\d+)', line)

            if time_match:
                latest_time = float(time_match.group(1))
            if uvel_match:
                advcfl_uvel_max = float(uvel_match.group(1))
            if wvel_match:
                advcfl_wvel_max = float(wvel_match.group(1))

    print(f"Latest Time: {latest_time} {latest_time/3600:.1f} hours {latest_time/12.4/3600:.1f} T")
    print(f"advcfl_uvel_max: {advcfl_uvel_max}")
    print(f"advcfl_wvel_max: {advcfl_wvel_max}")

def main():
    # parse command line arguments for runname
    import argparse
    parser = argparse.ArgumentParser(description='Parse STDOUT for latest time and advcfl values.')
    parser.add_argument('runname', type=str, help='The name of the run to parse.')
    args = parser.parse_args()
    parse_stdout(args.runname)

if __name__ == "__main__":
    main()