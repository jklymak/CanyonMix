import xarray as xr
import xmitgcm as xm
import os, sys
from dask.diagnostics import ProgressBar
import pdb

runname = 'Iso3kmlowU10Amp305f141B059RoughPatch100'
print(sys.argv)
if len(sys.argv) > 1:
    runnames = sys.argv[1:]

for runname in runnames:
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

    ds = xm.open_mdsdataset(data_dir, prefix=['spinup'], endian='=',
                            geometry='cartesian', chunks="2D")
    mid = int(ds.sizes['YC'] / 2)
    ds = ds.isel(YC=mid, YG=mid, time=slice(0, None, 5))
    print(ds)
    with ProgressBar():
        ds.to_zarr(f'../reduceddata/{runname}/SliceMid.zarr', mode='w')
