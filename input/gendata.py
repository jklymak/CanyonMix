import numpy as np

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
# from pylab import *
from shutil import copy
from os import mkdir
import shutil,os,glob
import scipy.signal as scisig
from maketopo import getTopo2D
import logging
from replace_data import replace_data

logging.basicConfig(level=logging.INFO)

_log = logging.getLogger(__name__)


for ndec, useVar_Bot_Drag in zip([0, 200, 200], [False, False, True]):

  amp = 305.
  K0 = 1.8e-4/2./np.pi
  L0 = 1.8e-4/2./np.pi
  runtype = 'low'  # 'full','filt','low'
  setupname=''
  u0 = 20
  N0 = 1e-3
  f0 = 1.410e-4
  geo_beta = 5.9e-12
  # geo_beta = 0
  wall = True
  patch = True

  if wall:
      suff = 'Wall'
  else:
      suff = 'Base'

  if patch:
      suff = f'Patch{ndec*5}'

  if useVar_Bot_Drag and ndec>0:
    suff = 'Sm200'
  elif ndec>0:
    suff = 'SmNoDrag'
  else:
    suff = 'Rough'

  runname='OneHill100%sU%dN%02dAmp%df%03dB%03d%s'%(runtype, u0, N0*1e4, amp, f0*1000000,
                                      geo_beta*1e13, suff)
  comments = 'One 100 km radius hill, rough, but using the same code'

  # to change U we need to edit external_forcing recompile

  outdir0='../results/'+runname+'/'


  ## Params for below as per Nikurashin and Ferrari 2010b
  H = 4000.
  U0 = u0/100.

  # need some info.  This comes from `leewave3d/EmbededRuns.ipynb` on `valdez.seos.uvic.ca`
  # the maxx and maxy are for finer scale runs.
  dx0=100.
  dy0=100.
  maxx = 12 * 120 * 1e3
  maxy =  16 * 76 * 1e3

  # reset f0 in data
  shutil.copy('data', 'dataF')
  replace_data('dataF', 'f0', '%1.3e'%f0)
  replace_data('dataF', 'beta', '%1.3e'%geo_beta)

  replace_data('data.btforcing', 'btforcingU0', '%1.3e'%U0)

  #if useVar_Bot_Drag:
  #  replace_data('data.pkg', 'useVar_Bot_Drag', '.TRUE.')
  #else:
  #  replace_data('data.pkg', 'useVar_Bot_Drag', '.FALSE.')
  # make alway True, which is a bit slow, but allows the
  # bottom boundary conditions to be the same between runs...
  replace_data('data.pkg', 'useVar_Bot_Drag', '.TRUE.')

  # topography parameters:
  useFiltTop=False
  useLowTopo=False
  gentopo=False # generate the topography.
  if runtype=='full':
      gentopo=True
  if runtype=='filt':
      useFiltTop=True
  elif runtype=='low':
      useLowTopo=True


  # model size
  nx = 12 * 120
  ny = 16 * 76
  nz = 400

  _log.info('nx %d ny %d', nx, ny)

  def lininc(n,Dx,dx0):
      a=(Dx-n*dx0)*2./n/(n+1)
      dx = dx0+arange(1.,n+1.,1.)*a
      return dx


  #### Set up the output directory
  backupmodel=1
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

  if 1:
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

  dx = np.zeros(nx)+maxx/nx

  print(len(dx))

  # dx = zeros(nx)+100.
  x=np.cumsum(dx)
  x=x-x[0]
  maxx=np.max(x)
  _log.info('XCoffset=%1.4f'%x[0])

  ##### Dy ######

  dy = np.zeros(ny)+maxy/ny

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
  # we will add a seed just in case we want to redo this exact phase later...
  seed = 20171117
  xtopo, ytopo, h, hband, hlow, k, l, P0, Pband, Plow = getTopo2D(
          dx[0], maxx+dx[0]/2.,
          dy[0],maxy+dy[0],
          mu=3.5, K0=K0, L0=L0,
        amp=amp, kmax=1./300., kmin=1./6000., seed=seed)
  _log.info('shape(hlow): %s', np.shape(hlow))
  _log.info('maxx %f dx[0] %f maxx/dx %f nx %d', maxx, dx[0], maxx/dx[0], nx)
  _log.info('maxxy %f dy[0] %f maxy/dy %f ny %d', maxy, dy[0], maxy/dy[0], ny)

  h = np.real(h - np.min(h))

  hlow = np.real(hlow - np.mean(hlow) + np.mean(h))

  xx = x - np.mean(x)
  yy = y - np.mean(y)
  X, Y = np.meshgrid(xx, yy)
  R = np.sqrt(X**2 + Y**2)
  centerx = 0
  centery = 0
  radius = 100e3
  env = 1
  print(hlow)
  if patch:
    env = X * 0
    env = np.exp(-(R/radius)**6)

    print(R)
    fig, ax = plt.subplots(2,1, constrained_layout=True)
    pcm=ax[1].pcolormesh(x/1.e3,y/1.e3,env,rasterized=True,
                        shading='auto', )
    fig.savefig(outdir+'/figs/env.png')

  if ndec > 1:
    print('convolve!')
    hlow = scisig.convolve2d(hlow, np.ones((ndec, ndec)) / ndec**2,
                            mode='same', boundary='wrap')

  hnew = hlow * env


  # hnew = hlow * 1.0
  if False:
    for i in range(nx):
        for j in range(ny):
            #print(np.floor((i-2)/4) * 4)
            ir = np.mod(i + np.arange(ndec)-ndec/2, nx).astype(int)
            jr = np.mod(j + np.arange(ndec)-ndec/2, ny).astype(int)
            hnew[j, i] = np.mean(hlow[jr,:][:, ir])


  d= hnew  - H

  if wall:
      d[0, :] = 0.0

  with open(indir+"/topog.bin", "wb") as f:
    d.tofile(f)
  topo=d
  f.close()

  _log.info(np.shape(d))

  fig, ax = plt.subplots(2,1, constrained_layout=True)
  _log.info('%s %s', np.shape(x), np.shape(d))
  for i in range(0, ny, int(np.ceil(ny/20))):
    ax[0].plot(x/1.e3, d[i,:].T)

  pcm=ax[1].pcolormesh(x/1.e3,y/1.e3,d,rasterized=True,
                      shading='auto', vmin=-4000, vmax=-3000)
  fig.colorbar(pcm,ax=ax[1])
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
  T0 = 28+np.cumsum(N0**2/g/alpha*(-dz))

  with open(indir+"/TRef.bin", "wb") as f:
    T0.tofile(f)
  f.close()
  #plot
  plt.clf()
  plt.plot(T0,z)
  plt.savefig(outdir+'/figs/TO.pdf')

  ###########################
  # velcoity data
  for j in range(nz):
    aa = np.ones((ny,nx)) * U0
    with open(indir+"/Uinit.bin", "ab") as f:
      aa.tofile(f)


  if False:
    ########################
    # RBCS sponge and forcing
    # In data.rbcs, we have set tauRelaxT=17h = 61200 s
    # here we wil set the first and last 50 km in *y* to relax at this scale and
    # let the rest be free.

    iny = np.where((y<50e3) | (y>maxy-50e3))[0]

    aa = np.zeros((nz,ny,nx))
    for i in iny:
        aa[:,:,i]=1.

    with open(indir+"/spongeweight.bin", "wb") as f:
        aa.tofile(f)

    aa=np.zeros((nz,ny,nx))
    aa+=T0[:,np.newaxis, np.newaxis]
    _log.info(np.shape(aa))

    with open(indir+"/Tforce.bin", "wb") as f:
        aa.tofile(f)

  ################################
  # make drag co-efficients:
  qdrag = 0 * np.ones((ny, nx))
  ldrag = 0 * np.ones((ny, nx))

  hh = amp * np.ones((ny, nx))
  hh = hh * env
  if useVar_Bot_Drag:
    # from AbiHillInterAnalysis/AnalyzeMatrix, linear regression
    ldrag  = hh**1.68 * 2.78e-6
  # otherwise:
  #    drags are zero!
  #qdrag  = hh * np.pi**2 / 2 / 100e3
  #ldrag  = hh**2 * np.pi / 2 / 100e3  # * N0

  #X, Y = np.meshgrid(x, y)
  #R2 = X**2 + Y**2
  #ldrag[R2<10000**2] = 0.005
  fig, ax = plt.subplots(2, 1)
  pc = ax[0].pcolormesh(ldrag, rasterized=True)
  fig.colorbar(pc, ax = ax[0])
  pc = ax[1].pcolormesh(qdrag, rasterized=True)
  fig.colorbar(pc, ax = ax[1])
  fig.savefig(outdir+'/figs/Drags.png')
  with open(indir+"/DraguQuad.bin", "wb") as f:
      qdrag.tofile(f)
  with open(indir+"/DragvQuad.bin", "wb") as f:
      qdrag.tofile(f)
  with open(indir+"/DraguLin.bin", "wb") as f:
      ldrag.tofile(f)
  with open(indir+"/DragvLin.bin", "wb") as f:
      ldrag.tofile(f)

  # make a file that spreads the stress...  Note sum fac*dz = 1

  dragscale = np.zeros((ny, nx)) + amp
  if 0:
    for i in range(nx):
        for j in range(ny):
          if False:
            ind = np.where((-z>=topo[j, i]))[0]
            if len(ind) > 0:
                dragfac[ind, j, i] = np.exp((z[ind] + topo[j, i]) / 300.)
                dsum = np.sum(dragfac[:, j, i] * dz[:])
                dragfac[ind, j, i] =  dragfac[ind, j, i] / dsum
          elif True:
            ind = np.where((-z>=topo[j, i]) & (-z<=topo[j, i]+300))[0]
            if len(ind) > 0:
                dragfac[ind, j, i] = 1.0
                dsum = np.sum(dragfac[:, j, i] * dz[:])
                dragfac[ind, j, i] =  dragfac[ind, j, i] / dsum
          else:
            ind = np.where((-z>=topo[j, i]))[0]
            if len(ind) > 0:
                dragfac[ind[-1], j, i] = 1.0
                dsum = np.sum(dragfac[:, j, i] * dz[:])
                dragfac[ind, j, i] =  dragfac[ind, j, i] / dsum


  with open(indir+"/BotDragVert.bin", "wb") as f:
    dragscale.tofile(f)


  ###### Manually make the directories
  #for aa in range(128):
  #    try:
  #        mkdir(outdir0+'%04d'%aa)
  #    except:
  #        pass

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
