# mamba activate canyonsim: (numpy xarray netcdf4 xmitgcm matplotlib)

import numpy as np

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
# from pylab import *
from shutil import copy
from os import mkdir
import shutil,os,glob
import scipy.signal as scisig
import logging
from replace_data import replace_data

logging.basicConfig(level=logging.INFO)

_log = logging.getLogger(__name__)


if True:
  runname = 'StraightSlopeExpStrat001'
  comments = "Just gettings started"

  u0 = 20
  N0 = 1e-3
  f0 = 1.410e-4
  f0 = 0.0
  geo_beta = 0.0

  outdir0='../results/'+runname+'/'

  # reset f0 in data
  shutil.copy('data', 'dataF')
  replace_data('dataF', 'f0', '%1.3e'%f0)
  replace_data('dataF', 'beta', '%1.3e'%geo_beta)

  # model size
  nx = 8 * 120
  ny = 1
  nz = 200

  _log.info('nx %d ny %d', nx, ny)


  #### Set up the output directory
  backupmodel = True
  if backupmodel:
    try:
      mkdir(outdir0)
    except:
      import datetime
      import time
      ts = time.time()
      st=datetime.datetime.fromtimestamp(ts).strftime('%Y%m%d%H%M%S')
      shutil.move(outdir0[:-1],outdir0[:-1]+'.bak'+st)
      mkdir(outdir0)

      _log.info(outdir0+' Exists')

    indir =outdir0+'/indata/'

    try:
        mkdir(indir)
    except:
      pass

    outdir=outdir0+'input/'
    try:
      mkdir(outdir)
    except:
      _log.info(outdir+' Exists')
    try:
        mkdir(outdir+'/figs/')
    except:
      pass

    copy('gendata.py',outdir)
    copy('moddata.py',outdir)
  else:
    outdir=outdir+'input/'

  ## Copy some other files
  _log.info( "Copying files")

  try:
    shutil.rmtree(outdir+'/../code/')
  except:
    _log.info("code is not there anyhow")
  shutil.copytree('../code', outdir+'/../code/')
  shutil.copytree('../python', outdir+'/../python/')

  try:
    shutil.rmtree(outdir+'/../build/')
  except:
    _log.info("build is not there anyhow")
  _log.info(outdir+'/../build/')
  mkdir(outdir+'/../build/')

  try:
      # copy any data that is in the local indata
      shutil.copytree('../indata/', outdir+'/../indata/')
  except:
      pass

  if True:
      shutil.copy('../build/mitgcmuv', outdir+'/../build/mitgcmuv')
      shutil.copy('../build/Makefile', outdir+'/../build/Makefile')
      shutil.copy('dataF', outdir+'/data')
      shutil.copy('eedata', outdir)
      shutil.copy('data.kl10', outdir)
      shutil.copy('data.btforcing', outdir)
      try:
        shutil.copy('data.kpp', outdir)
      except:
        pass
      try:
        shutil.copy('data.var_bot_drag', outdir)
      except:
        pass
      #shutil.copy('data.rbcs', outdir)
      try:
          shutil.copy('data.obcs', outdir)
      except:
          pass
      try:
        shutil.copy('data.diagnostics', outdir)
      except:
        pass
      try:
        shutil.copy('data.pkg', outdir+'/data.pkg')
      except:
        pass
      try:
        shutil.copy('data.rbcs', outdir+'/data.rbcs')
      except:
        pass

  _log.info("Done copying files")

  ####### Make the grids #########

  # Make grids:

  ##### Dx ######

  dx = np.zeros(nx) + 100.0
  for i in range(35,-1, -1):
    dx[i] = dx[i+1]*1.03
  print(dx)
  # dx = zeros(nx)+100.
  x=np.cumsum(dx)
  x = x - x[-1] + 20_000

  ##### Dy ######

  dy = np.zeros(ny)+100.0

  # dx = zeros(nx)+100.
  y=np.cumsum(dy)
  y=y-y[0]
  maxy=np.max(y)
  _log.info('YCoffset=%1.4f'%y[0])

  _log.info('dx %f dy %f', dx[0], dy[0])

  # save dx and dy
  with open(indir+"/delX.bin", "wb") as f:
    dx.tofile(f)
  f.close()
  with open(indir+"/delY.bin", "wb") as f:
    dy.tofile(f)
  f.close()
  # some plots
  fig, ax = plt.subplots(2,1)
  ax[0].plot(x/1000.,dx)
  ax[1].plot(y/1000.,dy)
  #xlim([-50,50])
  fig.savefig(outdir+'/figs/dx.pdf')

  ######## Bathy ############
  # get the topo:
  d=np.zeros((ny,nx))
  H = 2000
  d[0, ] = (-np.max(x)+x)*H / 20_000
  d[0, d[0, :]<-H] = -H

  with open(indir+"/topog.bin", "wb") as f:
    d.tofile(f)
  topo=d
  f.close()

  _log.info(np.shape(d))

  fig, ax = plt.subplots(2,1, constrained_layout=True)
  _log.info('%s %s', np.shape(x), np.shape(d))
  for i in range(0, ny, int(np.ceil(ny/20))):
    ax[0].plot(x/1.e3, d[i,:].T)

  #pcm=ax[1].pcolormesh(x/1.e3,y/1.e3,d,rasterized=True,
  #                      shading='auto', vmin=-4000, vmax=-3000)
  #fig.colorbar(pcm,ax=ax[1])
  fig.savefig(outdir+'/figs/topo.png')


  ##################
  # dz:
  # dz is from the surface down (right?).  Its saved as positive.
  dz = np.ones((1,nz))*H/nz

  with open(indir+"/delZ.bin", "wb") as f:
    dz.tofile(f)
  f.close()
  z=np.cumsum(dz)

  ####################
  # temperature profile...
  #
  # temperature goes on the zc grid:
  g=9.8
  alpha = 2e-4
  T0 = 28+np.cumsum(N0**2/g/alpha*(-dz)*np.exp(-z/500) )

  with open(indir+"/TRef.bin", "wb") as f:
    T0.tofile(f)
  f.close()
  #plot
  plt.clf()
  fig, ax = plt.subplots()
  ax.plot(T0, z)
  ax.set_ylim([2000, 0])
  fig.savefig(outdir+'/figs/TO.pdf')

  ###########################
  # velcoity data
  #for j in range(nz):
  #  aa = np.ones((ny,nx)) * U0
  #  with open(indir+"/Uinit.bin", "ab") as f:
  #    aa.tofile(f)


  _log.info('Writing info to README')
  ############ Save to README
  with open('README','r') as f:
    data=f.read()
  with open('README','w') as f:
    import datetime
    import time
    ts = time.time()
    st=datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')
    f.write( st+'\n')
    f.write( outdir+'\n')
    f.write(comments+'\n\n')
    f.write(data)

  _log.info('All Done!')

  _log.info('Archiving to home directory')

  try:
      shutil.rmtree('../archive/'+runname)
  except:
      pass

  shutil.copytree(outdir0+'/input/', '../archive/'+runname+'/input')
  shutil.copytree(outdir0+'/python/', '../archive/'+runname+'/python')
  shutil.copytree(outdir0+'/code', '../archive/'+runname+'/code')

  _log.info('doing this via git!!')

  os.system(f'git commit -a -m "gendata for {runname}: {comments}"')
  os.system('git push origin main')
  os.system(f'git checkout -B {runname}')
  os.system(f'git push origin {runname}')
  os.system('git checkout main')

exit()
