import os
import subprocess

# timestep to use in model (runModel.sh will modify this in `data``)
dt=30
# how long the model needs to run in wall time:
timetorun = "0-00:30:00"  # this _should_ override what is in runModel.sh
# seconds per day
day=86400
# restart every ddays  Note we are saving pickups every 3 days, so this
# should be multiple of 3...
ddays = 3

runModelName = 'runModel.sh'

for todo in ['Slope2D059']:
    outstr = f"{todo} queued "
    res = subprocess.check_output(["sbatch", f"--job-name={todo}",
                         f"--export=start={day*0},stop={day*(ddays) + 180},dt={dt}",
                         f"--time={timetorun}",
                         f"{runModelName}"])
    job = res.decode('utf8').split()[-1]
    outstr += f"{job} "
    if False:
        for i in range(1, 1):
            res = subprocess.check_output(["sbatch", f"--job-name={todo}",
                         f"--dependency=afterok:{job}",
                         f"--export=start={day*ddays*i},stop={day*ddays*(i+1) + 180},dt={dt}",
                         f"--time={timetorun}",
                         f"{runModelName}"])
            job = res.decode('utf8').split()[-1]
            outstr += f"{job} "
    if False:
        res = subprocess.check_output(["sbatch", f"--job-name={todo}",
                            f"--dependency=afterok:{job}",
                            f"../python/rungetWorkMean.sh"])
        job = res.decode('utf8').split()[-1]
        outstr += f"{job} "
        # store info in a file
        print(outstr)
    with open(".joblog", "a") as joblog:
        joblog.write(outstr+"\n")
