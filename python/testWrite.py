import xarray as xr
import numpy as np

print('Making')
data = xr.DataArray(np.random.randn(400, 480, 1), dims=("x", "y", "time"))
print(data)
data.to_netcdf('Boo.nc')

with xr.open_dataset('Boo.nc', chunks={'x':400, 'y':480}, lock=False) as ds:
    print(ds)
    ds.to_netcdf('Chunked.nc', 'w')
