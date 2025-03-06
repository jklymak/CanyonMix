# AbHillParam runs but with isolated roughness

##  MITGCM version

The version I'll use is the `varbd_bt` branch of my own fork.  https://github.com/jklymak/MITgcm/

## Mixing on a slope...


`../../MITgcm/tools/genmake2 -optfile=../build_options/onyx -mods=../code/ -rootdir=../../MITgcm -mpi`



### Todo:

Internal tide forcing with a shelf with passthrough is OK (`StraightSlopeExpStrat002`), but definitely concentrated near break.   If I don't have a shelf, then the internal tide is quite weak because the velocity isn't very large (standing wave)

Thats OK, but if I want to invert the stratification, then the forcing is still very focused at the break.

Maybe just have straight

### To run:

- in `intput`: `python gendata.py`
- `source runAll.sh`
  - this runs a chained set of 2-hr jobs (on koehr) in the background queue.  This will allow us to not use allocation.

## Contents:

  - `input` is where most model setup occurs.
  - `python` is where most processing occurs.

## Vagaries

   - Need `miniconda3` on the path!

## To compile on onyx

  - `module load cray-mpich`
  - `cd build/`
  - `../../MITgcm/tools/genmake2 -optfile=../build_options/onyx -mods=../code/ -rootdir=../../MITgcm -mpi`
  - `make depend`.  This will have some errors near the end about not being able to find source files for `module netcdf`.  This error is annoying but doesn't affect compile.
  - `make`

## To run

  - run `python gendata.py`
  - run `qsub -N jobname runModel.sh`
