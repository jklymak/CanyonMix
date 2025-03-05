#!/bin/bash
#SBATCH --account=def-jklymak
#SBATCH --mail-user=jklymak@gmail.com
#SBATCH --mail-type=ALL
#SBATCH --nodes=4
#SBATCH --ntasks-per-node=48
#SBATCH --time=0-10:30
#SBATCH --mem=0
#SBATCH --constraint=[skylake]

# run from runAll.sh  start and stop come from -v arguments.

# module swap mpt compiler/intelmpi

PARENT=AbHillInterNew

cd $PBS_O_WORKDIR

top=${SLURM_JOB_NAME}
results=${PROJECT}/jklymak/${PARENT}/results/
outdir=$results$top

cd $outdir/input
pwd
ls -al ../build/mitgcmuv

python moddata.py --startTime=$start --endTime=$stop --deltaT=$dt

printf "Starting: $outdir\n"
module list
which srun
srun ../build/mitgcmuv > mit.out