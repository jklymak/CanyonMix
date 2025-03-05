#!/bin/bash
#SBATCH --account=def-jklymak
#SBATCH --mail-user=jklymak@gmail.com
#SBATCH --mail-type=ALL
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=48
#SBATCH --time=0-00:35
#SBATCH --mem=0

source ~/venvs/AbHillInter2/bin/activate

PARENT=AbHillInterNew
cd $PROJECT/jklymak/$PARENT/python
pwd
todo=${SLURM_JOB_NAME}

# python getWork.py $todo
python getSliceZarr.py $todo
# python get2D.py $todo

rsync -av ../reduceddata/${todo}/ pender.seos.uvic.ca:AbHillInterAnalysis/reduceddata/${todo}
