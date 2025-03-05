import xarray as xr
import xmitgcm as xm
import os
from dask.diagnostics import ProgressBar
import pdb

runname = 'Iso3kmlowU10Amp305f141B059AllRough'
data_dir = f'../results/{runname}/input'
out_dir = f'../reduceddata/{runname}/'
try:
    os.mkdir('../reduceddata')
except:
    pass
try:
    os.mkdir(out_dir)
except:
    pass

if True:
    ds = xm.open_mdsdataset(data_dir, prefix=['spinup'], endian='=',
                        geometry='cartesian')
    print(ds)
    mid = int(ds.sizes['YC'] / 2)
    ds = ds.isel(YC=mid, YG=mid)
    print(ds)
    with ProgressBar():
        #ds.to_netcdf(f'../reduceddata/{runname}/SliceMid.nc', engine='netcdf4')
        ds.to_zarr(f'../reduceddata/{runname}/SliceMid.zar', mode='w')
