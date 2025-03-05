#!/bin/bash
#SBATCH --account=def-jklymak
#SBATCH --mail-user=jklymak@gmail.com
#SBATCH --mail-type=ALL
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=48
#SBATCH --time=0-06:00
#SBATCH --mem=0
#SBATCH --constraint=[skylake]

# run from runAll.sh  start and stop come from -v arguments.

module swap mpt compiler/intelmpi

PARENT=AbHillInter

cd $PBS_O_WORKDIR

PARENT=AbHillInter
top=${SLURM_JOB_NAME}
results=${PROJECT}/jklymak/${PARENT}/results/
outdir=$results$top

cd $outdir/input
pwd
ls -al ../build/mitgcmuv

python moddata.py --startTime=$start --endTime=$stop --deltaT=$dt

printf "Starting: $outdir\n"
mpiexec -N 48 ../build/mitgcmuv > mit.out
