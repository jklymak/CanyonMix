import xmitgcm as xm
import numpy as np

runname = 'Slope2D094'
with xm.open_mdsdataset(f'../results/{runname}/input/',
                       prefix=['spinup'], geometry='cartesian', endian='<',
                       iters=[1338270], clear_cache=False) as ds0:
    ds0 = ds0.isel(YC=0, YG=0)
    ds0['XC'] = (ds0.XC - ds0.XC[-1])/1e3

    print('XC range:', f"{float(ds0.XC.min().values):.1f} to {float(ds0.XC.max().values):.1f} km")
    print('Depth range:', f"{float(ds0.Depth.min().values):.1f} to {float(ds0.Depth.max().values):.1f} m")
    print()

    depth_diff = np.abs(ds0.Depth - 2000)
    mask = depth_diff < 50

    if mask.any():
        indices = np.where(mask.values)[0]
        print(f'Found {len(indices)} points within 50m of 2000m depth')
        idx_left = indices[0]
        idx_right = indices[-1]

        print(f'Leftmost: X={float(ds0.XC.isel(XC=idx_left).values):.1f}km, depth={float(ds0.Depth.isel(XC=idx_left).values):.1f}m')
        print(f'Rightmost: X={float(ds0.XC.isel(XC=idx_right).values):.1f}km, depth={float(ds0.Depth.isel(XC=idx_right).values):.1f}m')

        left_limit = np.floor(float(ds0.XC.isel(XC=idx_right).values) / 5) * 5
        print(f'\nSuggested xlim: ({left_limit:.0f}, 0)')
