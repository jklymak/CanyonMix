# mamba activate canyonsim: (numpy xarray netcdf4 xmitgcm matplotlib)

import numpy as np

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

# from pylab import *
from shutil import copy
from os import mkdir
import shutil, os, glob
import scipy.signal as scisig
import logging
from replace_data import replace_data

logging.basicConfig(level=logging.INFO)

_log = logging.getLogger(__name__)

# IW slope: dz/dx = \left( \frac{\omega^2 - f^2}{N^2-\omega^2}\right)^{1/2}


if True:

    u0 = 0.6
    f0 = 0.0
    geo_beta = 0.0
    strat_scale = 1e30 # 500  # m
    strat_scale_comp = 500
    N00 = 2e-3
    if strat_scale < 10_000:
        N0 = N00 / np.exp(-1) # so N0 is stratification at strat_scale depth
    else:
        N0 = N00
    _log.info(f'N0: {N0}')
    # strat_scale = 500 # m
    om = 2 * np.pi / 3600 / 12.4
    alpha = 1.25
    dzdxIW = np.sqrt((om**2 - f0**2) / (N00**2 - om**2))
    dhdx = alpha * dzdxIW
    expH = False

    # define the other way:
    #dhdx = 2000 / 50_000
    #alpha = dhdx * N0 / om

    # initialize the tracers 5 tidal periods:
    tracert0 = 12.4*3600*5
    deltaT = 6.2

    if strat_scale > 4000:
        strattype = "const"
    else:
        strattype = "exp"
    if expH:
        seafloor = 'expH'
    else:
        seafloor = ''

    runname = f"WavySlope001{strattype}N{N0*1e5:.0f}u0{u0*1e2:.0f}"
    outdir0 = "../results/" + runname + "/"
    comments = f"alpha = {alpha}. dhdx={dhdx} {strattype} stratification, no shelf etc. u_0={u0}. N_0={N0}.  Three tracers"
    _log.info("runname %s", runname)
    _log.info("dhdx %f", dhdx)

    # reset f0 in data
    shutil.copy("data", "dataF")
    replace_data("dataF", "f0", "%1.3e" % f0)
    replace_data("dataF", "beta", "%1.3e" % geo_beta)
    replace_data("dataF", "deltaT", f"{deltaT}")

    # model size
    nx = 8 * 120
    ny = 1
    nz = 200

    _log.info("nx %d ny %d", nx, ny)

    #### Set up the output directory
    backupmodel = True
    if backupmodel:
        try:
            mkdir(outdir0)
        except:
            import datetime
            import time

            ts = time.time()
            st = datetime.datetime.fromtimestamp(ts).strftime("%Y%m%d%H%M%S")
            shutil.move(outdir0[:-1], outdir0[:-1] + ".bak" + st)
            mkdir(outdir0)

            _log.info(outdir0 + " Exists")

        indir = outdir0 + "/indata/"

        try:
            mkdir(indir)
        except:
            pass

        outdir = outdir0 + "input/"
        try:
            mkdir(outdir)
        except:
            _log.info(outdir + " Exists")
        try:
            mkdir(outdir + "/figs/")
        except:
            pass

        copy("gendata.py", outdir)
        copy("moddata.py", outdir)
    else:
        outdir = outdir + "input/"

    ## Copy some other files
    _log.info("Copying files")

    try:
        shutil.rmtree(outdir + "/../code/")
    except:
        _log.info("code is not there anyhow")
    shutil.copytree("../code", outdir + "/../code/")
    shutil.copytree("../python", outdir + "/../python/")

    try:
        shutil.rmtree(outdir + "/../build/")
    except:
        _log.info("build is not there anyhow")
    _log.info(outdir + "/../build/")
    mkdir(outdir + "/../build/")

    try:
        # copy any data that is in the local indata
        shutil.copytree("../indata/", outdir + "/../indata/")
    except:
        pass

    if True:
        shutil.copy("../build/mitgcmuv", outdir + "/../build/mitgcmuv")
        shutil.copy("../build/Makefile", outdir + "/../build/Makefile")
        shutil.copy("dataF", outdir + "/data")
        shutil.copy("data.ptracers", outdir + "/data.ptracers")
        shutil.copy("data.layers", outdir)
        shutil.copy("eedata", outdir)
        shutil.copy("data.kl10", outdir)
        # shutil.copy('data.btforcing', outdir)
        try:
            shutil.copy("data.kpp", outdir)
        except:
            pass
        try:
            shutil.copy("data.var_bot_drag", outdir)
        except:
            pass
        # shutil.copy('data.rbcs', outdir)
        try:
            shutil.copy("data.obcs", outdir)
        except:
            pass
        try:
            shutil.copy("data.diagnostics", outdir)
        except:
            pass
        try:
            shutil.copy("data.pkg", outdir + "/data.pkg")
        except:
            pass
        try:
            shutil.copy("data.rbcs", outdir + "/data.rbcs")
        except:
            pass

    _log.info("Done copying files")

    ####### Make the grids #########

    # Make grids:

    ##### Dx ######

    dx = np.zeros(nx) + 100.0
    for i in range(35, -1, -1):
        dx[i] = dx[i + 1] * 1.12
    # dx = zeros(nx)+100.
    x = np.cumsum(dx)

    ##### Dy ######

    dy = np.zeros(ny) + 100.0

    # dx = zeros(nx)+100.
    y = np.cumsum(dy)
    y = y - y[0]
    maxy = np.max(y)
    _log.info("YCoffset=%1.4f" % y[0])

    _log.info("dx %f dy %f", dx[0], dy[0])

    # save dx and dy
    with open(indir + "/delX.bin", "wb") as f:
        dx.tofile(f)
    f.close()
    with open(indir + "/delY.bin", "wb") as f:
        dy.tofile(f)
    f.close()
    # some plots
    fig, ax = plt.subplots(2, 1)
    ax[0].plot(x / 1000.0, dx)
    ax[1].plot(y / 1000.0, dy)
    # xlim([-50,50])
    fig.savefig(outdir + "/figs/dx.pdf")

    ######## Bathy ############
    # get the topo:
    d = np.zeros((ny, nx))
    H = 2000
    d[0,] = (-np.max(x) + x) * dhdx
    d[0, d[0,:] < -H] = -H
    #  d[0, d[0, :]<-1700] = -H

    # d[0, d[0, :]>-50] = -50
    d[0, -1] = 0

    if expH:
        for i in range(nx-2, -1, -1):
            d[0, i] = d[0, i+1] - dx[i] * dhdx  * np.exp(1 + d[0, i+1] / 500)
    d[0, d[0,:] < -H] = -H

    # wavy:
    d[0, :] = -H
    i = len(x) - 1
    d[0, i] = 0
    while d[0, i] > -200:
        i = i - 1
        d[0, i] = d[0, i+1] - dx[i-1] * 200 / 15_000  # 5 km wide shelf
    while d[0, i] > -700:
        i = i - 1
        d[0, i] = d[0, i+1] - dx[i-1] * om / N0 * 1.5
    while d[0, i] > -1000:
        i = i - 1
        d[0, i] = d[0, i+1] - dx[i-1] * om / N0 * 0.5
    while d[0, i] > -1500:
        i = i - 1
        d[0, i] = d[0, i+1] - dx[i-1] * om / N0 * 1.5
    while d[0, i] > -1800:
        i = i - 1
        d[0, i] = d[0, i+1] - dx[i-1] * om / N0 * 0.5
    while d[0, i] > -2000:
        i = i - 1
        d[0, i] = d[0, i+1] - dx[i-1] * om / N0 * 1.5
    d[0, d[0,:] < -H] = -H
    d[0, :] = np.convolve(d[0, :], np.ones(20) / 20, mode="same")
    d[0, d[0,:] < -H] = -H
    d[0, :20] = -H
    d[0, -1] = 0.0


    with open(indir + "/topog.bin", "wb") as f:
        d.tofile(f)
    topo = d
    f.close()

    _log.info(np.shape(d))

    fig, ax = plt.subplots(2, 1, constrained_layout=True)
    _log.info("%s %s", np.shape(x), np.shape(d))
    for i in range(0, ny, int(np.ceil(ny / 20))):
        ax[0].plot(x / 1.0e3, d[i, :].T)
    fig.savefig(outdir + "/figs/topo.pdf")



    ##################
    # dz:
    # dz is from the surface down (right?).  Its saved as positive.
    dz = np.ones((1, nz)) * H / nz

    with open(indir + "/delZ.bin", "wb") as f:
        dz.tofile(f)
    f.close()
    z = np.cumsum(dz)

    ####################
    # temperature profile...
    #
    # temperature goes on the zc grid:
    g = 9.8
    alpha = 2e-4
    T0 = 28 + np.cumsum(N0**2 / g / alpha * (-dz) * np.exp((-z) / strat_scale))
    # surface mixed layer:
    # T0[0:10] = T0[10]

    with open(indir + "/TRef.bin", "wb") as f:
        T0.tofile(f)
    f.close()
    # plot
    plt.clf()
    fig, ax = plt.subplots()
    ax.plot(T0, z)
    ax.set_ylim([2000, 0])
    fig.savefig(outdir + "/figs/TO.pdf")

    # get layers for data.layers....
    nlayers = 100
    layerbounds = np.linspace(T0.min(), T0.max(), nlayers + 1)
    layersst = "&LAYERS_PARM01\n"
    layersst += "# temperature bins!\n"
    layersst += " layers_name(1) ='TH',\n"
    layersst += "# there need to be one more of these than the number of layers\n"
    layersst += f" layers_bounds(1:{nlayers+1},1)= "
    for i in range(0, nlayers + 1):
        layersst += f"{layerbounds[i]:.2f}, "
        if i % 4 == 3:
            layersst += "\n "
    layersst += "\n/"

    with open(outdir + "/data.layers", "w") as f:
        f.write(layersst)

    time = np.arange(0, 1240 * 36, 1240)

    uw = u0 * np.sin(om * time)
    uwn = np.zeros((np.shape(time)[0], nz, ny))
    for j in range(0, ny):
        for i in range(0, nz):
            uwn[:, i, j] = uw
    with open(indir + "/Uw.bin", "wb") as f:
        uwn.tofile(f)
