

import xarray as xr
import xmitgcm as xm
import os
from dask.diagnostics import ProgressBar
import sys
import matplotlib.pyplot as plt

runname = 'Iso3kmlowU10Amp305f141B059Patch'

print(sys.argv)
if len(sys.argv) > 1:
    runnames = sys.argv[1:]

for runname in runnames:
    data_dir = f'../results/{runname}/input'
    out_dir = f'../reduceddata/{runname}/'

    print(f'processing {data_dir}/{runname}')
    print(f'Writing to {out_dir}')
    try:
        os.mkdir('../reduceddata')
    except:
        pass
    try:
        os.mkdir(out_dir)
    except:
        pass


    if 1:
        iter = -1
        with xm.open_mdsdataset(data_dir, prefix=['spinup2d'], endian="<", 
                                geometry='cartesian', iters=[iter]) as ds:
            #ds = ds.chunk(chunks={'time':1, 'Z':10})
            print(ds)
        fig, ax = plt.subplots()
        ax.imshow(-ds.Depth, vmin=-4000, vmax=-3000)
        fig.savefig(f'../reduceddata/{runname}/Depth{iter}.png')