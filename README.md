---
title: CanyonMix
tags: ["_active", "MITgcm", "Alford"]
---




##  MITGCM version

The version I'll use is the `varbd_bt` branch of my own fork.  https://github.com/jklymak/MITgcm/

## Mixing on a slope...



- running smooth versions with 0.6 m/s forcing.  Need to check alpha.  Try sub and supercritical at the same alpha.  Too strong stratification and overturns cannot develop.  Rough seafloor leads to more turnulence (a lot), so can play with hfac.  hfac=1 is much more turbulence than hfac=0.1.

- guess is that turbulent strength leads to upwelling speeds.


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


## To run

  - run `python gendata.py`
  - run `qsub -N jobname runModel.sh`
