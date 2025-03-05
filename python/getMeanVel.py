

import xarray as xr
import xmitgcm as xm
import os
from dask.diagnostics import ProgressBar
import sys


f0 = 1.4e-4
U0 = 0.1

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
        with xm.open_mdsdataset(data_dir, prefix=['means'], 
                                endian="<", geometry='cartesian',
                                chunks="2D") as ds:
            print(ds)
            w = (ds['VVEL'] * ds['hFacS'] * ds['rAs'] * f0 * U0 ).sum(dim=('YG', 'XC'))
            w.attrs['Processing'] = 'made with getMeanVel.py'

            work = xr.Dataset({'work': w})
            work['AreaS'] = ds['rAs'].sum(dim=('YG', 'XC')).values
            work['meanU'] = (ds['UVEL'] * ds['hFacW'] * ds['rAw']).sum(dim=('YC', 'XG'))
            
            work.to_zarr(f'{out_dir}/workMean.zarr', mode='w')
