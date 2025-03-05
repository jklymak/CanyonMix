#!/bin/bash
#SBATCH --account=def-jklymak
#SBATCH --mail-user=jklymak@gmail.com
#SBATCH --mail-type=ALL
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --time=0-00:45
#SBATCH --mem=0

source ~/venvs/AbHillInter2/bin/activate

PARENT=AbHillInterNew
cd $PROJECT/jklymak/$PARENT/python
pwd
todo=${SLURM_JOB_NAME}

# python getWork.py $todo
python getMeanVel.py $todo
python get2D.py $todo

rsync -av ../reduceddata/${SLURM_JOB_NAME}/ pender.seos.uvic.ca:AbHillInterAnalysis/reduceddata/${SLURM_JOB_NAME}
