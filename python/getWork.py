import xarray as xr
import xmitgcm as xm
import os
from dask.diagnostics import ProgressBar
import sys


f0 = 1.4e-4
U0 = 0.1

runname = 'Iso3kmlowU10Amp305f141B059MixRoughPatch100'

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

    with xm.open_mdsdataset(data_dir, prefix=['spinup2d'], endian="<", geometry='cartesian') as ds:
        #ds = ds.isel(time=slice(-12, -1))
        print('keys', ds.coords)
        for k in ds.coords:
            if k[:4] in ('hFac', 'mask'):
                ds = ds.drop(k)
        print(ds.time)
        with ProgressBar():
            ds.to_zarr(f'{out_dir}/twod.zarr', mode='w')

    
    if 0:
        with xm.open_mdsdataset(data_dir, prefix=['final'], endian="<", geometry='cartesian') as ds:
            print(ds)
            w = (ds['VVEL'] * ds['hFacS'] * ds['rAs'] * f0 * U0 ).sum(dim=('YG', 'XC'))
            w.attrs['Processing'] = 'made with getWork.py'

            work = xr.Dataset({'work': w})
            work['meanU'] = (ds['UVEL'] * ds['hFacW'] * ds['rAw']).sum(dim=('YC', 'XG'))
            
            work['AreaS'] = ds['rAs'].sum(dim=('YG', 'XC'))
            work['meanU'] = work['meanU'] / work['AreaS'].value
            
            with ProgressBar():
                work.to_zarr(f'{out_dir}/work.zarr', mode='w')

            sl = ds.isel(YC=64, YG=64, time=slice(-4,-1))
            with ProgressBar():
                sl.to_zarr(f'{out_dir}/yslice.zarr', mode='w')
