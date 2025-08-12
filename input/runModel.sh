#!/bin/bash
#SBATCH --account=def-jklymak
#SBATCH --mail-user=jklymak@gmail.com
#SBATCH --mail-type=ALL
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=8
#SBATCH --time=0-04:30
#SBATCH --mem=0

# run from runAll.sh  start and stop come from -v arguments.

# module swap mpt compiler/intelmpi

module load StdEnv/2023
module load intel
PARENT=CanyonMix

cd $PBS_O_WORKDIR

top=${SLURM_JOB_NAME}
results=${PROJECT}/jklymak/${PARENT}/results/
outdir=$results$top

cd $outdir/input
pwd
ls -al ../build/mitgcmuv

# python moddata.py --startTime=$start --endTime=$stop --deltaT=$dt

printf "Starting: $outdir\n"
module list
which srun
srun ../build/mitgcmuv > mit.out