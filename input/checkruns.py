from pathlib import Path
import subprocess
import sys

def check_run(run_name):
    stdout = Path(f"../results/{run_name}/input/STDOUT.0000")
    if not stdout.exists():
        print(f"STDOUT file not found for run: {run_name}")
        return

    # Get latest model time
    cmd = f'grep time_secondsf {stdout} | tail -1'
    res = subprocess.run(cmd, shell=True, capture_output=True)
    res = res.stdout.decode('utf-8', 'ignore')
    try:
        time = float(res.split()[-1])
        tidal_cycles = time / 3600 / 12.4
        print(f"Model-time: {tidal_cycles:1.2f} tidal cycles")
    except Exception as e:
        print('Model started, but no output yet')
        return

    # Get latest CFL values
    cfl = {}
    for td in ['u', 'v', 'w']:
        cmd = f'grep advcfl_{td}vel_max {stdout} | tail -1'
        res = subprocess.run(cmd, shell=True, capture_output=True)
        res = res.stdout.decode('utf-8', 'ignore')
        try:
            cfl[td] = float(res.split()[-1])
        except Exception:
            cfl[td] = None
    print(f"CFL: u: {cfl['u'] if cfl['u'] is not None else 'N/A':1.2f}, v: {cfl['v'] if cfl['v'] is not None else 'N/A':1.2f}, w: {cfl['w'] if cfl['w'] is not None else 'N/A':1.2f}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python checkruns.py <run_name>")
    else:
        check_run(sys.argv[1])
