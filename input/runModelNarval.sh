#!/bin/bash
#SBATCH --account=def-jklymak
#SBATCH --mail-user=jklymak@gmail.com
#SBATCH --mail-type=ALL
#SBATCH --nodes=3
#SBATCH --ntasks-per-node=64
#SBATCH --time=0-10:30
#SBATCH --mem=0

# run from runAll.sh  start and stop come from -v arguments.

# module swap mpt compiler/intelmpi

module load netcdf-fortran-mpi/4.5.2
module load python/3.9.6


PARENT=AbHillInterNew

cd $SLURM_SUBMIT_DIR
printf 'workdir? $SLURM_SUBMIT_DIR'
pwd
top=${SLURM_JOB_NAME}
printf "top: $top\n"
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