#    for j in range(0, ny):
#        for i in range(0, nz):
#            uwn[:, i, j] = uw
#    with open(indir + "/Ue.bin", "wb") as f:
#        uwn.tofile(f)

    t = np.zeros((np.shape(time)[0], nz, ny))
    for j in range(0, ny):
        for i in range(0, nz):
            for k in range(0, np.shape(time)[0]):
                t[k, i, j] = T0[i]

    with open(indir + "/Tw.bin", "wb") as f:
        t.tofile(f)
#    with open(indir + "/Te.bin", "wb") as f:
#        t.tofile(f)

    fig, ax = plt.subplots()
    ax.plot(time, uwn[:, 0, 0])
    fig.savefig(outdir + "/figs/uwn.pdf")

    T = np.zeros((nz, ny, nx)) + T0[:, np.newaxis, np.newaxis]

    with open(indir + "/Tinit.bin", "wb") as f:
        T.tofile(f)
    T = np.zeros((nz, ny, nx))
    with open(indir + "/Uinit.bin", "wb") as f:
        T.tofile(f)
    T = T + 35
    with open(indir + "/Sinit.bin", "wb") as f:
        T.tofile(f)

    T = np.zeros((ny, nx))
    with open(indir + "/Etainit.bin", "wb") as f:
        T.tofile(f)

    # make the tracer files:
    # Put a tracer blob at -500, -1000, an -1800 m.



    for depth, name in zip([-450, -850, -1250, -1650], ['TRAC01', 'TRAC02', 'TRAC03', 'TRAC04']):
        S = np.zeros((nz, ny, nx)) + 1e-10
        indi = int(np.round(np.interp(depth, d[0, :], np.arange(len(d[0, :])))))
        indk = np.where(-z> depth)[0][-1]
        for i in range(-2, 3):
            indk = np.where(-z > d[0, indi+i])[0][-1]
            for j in range(-3, 1):
                S[indk+j, 0, indi+i] = 400.0

        with open(indir + f"/{name}.bin", "wb") as f:
            S.tofile(f)

        fig, ax = plt.subplots()
        ax.pcolormesh(S[:, 0, :], rasterized=True)
        fig.savefig(outdir + f"/figs/Trac{name}.png", dpi=200)

    # replace_data(outdir + "/data.ptracers", "PTRACERS_Iter0", f"{int(tracert0/deltaT)}")

    _log.info("Writing info to README")
    ############ Save to README
    with open("README", "r") as f:
        data = f.read()
    with open("README", "w") as f:
        import datetime
        import time

        ts = time.time()
        st = datetime.datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")
        f.write(st + "\n")
        f.write(outdir + "\n")
        f.write(comments + "\n\n")
        f.write(data)

    _log.info("All Done!")

    _log.info("Archiving to home directory")

    try:
        shutil.rmtree("../archive/" + runname)
    except:
        pass

    shutil.copytree(outdir0 + "/input/", "../archive/" + runname + "/input")
    shutil.copytree(outdir0 + "/python/", "../archive/" + runname + "/python")
    shutil.copytree(outdir0 + "/code", "../archive/" + runname + "/code")

    _log.info("doing this via git!!")

    os.system(f'git commit -a -m "gendata for {runname}: {comments}"')
    os.system("git push origin main")
    os.system(f"git checkout -B {runname}")
    os.system(f"git push origin {runname}")
    os.system("git checkout main")

exit()
