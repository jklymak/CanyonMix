from pathlib import Path
import subprocess

with open('.joblog') as fin:
    for l in fin:
        parts = l.split()
        name = parts[0]
        jobstat = f'{name:50s} '
        jobids = f'{name:50s} '
        status = parts[1]
        pending = False
        running = False
        for jobid in parts[2:]:
            jobid = jobid.strip('\n')
            cmd = f'sacct -j {jobid} -n --format=State,Reason,ExitCode,Elapsed'
            res = subprocess.run(cmd, shell=True, capture_output=True)
            std = res.stdout.decode('utf-8', 'ignore').split()
            if not pending and std[0] == 'PENDING':
                pending = True
                # pending often gives wrong reason in sacct, so try squeue:
                cmd = f'squeue -j {jobid} -h --format="%r"'
                res = subprocess.run(cmd, shell=True, capture_output=True)
                std2 = res.stdout.decode('utf-8', 'ignore').split()

                jobstat += f'{jobid}: {std[0]} {std2[0]}  '
            elif std[0] == 'PENDING':
                jobstat += f'{jobid} '
            elif std[0] == 'COMPLETED':
                jobstat += f'{jobid}: done: {std[2]}  '
            else:
                jobstat += f'{jobid}: {std[0]}  '
            if std[0] == 'RUNNING':
                running = True
                elapsed = std[3]

            jobids += jobid + ' '
        print(jobstat)
        print(jobids)
        if running:
            stdout = f'../results/{name}/input/STDOUT.0000'
            cmd = f'grep time_secondsf {stdout} | tail -1'
            res = subprocess.run(cmd, shell=True, capture_output=True)
            res = res.stdout.decode('utf-8', 'ignore')
            try:
                time = float(res.split()[-1])
                print(f'Model-time: {time/24/3600:1.2f} days')
                cfl = {}
                for td in ['u', 'v', 'w']:
                    cmd = f'grep advcfl_{td}vel_max {stdout} | tail -1'
                    res = subprocess.run(cmd, shell=True, capture_output=True)
                    res = res.stdout.decode('utf-8', 'ignore')
                    cfl[td]= float(res.split()[-1])
                print(f"CFL: u: {cfl['u']:1.2f}, v: {cfl['v']:1.2f}, w: {cfl['w']:1.2f}")
            except:
                print('Model started, but no output yet')
            print(f"Elapsed time {elapsed}")
            running = False
        print()