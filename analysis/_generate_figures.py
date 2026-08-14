#!/usr/bin/env python
"""
Generate figures for CanyonMix analysis

Usage:
    python generate_figures.py --runname Slope2D093 --mooringX -55 -45 -35
    python generate_figures.py --runname Slope2D091 --mooringX -36 -31 -24
    python generate_figures.py --runname Slope2D091 --mooringZ -1750 -1250 -750
"""
import argparse
import xmitgcm as xm
import xarray as xr
import numpy as np
import matplotlib
# matplotlib.use('Agg')  # Use non-interactive backend for script execution
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import matplotlib.ticker as mticker
import traceback
import xhistogram.xarray as xhist
import mpl_direct_layout



try:
    import jmkfigure
    HAS_JMKFIGURE = True
except Exception as e:
    HAS_JMKFIGURE = False
    print(f"Warning: jmkfigure not available ({e.__class__.__name__}), using standard matplotlib save")

import os
from pathlib import Path
import glob


def get_available_iterations(runname, prefix='spinup'):
    """Get available iteration numbers for a given run and prefix"""
    pattern = f'../results/{runname}/input/{prefix}.*.meta'
    files = sorted(glob.glob(pattern))
    if not files:
        raise FileNotFoundError(f"No {prefix} files found for {runname}")

    iters = [int(f.split('.')[-2]) for f in files]
    return np.array(iters)


def select_iterations_from_end(iters, time_window_hours=12.4, interval_seconds=930,
                                n_snapshots=None, snapshot_spacing=None):
    """
    Select iterations from the last time_window_hours of available data.

    Parameters:
    -----------
    iters : array
        Available iteration numbers
    time_window_hours : float
        Time window from end in hours (default: 12.4 = one tidal period)
    interval_seconds : int
        Time interval between iterations in seconds (default: 930)
    n_snapshots : int, optional
        If provided, return evenly spaced snapshots within window
    snapshot_spacing : int, optional
        If provided, spacing between snapshots in number of iterations

    Returns:
    --------
    selected_iters : array
        Selected iteration numbers
    """
    print('n_snapshots: ', n_snapshots)
    interval_seconds = np.median(np.diff(iters))
    print('Interval: ', interval_seconds)
    if len(iters) == 0:
        raise ValueError("No iterations available")

    # Calculate how many iterations correspond to the time window
    time_window_seconds = time_window_hours * 3600
    n_iters_in_window = int(time_window_seconds / interval_seconds)
    print(n_iters_in_window, ' iterations in window')
    # Select from the end
    if n_snapshots is not None:
        # For snapshots: evenly spaced within the window
        if snapshot_spacing is None:
            # Auto-calculate spacing
            snapshot_spacing = max(1, int(float(n_iters_in_window) / n_snapshots))
        print('Spacing: ', snapshot_spacing)
        start_idx = max(0, len(iters) - n_iters_in_window)
        end_idx = len(iters)
        selected_iters = iters[start_idx:end_idx:snapshot_spacing]
        # Make sure we get exactly n_snapshots
        if len(selected_iters) > n_snapshots:
            selected_iters = selected_iters[-n_snapshots:]
    else:
        # For time series: all iterations in window
        start_idx = max(0, len(iters) - n_iters_in_window)
        selected_iters = iters[start_idx:]

    return selected_iters


def preprocess_run(ds):
    """Preprocess run data"""
    ds = ds.isel(YC=0, YG=0)
    ds['XG'] = (ds.XG - ds.XC[-1])/1e3
    ds['XC'] = (ds.XC - ds.XC[-1])/1e3
    return ds


def contour_theta(ds, timeidx=0, ax=None, thetalevels=None, thetalevelsmaj=None,
                  thetalevelspecial=None):
    """Add temperature contours to axis"""
    if thetalevels is None:
        thetalevels = np.arange(20, 28, 0.2)
        thetalevelsmaj = np.arange(20, 28, 1)
        thetalevelspecial = np.array([25.6])
        thetalevels = thetalevels[~np.isin(thetalevels, thetalevelsmaj)]

    if timeidx is None:
        Theta = ds.THETA
    else:
        Theta = ds.THETA.isel(time=timeidx)
    cs = ax.contour(ds.XC, ds.Z, Theta, colors='0.6', levels=thetalevels, linewidths=0.5)
    ax.contour(ds.XC, ds.Z, Theta, colors='0.4', levels=thetalevelsmaj, linewidths=1)
    ax.contour(ds.XC, ds.Z, Theta, colors='m', levels=thetalevelspecial, linewidths=1.5)
    return cs


def get_xlimits_from_depth(ds, target_depth=2000, right_limit=0, offshore_buffer=10):
    """
    Determine appropriate x-axis limits based on bathymetry

    Parameters:
    -----------
    ds : xarray Dataset
        Dataset containing Depth variable
    target_depth : float
        Target depth for left limit (default: 2000m)
    right_limit : float
        Right x-axis limit (default: 0, the coast)
    offshore_buffer : float
        Additional distance offshore from target depth contour in km (default: 10)

    Returns:
    --------
    xlim : tuple
        (left_limit, right_limit) for plotting
    """
    try:
        # Find where depth is close to target_depth, searching from the shallow end
        # to find the slope location, not the deep water boundary
        depth_diff = np.abs(ds.Depth - target_depth)

        # Find all locations where depth is within 50m of target
        mask = depth_diff < 50
        if mask.any():
            # Get the rightmost location (closest to shore) where depth ~ target_depth
            indices = np.where(mask.values)[0]
            idx = indices[-1]  # Rightmost index where depth ~ 2000m (on the slope)
        else:
            # Fallback: just use the closest match
            idx = depth_diff.argmin().values.item()

        slope_location = float(ds.XC.isel(XC=idx).values)
        # Add buffer distance offshore (negative direction)
        left_limit = slope_location - offshore_buffer
        # Round to nearest 5 km for cleaner limits
        left_limit = np.floor(left_limit / 5) * 5

        print(f"  Found depth {float(ds.Depth.isel(XC=idx).values):.1f}m at X={slope_location:.1f}km, using left limit={left_limit:.0f}km")
        return (left_limit, right_limit)
    except Exception as e:
        print(f"  Warning: Could not determine xlimits from depth, using defaults: {e}")
        return (-50, right_limit)


def plot_virt_moorings(ax, ds, mooringX):
    """Plot virtual mooring locations"""
    for nn in range(len(mooringX)):
        depth = ds.Depth.sel(XC=mooringX[nn], method='nearest').values
        ax.plot([mooringX[nn], mooringX[nn]], [-depth, 0], '--', lw=1, color='gray')


def get_mooringX_from_mooringZ(ds, mooringZ):
    """Map requested mooring depths to x-locations using bathymetry."""
    depth = np.asarray(-ds.Depth.values)
    xcoord = np.asarray(ds.XC.values)

    valid = np.isfinite(depth) & np.isfinite(xcoord)
    depth = depth[valid]
    xcoord = xcoord[valid]

    order = np.argsort(depth)
    depth = depth[order]
    xcoord = xcoord[order]

    return np.interp(mooringZ, depth, xcoord)


def save_figure(fig, filename, dpi=300, kinds=['png', 'pdf']):
    """Save figure using jmkfigure if available, otherwise matplotlib"""
    outdir = Path('doc')
    outdir.mkdir(exist_ok=True)

    if HAS_JMKFIGURE:
        jmkfigure.jmkprint(filename, './generate_figures.py', dpi=dpi, kinds=kinds)
    else:
        for kind in kinds:
            outfile = outdir / f'{filename}.{kind}'
            fig.savefig(outfile, dpi=dpi, bbox_inches='tight')
            print(f"Saved: {outfile}")


def generate_eulerian_snapshots(runname, mooringX, cmapU, cmapKL, lognorm,
                                thetalevels, thetalevelsmaj, thetalevelspecial, xlim=None):
    """Generate Eulerian snapshot figures"""
    print("Generating Eulerian snapshots...")

    # Get available iterations and select 4 snapshots from last 12.4 hours
    available_iters = get_available_iterations(runname, 'spinup')
    iters = select_iterations_from_end(available_iters, time_window_hours=12.4,
                                       n_snapshots=4)
    print(f"  Selected snapshot iterations: {iters}")

    # Dissipation files use same iterations
    itersD = iters

    with (xm.open_mdsdataset(f'../results/{runname}/input/',
                               prefix=['dissipation'], geometry='cartesian', endian='<',
                               iters=list(itersD), clear_cache=False
                               ) as dsdiss0,
          xm.open_mdsdataset(f'../results/{runname}/input/',
                               prefix=['spinup'], geometry='cartesian', endian='<',
                               iters=list(iters), clear_cache=False
                               ) as ds0):
        ds0 = preprocess_run(ds0)
        ds0['UVEL'] = ds0['UVEL'].where(ds0['THETA'].values > 0).rolling(XG=5).mean().rolling(Z=3).mean()
        ds0['THETA'] = ds0['THETA'].where(ds0['THETA'].values > 0).rolling(XC=5).mean().rolling(Z=3).mean()
        dsdiss0 = preprocess_run(dsdiss0)

        # Determine appropriate xlimits from bathymetry
        if xlim is None:
            xlim = get_xlimits_from_depth(ds0, target_depth=2000, right_limit=0)
        print(f"  Using xlim: {xlim}")

        fig, axs = plt.subplots(4, 2, layout='direct', figsize=(10, 8), sharex=True, sharey=True)

        for nn in range(4):
            axu = axs[nn, 0]
            axd = axs[nn, 1]
            pcmu = axu.pcolormesh(ds0.XC, ds0.Z, ds0.UVEL.isel(time=nn), cmap=cmapU,
                                 shading='nearest', vmin=-0.6, vmax=0.6, rasterized=True)
            contour_theta(ds0, timeidx=nn, ax=axu, thetalevels=thetalevels,
                         thetalevelsmaj=thetalevelsmaj, thetalevelspecial=thetalevelspecial)

            pcmd = axd.pcolormesh(dsdiss0.XC, dsdiss0.Z,
                                 dsdiss0.KLeps.isel(time=nn).rolling(XC=3).mean().rolling(Zl=3).mean(),
                                 cmap=cmapKL, shading='nearest', rasterized=True, norm=lognorm)
            contour_theta(ds0, timeidx=nn, ax=axd, thetalevels=thetalevels,
                         thetalevelsmaj=thetalevelsmaj, thetalevelspecial=thetalevelspecial)

            axd.set_xlim(xlim)
            axd.set_facecolor('lightgray')
            axu.set_facecolor('lightgray')

            for nax, ax in enumerate([axu, axd]):
                let = chr(ord('a') + nn + nax*4)
                ax.text(-2, -800, f'{let}) {float(ds0.time.isel(time=nn).values)/3600/12.4/1e9:.2f} T',
                       color='k', ha='right')
                plot_virt_moorings(ax, ds0, mooringX)

            if nn == 0:
                axcb = axu.inset_axes([0.75, 0.32, 0.22, 0.04], transform=axu.transAxes)
                fig.colorbar(pcmu, cax=axcb, label=r'$U\ \mathrm{(m/s)}$',
                           orientation='horizontal', extend='both')
                axcb = axd.inset_axes([0.75, 0.32, 0.22, 0.04], transform=axd.transAxes)
                fig.colorbar(pcmd, cax=axcb, label=r'$\epsilon\ \mathrm{(m^2/s^3)}$',
                           orientation='horizontal', extend='both')
                axu.set_ylabel(r'Depth (m)')
            if nn==3:
                axd.set_xlabel(r'X (km)')

        save_figure(fig, f'{runname}_U_eps_snap')
        plt.close(fig)


def generate_eulerian_means(runname, mooringX, cmapU, cmapKL, lognorm,
                           thetalevels, thetalevelsmaj, thetalevelspecial, xlim=None, run_comment=None):
    """Generate Eulerian mean figures"""
    print("Generating Eulerian means...")

    with xm.open_mdsdataset(f'../results/{runname}/input/',
                                prefix=['tideave'],
                                geometry='cartesian', endian='<',
                                iters='all'
                                ) as ds0:
        ds0['XG'] = (ds0['XG'] - ds0.XC[-1]) / 1000
        ds0['XC'] = (ds0['XC'] - ds0.XC[-1]) / 1000
        ds = ds0.isel(YC=0, YG=0, time=slice(-6, -3)).mean(dim='time')

        ds['UVEL'] = ds['UVEL'].where(ds['THETA'].values > 0).rolling(XG=5).mean().rolling(Z=3).mean()
        ds['KLeps'] = ds['KLeps'].where(ds['THETA'].values > 0).rolling(XC=3).mean().rolling(Zl=3).mean()
        ds['THETA'] = ds['THETA'].where(ds['THETA'].values > 0).rolling(XC=5).mean().rolling(Z=3).mean()

        # Determine appropriate xlimits from bathymetry
        if xlim is None:
            xlim = get_xlimits_from_depth(ds, target_depth=2000, right_limit=0)
        print(f"  Using xlim: {xlim}")

        fig, axs = plt.subplots(1, 2, layout='direct', figsize=(10, 2.6),
                               sharey=True, sharex=True)
        axu = axs[0]
        axu.set_title(run_comment, fontsize='medium', loc='left')
        axd = axs[1]

        pcmu = axu.pcolormesh(ds.XC, ds.Z, ds.UVEL, cmap=cmapU,
                              shading='nearest', vmin=-0.2, vmax=0.2, rasterized=True)
        contour_theta(ds, timeidx=None, ax=axu, thetalevels=thetalevels,
                     thetalevelsmaj=thetalevelsmaj, thetalevelspecial=thetalevelspecial)

        pcmd = axd.pcolormesh(ds.XC, ds.Z, ds.KLeps, cmap=cmapKL,
                              shading='nearest', rasterized=True, norm=lognorm)
        contour_theta(ds, timeidx=None, ax=axd, thetalevels=thetalevels,
                     thetalevelsmaj=thetalevelsmaj, thetalevelspecial=thetalevelspecial)

        axd.set_xlim(xlim)
        axd.set_facecolor('lightgray')
        axu.set_facecolor('lightgray')

        axcb = axu.inset_axes([0.7, 0.32, 0.25, 0.04], transform=axu.transAxes)
        fig.colorbar(pcmu, cax=axcb, label=r'$\left<U\right>\ \mathrm{(m/s)}$',
                   orientation='horizontal', extend='both')
        axcb = axd.inset_axes([0.7, 0.32, 0.25, 0.04], transform=axd.transAxes)
        fig.colorbar(pcmd, cax=axcb, label=r'$\left<\epsilon\right>\ \mathrm{(m^2/s^3)}$',
                   orientation='horizontal', extend='both')

        axu.set_ylabel(r'Depth (m)')
        axd.set_xlabel(r'X (km)')
        axu.text(-2, -800, f'a) Last 5 tides', color='k', ha='right')
        axd.text(-2, -800, f'b) Last 5 tides', color='k', ha='right')

        plot_virt_moorings(axu, ds, mooringX)
        plot_virt_moorings(axd, ds, mooringX)

        save_figure(fig, f'{runname}_U_eps_eulerianave')
        plt.close(fig)


def generate_eulerian_means_justflowzoom(runname, mooringX, cmapU,
                           thetalevels, thetalevelsmaj, thetalevelspecial, xlim=None,
                           xlimzoom=None,
                           run_comment=None,
                           ylimzoom=[-2000, 0],
                           xmooring=None,
                           Umin=-0.2, Umax=0.2, smooth=True):
    """Generate Eulerian mean figures"""
    print("Generating Eulerian means...")

    with xm.open_mdsdataset(f'../results/{runname}/input/',
                                prefix=['tideave'],
                                geometry='cartesian', endian='<',
                                iters='all'
                                ) as ds0:
        ds0['XG'] = (ds0['XG'] - ds0.XC[-1]) / 1000
        ds0['XC'] = (ds0['XC'] - ds0.XC[-1]) / 1000
        ds = ds0.isel(YC=0, YG=0, time=slice(4, 8)).mean(dim='time')

        if smooth:
            ds['UVEL'] = ds['UVEL'].where(ds['THETA'].values > 0).rolling(XG=5).mean().rolling(Z=3).mean()
            ds['THETA'] = ds['THETA'].where(ds['THETA'].values > 0).rolling(XC=5).mean().rolling(Z=3).mean()
        else:
            ds['UVEL'] = ds['UVEL'].where(ds['THETA'].values > 0)
            ds['THETA'] = ds['THETA'].where(ds['THETA'].values > 0)

        # Determine appropriate xlimits from bathymetry
        if xlim is None:
            xlim = get_xlimits_from_depth(ds, target_depth=2000, right_limit=0)
        print(f"  Using xlim: {xlim}")

        fig, axs = plt.subplots(1, 3, layout='direct', figsize=(10, 2.6),
                               sharey=False, sharex=False, width_ratios=[1, 1, 0.4])
        axu = axs[0]
        axu.set_title(run_comment, fontsize='medium', loc='left')
        axz = axs[1]
        axp = axs[2]

        for ax in [axu, axz]:
            pcmu = ax.pcolormesh(ds.XC, ds.Z, ds.UVEL, cmap=cmapU,
                              shading='nearest', vmin=Umin, vmax=Umax, rasterized=True)
            contour_theta(ds, timeidx=None, ax=ax, thetalevels=thetalevels,
                     thetalevelsmaj=thetalevelsmaj, thetalevelspecial=thetalevelspecial)

            ax.set_xlim(xlim)
            ax.set_facecolor('lightgray')

            if ax == axu:
                axcb = ax.inset_axes([0.55, 0.25, 0.4, 0.04], transform=ax.transAxes)
                cbar = fig.colorbar(pcmu, cax=axcb, label=r'$\left<U\right>\ \mathrm{(m/s)}$',
                    orientation='horizontal', extend='both')
                cbar.ax.xaxis.set_tick_params(labelsize='small')
            if ax == axz:
                ax.set_xlim(xlimzoom)
                ax.set_ylim(ylimzoom)
                # draw a box around the zoomed region in the second plot:
            else:
                rect = matplotlib.patches.Rectangle((xlimzoom[0], ylimzoom[0]),
                                                    xlimzoom[1]-xlimzoom[0],
                                                    ylimzoom[1]-ylimzoom[0],
                                                    linewidth=1, edgecolor='m', facecolor='none',
                                                    transform=ax.transData, zorder=5)
                print(rect)
                ax.add_patch(rect)
                ax.set_xlim(xlim)
                ax.set_ylim([-2000, 0])
                ax.set_ylabel(r'Depth (m)')

        ax = axs[2]
        if xmooring is None:
            xmid = (xlimzoom[1] - xlimzoom[0]) / 2 + xlimzoom[0]
        else:
            xmid = xmooring
        ax.plot(ds.UVEL.sel(XG=xmid, method='nearest'), ds.Z, color='k')
        ax.set_xlim([Umin, Umax])
        ax.set_yticklabels([])
        ax.grid('on')
        ax.set_ylim([ylimzoom[0], ylimzoom[1]])
        ax.set_xlabel(r'$\left<U\right>\ \mathrm{(m/s)}$')
        axz.set_xlabel(r'X (km)')

        save_figure(fig, f'{runname}_U_eps_eulerianave_justflowzoom')
        return fig, axs


def generate_timeseries_moorings(runname, mooringX, cmapU, cmapKL, lognorm,
                                 thetalevels, thetalevelsmaj, thetalevelspecial):
    """Generate time series at virtual moorings"""
    print("Generating time series at moorings...")

    # Get all iterations from last 12.4 hours
    available_iters = get_available_iterations(runname, 'spinup')
    iters = select_iterations_from_end(available_iters, time_window_hours=12.4*2.5)
    print(f"  Using {len(iters)} iterations from last 31 hours")

    # Dissipation files use same iterations
    itersD = iters

    with (xm.open_mdsdataset(f'../results/{runname}/input/',
                               prefix=['dissipation'], geometry='cartesian', endian='<',
                               iters=list(itersD), clear_cache=False
                               ) as dsdiss0,
          xm.open_mdsdataset(f'../results/{runname}/input/',
                               prefix=['spinup'], geometry='cartesian', endian='<',
                               iters=list(iters), clear_cache=False
                               ) as ds0):
        ds0 = preprocess_run(ds0)
        dsdiss0 = preprocess_run(dsdiss0)

        width_ratios = [r for _ in range(len(mooringX)) for r in (1, 0.5)]
        fig, axs = plt.subplots(3, len(mooringX)*2, layout='direct', figsize=(12, 7),
                   sharey='row', subplot_kw={'facecolor':'lightgray'},
                   gridspec_kw={'width_ratios': width_ratios,
                        'height_ratios': [1, 1, 0.3]})

        for nn in range(len(mooringX)):
            ds = ds0.sel(XC=mooringX[nn], XG=mooringX[nn], method='nearest')
            ds['UVEL'] = ds.UVEL.where(ds.THETA.values > 0)
            ds['THETA'] = ds.THETA.where(ds.THETA.values > 0)
            ds['tides'] = np.float64(ds.time) / 3600 / 12.4 / 1e9

            dsdiss = dsdiss0.sel(XC=mooringX[nn], XG=mooringX[nn], method='nearest')
            dsdiss['tides'] = np.float64(dsdiss.time) / 3600 / 12.4 / 1e9

            axu = axs[0, nn*2]
            axum = axs[0, nn*2+1]
            axd = axs[1, nn*2]
            axdm = axs[1, nn*2+1]
            axint = axs[2, nn*2]
            axintm = axs[2, nn*2+1]

            pcmu = axu.pcolormesh(ds.tides, ds.Z, ds.UVEL.T, rasterized=True,
                                 shading='nearest', cmap=cmapU, vmin=-0.6, vmax=0.6)
            axu.contour(ds.tides, ds.Z, ds.THETA.T, colors='k', levels=thetalevels, linewidths=0.5)
            axu.contour(ds.tides, ds.Z, ds.THETA.T, colors='k', levels=thetalevelsmaj, linewidths=1)
            axu.contour(ds.tides, ds.Z, ds.THETA.T, colors='m', levels=thetalevelspecial, linewidths=1.5)
            axu.set_title(f'X = {mooringX[nn]:1.1f} km')

            if nn == 2:
                cax = axu.inset_axes([0.6, 0.32, 0.35, 0.04], transform=axu.transAxes)
                fig.colorbar(pcmu, cax=cax, label=r'$U\ \mathrm{(m/s)}$',
                           orientation='horizontal', extend='both')
            axu.set_title(f'{chr(ord("a")+nn)})', loc='left', fontsize='medium')
            axum.plot(ds.UVEL.isel(time=slice(-24*2, None)).mean(dim='time'), ds.Z)
            axum.set_xlim([-0.29999, 0.29999])
            axum.grid('on')
            axum.set_xticks(np.arange(-0.2, 0.21, 0.2))
            axum.set_facecolor('white')

            pcmd = axd.pcolormesh(dsdiss.tides, dsdiss.Z, dsdiss.KLeps.T, rasterized=True,
                                 shading='nearest', cmap=cmapKL, norm=lognorm)
            axd.contour(ds.tides, ds.Z, ds.THETA.T, colors='k', levels=thetalevels, linewidths=0.5)
            axd.contour(ds.tides, ds.Z, ds.THETA.T, colors='k', levels=thetalevelsmaj, linewidths=1)
            axd.contour(ds.tides, ds.Z, ds.THETA.T, colors='m', levels=thetalevelspecial, linewidths=1.5)

            # Vertically integrated turbulence time series at this mooring.
            zdim = 'Zl' if 'Zl' in dsdiss.KLeps.dims else 'Z'
            # Previous integrated version (kept for easy restore):
            # zcoord = dsdiss[zdim]
            # dz = np.abs(zcoord.diff(zdim).mean())
            # eps_int = (dsdiss.KLeps.where(dsdiss.KLeps > 0, 0.0) * dz).sum(dim=zdim) * 1000.0
            eps_int = dsdiss.KLeps.where(dsdiss.KLeps > 0).mean(dim=zdim, skipna=True)
            eps_int = eps_int.where(np.isfinite(eps_int))
            axint.semilogy(dsdiss.tides, eps_int, color='k', lw=1.25)

            # Bottom-200 m velocity mean on a twin axis, filled about zero.
            z_bottom = -float(ds.Depth.values)
            ubot200 = ds.UVEL.where(ds.THETA.values > 0).where(ds.Z <= (z_bottom + 200.0)).mean(dim='Z')
            ubot200 = ubot200.where(np.isfinite(ubot200), 0.0)
            axint_u = axint.twinx()
            axint_u.fill_between(ds.tides.values, 0.0, ubot200.values,
                                 where=(ubot200.values >= 0.0),
                                 color='#f6caca', alpha=0.9, linewidth=0)
            axint_u.fill_between(ds.tides.values, 0.0, ubot200.values,
                                 where=(ubot200.values < 0.0),
                                 color='#cfe2f3', alpha=0.9, linewidth=0)
            axint_u.plot(ds.tides, ubot200, color='#5f7ea8', lw=0.9)
            axint_u.axhline(0.0, color='#5f7ea8', ls='--', lw=1.0)
            axint_u.set_zorder(axint.get_zorder() - 1)
            axint_u.patch.set_visible(False)
            axint.set_zorder(axint_u.get_zorder() + 1)
            axint.patch.set_visible(False)
            axint_u.set_ylim([-0.5, 0.5])
            axint_u.tick_params(axis='y', colors='#5f7ea8', labelright=False)
            axint.set_title(f'{chr(ord("a")+nn+6)})', loc='left', fontsize='medium')
            axint.grid('on')
            axint.set_facecolor('white')
            axintm.axis('off')

            tide_min = float(dsdiss.tides.min())
            tide_max = float(dsdiss.tides.max())
            for axt in [axu, axint, axd]:
                axt.set_xlim([tide_min, tide_max])
                axt.xaxis.set_major_locator(mticker.MaxNLocator(nbins=6, min_n_ticks=4))
                #axt.xaxis.set_minor_locator(mticker.AutoMinorLocator())

            axd.set_title(f'{chr(ord("a")+nn+3)})', loc='left', fontsize='medium')
            if nn == 2:
                cax = axd.inset_axes([0.6, 0.32, 0.35, 0.04], transform=axd.transAxes)
                fig.colorbar(pcmd, cax=cax, label=r'$\epsilon\ \mathrm{(m^2/s^3)}$',
                           orientation='horizontal', extend='both')
                axint.set_xlabel(r'Time [tidal cycles]')
            if nn == 0:
                axu.set_ylabel(r'Depth (m)')
                axd.set_ylabel(r'Depth (m)')
                axint.set_ylabel(r'$\left<\epsilon\right>_z\ \mathrm{(m^2/s^3)}$')
                axdm.set_xlabel(r'$\left<\epsilon\right>\ \mathrm{(m^2/s^3)}$')
                axum.set_xlabel(r'$\left<U\right>\ \mathrm{(m/s)}$')

            axdm.semilogx(dsdiss.KLeps.isel(time=slice(-48, None)).mean(dim='time'), dsdiss.Z)
            axdm.set_xlim([.099e-11, 1e-5])
            axdm.grid('on')
            axdm.set_facecolor('white')

        save_figure(fig, f'{runname}_U_eps_timeseries_moorings')
        plt.close(fig)


def get_layered_histogram_path(runname):
    """Get the path to the layered histogram file for a given runname"""
    return f'../results/{runname}/input/layered_histograms.nc'


def create_or_update_layered_histogram(runname):
    """Create layered histogram data if it doesn't exist"""
    print("Checking/creating layered histogram data...")

    layername = get_layered_histogram_path(runname)

    if Path(layername).exists():
        print(f"  Layered histogram already exists: {layername}")
        return layername

    print(f"  Creating layered histogram: {layername}")


    iters = np.arange(720-48-12, 720) * 1860  # Default iters

    with (xm.open_mdsdataset(f'../results/{runname}/input/',
                            prefix=['dissipation'], geometry='cartesian', endian='<',
                            iters='all', clear_cache=False
                            ) as dsdiss0,
        xm.open_mdsdataset(f'../results/{runname}/input/',
                            prefix=['spinup'], geometry='cartesian', endian='<',
                            iters='all', clear_cache=False
                            ) as ds0,
            xm.open_mdsdataset(f'../results/{runname}/input/',
                            prefix=['layDiag'], geometry='cartesian', endian='<',
                            iters='all', clear_cache=False
                            ) as dslayer):
        dt = float(1.0*ds0.time.diff(dim='time').median().values / 1e9)

        fact = int(1860 / dt)
        timeslice = slice(-24*5*fact, None)
        ds0 = ds0.isel(YC=0, YG=0, time=timeslice)
        dslayer = dslayer.isel(YC=0, YG=0, time=timeslice)
        ds0['XG'] = (ds0.XG - ds0.XC[-1]) / 1e3
        ds0['XC'] = (ds0.XC - ds0.XC[-1]) / 1e3
        dslayer['XG'] = (dslayer.XG - dslayer.XC[-1]) / 1e3
        dsdiss0 = dsdiss0.isel(YC=0, YG=0, time=timeslice)
        dsdiss0['XG'] = (dsdiss0.XG - dsdiss0.XC[-1]) / 1e3
        dsdiss0['XC'] = (dsdiss0.XC - dsdiss0.XC[-1]) / 1e3

        theta0 = ds0.THETA.isel(time=0)
        wet0 = theta0 != 0
        below_wet0 = wet0.shift(Z=1, fill_value=False)
        bottom_wet0 = wet0 & (~below_wet0)

        LayerTh = dslayer.layer_1TH_bounds.values
        ds0['KLeps'] = (('time', 'Z', 'XC'), dsdiss0['KLeps'].values)
        ds0['KLviscAr'] = (('time', 'Z', 'XC'), dsdiss0['KLviscAr'].values)

        ds0["drhodz"] = ds0.THETA.differentiate("Z") * (-0.2)
        K = ds0["KLviscAr"]
        Kf = 0.5 * (K.shift(Z=-1) + K)
        Kf = Kf.fillna(Kf.isel(Z=-2))
        ds0["Kf"] = K

        rho0 = ds0["THETA"] * (-0.2)
        rho = rho0.where(rho0<0, rho0.shift(Z=1))
        drhodz_f = (rho.shift(Z=-1) - rho) / (rho["Z"].shift(Z=-1) - rho["Z"])
        ds0["drhodz_f"] = drhodz_f

        ds0['F'] = Kf * ds0["drhodz_f"]
        ds0['F'] = ds0['F'].where(ds0.THETA > 0, 0.0)
        ds0['F'] = np.absolute(ds0.F)

        dz = float(ds0["Z"].diff("Z").mean())
        dFdz = (ds0['F'] - ds0['F'].shift(Z=1)) / dz
        ds0["dFdz"] = dFdz

        eps = 1e-12
        ds0["S"] = ds0["dFdz"] / xr.where(np.abs(ds0["drhodz"]) > eps, ds0["drhodz"],
                                          np.sign(ds0["drhodz"]) * eps)
        ds0["S"] = ds0["S"].where(wet0 & (~bottom_wet0), 0.0)

        hist0 = xhist.histogram(ds0['THETA'], bins=LayerTh[::1], dim=['Z'])
        hist = xhist.histogram(ds0['THETA'], bins=LayerTh[::1], weights=ds0.KLeps, dim=['Z'])

        ds0['UVELXC'] = ds0['UVEL'].interp(XG=ds0.XC)
        histU = xhist.histogram(ds0['THETA'], bins=LayerTh[::1], weights=ds0.UVELXC, dim=['Z'])
        histS = xhist.histogram(ds0['THETA'], bins=LayerTh[::1], weights=ds0.F, dim=['Z'])

        histU = histU.where(hist0 > 0)
        histS = histS.where(hist0 > 0)
        hist = hist.where(hist0 > 0)

        dhist = xr.Dataset({'KLeps': hist, 'UVEL': histU, 'Jb': histS*9.8/1000}).rename({'THETA_bin': 'layer_1TH_center'})
        dhist['layer_1TH_center'] = dslayer.layer_1TH_center
        dhist['tides'] = (('time'), np.astype(ds0.time.values, float) / 3600 / 12.4 / 1e9)
        dhist['LayerH'] = (('time', 'XC', 'layer_1TH_center'), hist0.values*10.0)

        dhist['Z0'] = (('layer_1TH_center'), np.interp(dhist.layer_1TH_center.values,
                                                        ds0.THETA.isel(time=0, XC=0).values[::-1],
                                                        ds0.Z.values[::-1]))
        dhist.to_netcdf(layername)
        print(f"  Created: {layername}")

    return layername


def generate_semilagrangian_snapshots(runname, mooringX, cmapU, cmapKL, lognorm,
                                     thetalevelspecial, xlim=None):
    """Generate semi-Lagrangian snapshot figures"""
    print("Generating semi-Lagrangian snapshots...")

    layername = get_layered_histogram_path(runname)
    iters = np.array([-24, -18, -12, -6]) * 2

    with (xr.open_dataset(layername) as dhist0,
          xm.open_mdsdataset(f'../results/{runname}/input/',
                           prefix=['spinup'], geometry='cartesian', endian='<',
                           iters='all', clear_cache=False
                           ) as ds0):
        ds0 = preprocess_run(ds0)

        # Determine appropriate xlimits from bathymetry
        if xlim is None:
            xlim = get_xlimits_from_depth(ds0, target_depth=2000, right_limit=-10)
        print(f"  Using xlim: {xlim}")

        fig, axs = plt.subplots(4, 2, layout='direct', figsize=(10, 8),
                               sharey=True, sharex=True)
        dhist0 = dhist0.sel(XC=slice(xlim[0]-10, None))
        zspecial = np.interp(thetalevelspecial, dhist0.layer_1TH_center.values, dhist0.Z0.values)

        for nn in range(4):
            axu = axs[nn, 0]
            axd = axs[nn, 1]
            tide = dhist0.tides.isel(time=iters[nn]).values
            pcmu = axu.pcolormesh(dhist0.XC, dhist0.Z0, dhist0.UVEL.isel(time=iters[nn]).T,
                                 shading='nearest', cmap=cmapU, vmin=-0.6, vmax=0.6, rasterized=True)

            pcmd = axd.pcolormesh(dhist0.XC, dhist0.Z0, dhist0.KLeps.isel(time=iters[nn]).T,
                                 shading='nearest', cmap=cmapKL, rasterized=True, norm=lognorm)
            axd.set_facecolor('lightgray')
            axu.set_facecolor('lightgray')

            for nax, ax in enumerate([axu, axd]):
                let = chr(ord('a') + nn + nax*4)
                ax.set_title(f'{let}) {tide:.2f} tides', loc='left', fontsize='medium')
                UU = dhist0.UVEL.isel(time=iters[nn]).sel(layer_1TH_center=thetalevelspecial,
                                                          method='nearest').values.flatten()
                Xmax = dhist0.XC.values[~np.isnan(UU)][-1]
                ax.plot([-50, Xmax], [zspecial[0], zspecial[0]], color='m', lw=1.5)
                plot_virt_moorings(ax, ds0, mooringX=mooringX)

            if nn == 0:
                axcb = axu.inset_axes([0.6, 0.32, 0.35, 0.04], transform=axu.transAxes)
                fig.colorbar(pcmu, cax=axcb, label=r'$U\ \mathrm{(m/s)}$',
                           orientation='horizontal', extend='both')
                axcb = axd.inset_axes([0.6, 0.32, 0.35, 0.04], transform=axd.transAxes)
                fig.colorbar(pcmd, cax=axcb, label=r'$\epsilon\ \mathrm{(m^2/s^3)}$',
                           orientation='horizontal', extend='both')
                axu.set_ylabel(r'Semi-Lagrangian Depth (m)')
            if nn==3:
                axd.set_xlabel(r'X (km)')
            axd.set_xlim(xlim)
            axd.set_ylim([-2000, 0])

        save_figure(fig, f'{runname}_U_eps_layered_snap')
        plt.close(fig)


def generate_semilagrangian_moorings(runname, mooringX, cmapU, cmapKL, lognorm,
                                    thetalevelspecial):
    """Generate semi-Lagrangian mooring time series"""
    print("Generating semi-Lagrangian moorings...")

    layername = get_layered_histogram_path(runname)
    with xr.open_dataset(layername) as dhist0:
        zspecial = np.interp(thetalevelspecial, dhist0.layer_1TH_center.values, dhist0.Z0.values)

        # Calculate time limits: show last 2.5 tidal cycles
        last_tide = float(dhist0.tides.max())
        tide_xlim = [last_tide - 2.5, last_tide]
        print(f"  Time range: {tide_xlim[0]:.2f} to {tide_xlim[1]:.2f} tidal cycles")

        fig, axs = plt.subplots(2, 6, layout='direct', figsize=(12, 5), sharey=True,
                               subplot_kw={'facecolor':'lightgray'}, width_ratios=[1, 0.5]*3)

        for nn in range(len(mooringX)):
            axu = axs[0, nn*2]
            axd = axs[1, nn*2]
            axum = axs[0, nn*2+1]
            axdm = axs[1, nn*2+1]

            dhist = dhist0.sel(XC=mooringX[nn], method='nearest')

            pcmu = axu.pcolormesh(dhist.tides, dhist.Z0,
                                  dhist.UVEL.T, shading='nearest', cmap=cmapU, vmin=-0.6, vmax=0.6,
                                  rasterized=True)
            axu.set_title(f'X = {mooringX[nn]:1.2f} km')
            if nn == 2:
                cax = axu.inset_axes([0.6, 0.25, 0.35, 0.04], transform=axu.transAxes)
                fig.colorbar(pcmu, cax=cax, label=r'$U\ \mathrm{(m/s)}$',
                           orientation='horizontal', extend='both')
            axu.set_title(f'{chr(ord("a")+nn)})', loc='left', fontsize='medium')
            axu.set_ylim([-2000, 0])
            axu.axhline(y=zspecial[0], color='m', linestyle='-', linewidth=1.5)

            U = dhist.UVEL.isel(time=slice(-48*4, None))
            U = U.fillna(0.0)
            axum.plot(U.mean(dim='time'), dhist.Z0)
            axum.set_xlim([-0.29999, 0.29999])
            axum.set_xticks(np.arange(-0.2, 0.21, 0.2))

            pcmd = axd.pcolormesh(dhist.tides, dhist.Z0,
                                    dhist.KLeps.T, shading='nearest', cmap=cmapKL,
                                    norm=lognorm, rasterized=True)
            if nn == 2:
                cax = axd.inset_axes([0.6, 0.25, 0.35, 0.04], transform=axd.transAxes)
                fig.colorbar(pcmd, cax=cax, label=r'$\epsilon\ \mathrm{(m^2/s^3)}$',
                           orientation='horizontal', extend='both')
                axd.set_xlabel(r'Time [tidal cycles]')
            axd.set_title(f'{chr(ord("a")+nn+3)})', loc='left', fontsize='medium')
            axd.axhline(y=zspecial[0], color='m', linestyle='-', linewidth=1.5)
            if nn == 0:
                axu.set_ylabel(r'SL-Depth (m)')

            Eps = dhist.KLeps.isel(time=slice(-48*4, None))
            Eps = Eps.fillna(1e-20)
            axdm.semilogx(Eps.mean(dim='time'), dhist.Z0)
            axdm.set_xlim([.099e-11, 1e-4])
            if nn == 0:
                axdm.set_xlabel(r'$\left<\epsilon\right>\ \mathrm{(m^2/s^3)}$')
                axum.set_xlabel(r'$\left<U\right>\ \mathrm{(m/s)}$')
            for ax in [axu, axd]:
                ax.set_xlim(tide_xlim)
                ax.set_ylim([-2000, 0])
            for ax in [axum, axdm]:
                ax.grid('on')
                ax.set_facecolor('white')

        save_figure(fig, f'{runname}_U_eps_layered_moorings')
        plt.close(fig)


def generate_semilagrangian_means(runname, mooringX, cmapU, cmapKL, lognorm,
                                  thetalevelspecial, xlim=None, run_comment=None, uscale=0.2):
    """Generate semi-Lagrangian mean sections"""
    print("Generating semi-Lagrangian means...")

    layername = get_layered_histogram_path(runname)
    with (xr.open_dataset(layername) as dhist0,
          xm.open_mdsdataset(f'../results/{runname}/input/',
                           prefix=['spinup'], geometry='cartesian', endian='<',
                           iters='all', clear_cache=False
                           ) as ds0):
        ds0 = preprocess_run(ds0)

        # Determine appropriate xlimits from bathymetry
        if xlim is None:
            xlim = get_xlimits_from_depth(ds0, target_depth=2000, right_limit=0)
        print(f"  Using xlim: {xlim}")

        fig, ax = plt.subplots(1, 2, layout='direct', figsize=(10, 2.6), sharey=True,
                              sharex=True, subplot_kw={'facecolor':'lightgray'})

        dhist = dhist0.sel(XC=slice(xlim[0]-10, None)).mean(dim='time')
        zspecial = np.interp(thetalevelspecial, dhist0.layer_1TH_center.values, dhist0.Z0.values)

        axu = ax[0]
        axd = ax[1]
        axu.set_title('a) ' + run_comment, fontsize='medium', loc='left')
        pcmu = axu.pcolormesh(dhist.XC, dhist.Z0, dhist.UVEL.T, shading='nearest',
                             cmap=cmapU, vmin=-uscale, vmax=uscale, rasterized=True)
        axcb = axu.inset_axes([0.7, 0.32, 0.25, 0.04], transform=axu.transAxes)
        fig.colorbar(pcmu, cax=axcb, label=r'$\left<U\right>\ \mathrm{(m/s)}$',
                   orientation='horizontal', extend='both')
        axu.set_ylabel(r'Semi-Lagrangian Depth (m)')

        pcmd = axd.pcolormesh(dhist.XC, dhist.Z0, dhist.KLeps.T, shading='nearest',
                             cmap=cmapKL, rasterized=True, norm=lognorm)
        axd.set_facecolor('lightgray')
        axcb = axd.inset_axes([0.7, 0.32, 0.25, 0.04], transform=axd.transAxes)
        fig.colorbar(pcmd, cax=axcb, label=r'$\left<\epsilon\right>\ \mathrm{(m^2/s^3)}$',
                   orientation='horizontal', extend='both')
        axd.set_xlabel(r'X (km)')

        for nn, axp in enumerate([axu, axd]):
            axp.text(-2, -800, f'{chr(ord("a")+nn)}) Last 5 tides', color='k', ha='right')
            # Plot special isopycnal line to its maximum extent
            uu = dhist.UVEL.sel(layer_1TH_center=thetalevelspecial, method='nearest').values.flatten()
            Xmax = dhist.XC.values[~np.isnan(uu)][-1]
            axp.plot([xlim[0], Xmax],  [zspecial[0], zspecial[0]], color='m', lw=1.5)
            axp.set_xlim(xlim)
            plot_virt_moorings(axp, ds0, mooringX=mooringX)

        save_figure(fig, f'{runname}_U_eps_layeredave')
        plt.close(fig)


def generate_streamfunction(runname, xlim=None, run_comment=None, interactive_mode=False):
    """Generate streamfunction plot"""
    print("Generating streamfunction plot...")

    layername = get_layered_histogram_path(runname)
    with (xm.open_mdsdataset(f'../results/{runname}/input/',
                            prefix=['layDiag'], geometry='cartesian', endian='<',
                            iters='all', clear_cache=False
                            ) as dslayer,
          xm.open_mdsdataset(f'../results/{runname}/input/',
                            prefix=['layTher'], geometry='cartesian', endian='<',
                            iters='all', clear_cache=False
                            ) as dsthermo,
          xr.open_dataset(layername) as dhist0,
          xm.open_mdsdataset(f'../results/{runname}/input/',
                           prefix=['spinup'], geometry='cartesian', endian='<',
                           iters='all', clear_cache=False
                           ) as ds0,
          xm.open_mdsdataset(f'../results/{runname}/input/',
                           prefix=['layHsnap'], geometry='cartesian', endian='<',
                           iters='all', clear_cache=False
                           ) as dshsnap
        ):

        start = -5
        ds0 = preprocess_run(ds0)
        dsthermo = preprocess_run(dsthermo)
        dsthermo = dsthermo.isel(time=slice(start, None)).mean(dim='time')

        dslayer = preprocess_run(dslayer)
        dslayer = dslayer.isel(time=slice(start, None))

        dhsnap = preprocess_run(dshsnap)
        print(dhsnap)
        dhsnap = dhsnap.isel(time=slice(start-1,  None))

        print(dslayer.time.values)
        print(dhsnap.time.values)

        print('-------------------')
        # calc the time rate of change of the layer thickness:

        dH = dhsnap.LaHw1TH.isel(time=-1) - dhsnap.LaHw1TH.isel(time=0)

        dHdt = dH / (float(dhsnap.time.isel(time=-1) - dhsnap.time.isel(time=0).values)/1e9)

        dHdtOld = dslayer.LaHw1TH.isel(time=-1) - dslayer.LaHw1TH.isel(time=0)
        dHdtOld = (5./6.)*dHdtOld / (float(dslayer.time.isel(time=-1) - dslayer.time.isel(time=0).values)/1e9)

        print(dslayer.time[-1].values, dslayer.time[0].values)

        dslayer = dslayer.mean(dim='time')

        # Determine appropriate xlimits from bathymetry
        if xlim is None:
            xlim = get_xlimits_from_depth(ds0, target_depth=2000, right_limit=0)
        xmin = xlim[0]
        print(f"  Using xlim: {xlim}, xmin for integration: {xmin}")

        dslayer['Z0'] = (('layer_1TH_center'), np.interp(dslayer.layer_1TH_center.values,
                                                          ds0.THETA.isel(time=0, XC=0).values[::-1],
                                                          ds0.Z.values[::-1]))

        layer_bounds = np.asarray(dslayer.layer_1TH_bounds.values, dtype=float)
        dtheta = xr.DataArray(np.diff(layer_bounds),
                              dims=('layer_1TH_center',),
                              coords={'layer_1TH_center': dslayer.layer_1TH_center.values})

        def theta_cumsum(da):
            return (da * dtheta).cumsum('layer_1TH_center')

        fig, axs = plt.subplots(1, 3, layout='direct', figsize=(7.3, 4),
                               width_ratios=[1, 0.3, 0.3], sharey=True)

        ax = axs[0]
        psi = theta_cumsum(dslayer.LaUH1TH)
        thesum = psi.sel(XG=slice(xmin, 0)).isel(XG=0, layer_1TH_center=-1)
        if run_comment is not None:
            ax.set_title('a) ' + run_comment, fontsize='medium', loc='left')
        pp = ax.pcolormesh(dslayer.XC, dslayer.Z0, psi,
                          cmap='RdBu_r', shading='nearest', rasterized=True, vmin=-10, vmax=10)
        ax.contour(dslayer.XC, dslayer.Z0, psi - thesum,
                  levels=np.arange(-10, 11, 0.5), colors='0.4', linewidths=0.5)
        ax.set_xlim(xlim)
        ax.set_facecolor('lightgray')
        ax.set_xlabel(r'X (km)')
        ax.set_ylabel(r'Semi-Lagrangian Depth (m)')
        cax = ax.inset_axes([0.7, 0.22, 0.23, 0.04], transform=ax.transAxes)
        fig.colorbar(pp, cax=cax, label=r'$\Psi\ \mathrm{(m^2/s)}$',
                   orientation='horizontal', extend='both')

        ax = axs[1]
        ax.set_title('b)', loc='left', fontsize='medium')

        wflux = theta_cumsum(dslayer.LaUH1TH.sel(XG=slice(xmin, 0)).isel(XG=0))
        dhdt = theta_cumsum(dHdt.sel(XG=slice(xmin, 0)).integrate('XG')) * 1000
        wflux = wflux - dhdt
        # Show sign of overturning transport relative to zero baseline.
        ax.axvline(0.0, color='0.35', lw=1.0, ls='--')
        y = dslayer.Z0.values
        x = wflux.values
        ax.fill_betweenx(y, 0.0, x, where=(x >= 0), color='#c44e52', alpha=0.35, interpolate=True)
        ax.fill_betweenx(y, 0.0, x, where=(x < 0), color='#4c72b0', alpha=0.35, interpolate=True)
        ax.plot(x, y, lw=1.6, color='0.2')
        ax.set_xlabel(r'$\int w \, \mathrm{d}x\ \mathrm{(m^2/s)}$')
        ax.grid('on')
        # ax.set_xlim([-2.4999, 2.4999])
        print('Plot!')
        ax.plot(dhdt, dslayer.Z0, lw=1, color='k', ls='-', label='Layer thickness tendency')
        dhdt_old = theta_cumsum(dHdtOld.sel(XG=slice(xmin, 0)).integrate('XG')) * 1000
        ax.plot(dhdt_old, dslayer.Z0, lw=1, color='c', ls='-', label='Layer thickness tendency')

        ax = axs[2]

        # get Jb from the thermo diagnostic:
        drho = 0.2 * 0.04

        Jb = dsthermo.LaTz1TH.sel(XC=slice(xmin, 0)).cumsum('layer_1TH_interface').integrate('XC') * 1000.0 * drho

        ax.set_title('c)', loc='left', fontsize='medium')
        ax.plot(Jb, dslayer.Z0[1:], lw=1, ls='-', label='Diff.', color='C1')
        ax.plot(dhist0.KLeps.sel(XC=slice(xmin, 0)).fillna(0).mean('time').integrate('XC')*1000*0.2*1000/9.8,
               dhist0.Z0, label='Diss.', color='C0')

        # this estimate is quite poor:
        # ax.plot(dhist0.Jb.sel(XC=slice(xmin, 0)).fillna(0).mean('time').integrate('XC')*1000*1000/9.8,
        #       dhist0.Z0, label='Diff.')
        circ = theta_cumsum(theta_cumsum(dslayer.LaUH1TH.sel(XG=xmin, method='nearest')))
        dhdt_int = theta_cumsum(dhdt)
        ax.plot((circ - dhdt_int) * drho,
               dslayer.Z0, lw=2, label='Circ', color='C2')
        ax.plot(circ * drho,
               dslayer.Z0, lw=0.5, label='Circ', color='m')
        ax.set_xlabel(r'$\int J_b \, \mathrm{d}x\ \mathrm{(m^3/s^3)}$')
        ax.grid('on')
        ax.legend(fontsize='small', loc='center right')
        #ax.set_xlim([0, 0.45])
        save_figure(fig, f'{runname}_psi_layered')
        if not interactive_mode:
            plt.close(fig)


def plot_hovmoller_velocity_dissipation(runname, thetalevelspecial,
                                        cmapKL=None, lognorm=None, xlim=None):
    """
    Generate Hovmoller plot of velocity and dissipation along special
    isopycnal
    """

    print("Generating Hovmoller plot of velocity and dissipation...")

    layername = get_layered_histogram_path(runname)
    with xr.open_dataset(layername) as dhist0:

        # zspecial = np.interp(thetalevelspecial, dhist0.layer_1TH_center.values, dhist0.Z0.values)
        dhist0 = dhist0.sel(layer_1TH_center=thetalevelspecial, method='nearest')
        # Assume dhist0 has a 'time' or 'tides' dimension of length 240 (5*48)
        n_cycles = 5
        n_per_cycle = 48

        # Reshape and average over cycles
        n_cycles = 5
        n_per_cycle = 48

        # Ensure time is the correct length
        dhist0 = dhist0.isel(time=slice(0, n_cycles * n_per_cycle))

        # Reshape the data: new dims will be ('cycle', 'phase', ...)
        dhist0_reshaped = dhist0.assign_coords(
            cycle=("time", np.repeat(np.arange(n_cycles), n_per_cycle)),
            phase=("time", np.tile(np.arange(n_per_cycle), n_cycles))
        ).set_index(time=["cycle", "phase"]).unstack("time")

        # Now average over 'cycle'
        dhist0 = dhist0_reshaped.mean(dim="cycle")


        maxx = np.nanmax(np.argmax(~np.isnan(dhist0.UVEL.values), axis=1))
        max_XC = dhist0.XC.where(dhist0.UVEL.notnull().any("phase")).max()
        print(max_XC)
        if xlim is None:
            xlim = (max_XC - 40, max_XC + 4)
        dhist0 = dhist0.sel(XC=slice(*xlim)).where(dhist0.tides> dhist0.tides[-1]-2.5, drop=True)


        fig, axs = plt.subplots(2, 2, layout='direct', figsize=(6, 4), sharex=False, sharey=True, subplot_kw={'facecolor':'lightgray'}, width_ratios=[1, 0.5])

        ax = axs[0,0]
        # Squeeze singleton dimension to ensure shape matches (Y, X)
        uvel = dhist0.UVEL.squeeze()
        print(dhist0)

        pcm = ax.pcolormesh( dhist0.XC, dhist0.tides, uvel.T,
                    shading='nearest', cmap='RdBu_r', rasterized=True,
                    vmin=-0.7, vmax=0.7)
        ax.set_xlabel(r'Time [tidal cycles]')
        ax.set_ylabel(r'X (km)')

        fig.colorbar(pcm, ax=ax, label=r'$U \mathrm{(m/s)}$',
                   orientation='vertical', extend='both')
        #ax.axhline(y=mooringX[0], color='k', linestyle='--', lw=1)
        #ax.axhline(y=mooringX[1], color='k', linestyle='--', lw=1)
        #ax.axhline(y=mooringX[2], color='k', linestyle='--', lw=1)


        ax = axs[1,0]
        pcm = ax.pcolormesh(dhist0.XC, dhist0.tides, dhist0.KLeps.squeeze().T,
                            shading='nearest', cmap=cmapKL, norm=lognorm, rasterized=True)
        ax.set_ylabel(r'Time [tidal cycles]')

        ax.set_xlabel(r'X (km)')
        fig.colorbar(pcm, ax=ax, label=r'$\epsilon\ \mathrm{(m^2/s^3)}$',
                   orientation='vertical', extend='both')
        #ax.axhline(y=mooringX[0], color='k', linestyle='--', lw=1)
        #ax.axhline(y=mooringX[1], color='k', linestyle='--', lw=1)
        #ax.axhline(y=mooringX[2], color='k', linestyle='--', lw=1)
        axs[1, 1].semilogx(dhist0.KLeps.mean(dim='XC').squeeze(), dhist0.tides)
        axs[1, 1].set_xlim(1e-8, 6e-6)
        axs[0,0].set_title(f'{runname}: Hovmoller along {thetalevelspecial} isopycnal', loc='center', fontsize='medium')
        save_figure(fig, f'{runname}_dissipation_hovmoller')
        plt.close(fig)



def generate_markdown_snippet(runname, mooringX, run_comment=None):
    """Generate markdown snippet with figure captions"""
    print("\nGenerating markdown snippet...")

    comment_block = ''
    if run_comment:
        comment_block = f"\nRun description: {run_comment}\n"

    markdown = f"""
## Run {runname}

{comment_block}

Mooring locations: X = {', '.join([f'{x} km' for x in mooringX])}

![Snapshots of velocity (a--d) and dissipation (e--h) for run {runname}. Thick contours are density contours](../analysis/doc/{runname}_U_eps_snap.png){{#fig:{runname}_U_eps_snap}}

![Tidal average of a) velocity and b) dissipation for run {runname}. Both panels have the mean density field contoured.](../analysis/doc/{runname}_U_eps_eulerianave.png){{#fig:{runname}_U_eps_eulerianave}}

![Virtual moorings time series for run {runname} showing a-c) velocity and d-f) dissipation.](../analysis/doc/{runname}_U_eps_timeseries_moorings.png){{#fig:{runname}_U_eps_timeseries_moorings}}

![Semi-Lagrangian snapshots of velocity (a--d) and dissipation (e--h) for run {runname}.](../analysis/doc/{runname}_U_eps_layered_snap.png){{#fig:{runname}_U_eps_layered_snap}}

![Semi-Lagrangian mooring time series for run {runname}.](../analysis/doc/{runname}_U_eps_layered_moorings.png){{#fig:{runname}_U_eps_layered_moorings}}

![Semi-Lagrangian mean sections for run {runname} showing a) velocity and b) dissipation.](../analysis/doc/{runname}_U_eps_layeredave.png){{#fig:{runname}_U_eps_layeredave}}

![Hovmoller of velocity and dissipation for run {runname} showing a) velocity and b) dissipation.](../analysis/doc/{runname}_U_eps_hovmoller.png){{#fig:{runname}_U_eps_hovmoller}}

![Streamfunction and buoyancy flux diagnostics for run {runname}.](../analysis/doc/{runname}_psi_layered.png){{#fig:{runname}_psi_layered}}
"""

    # Save markdown snippet to plot_summaries directory
    markdown_dir = Path('../plot_summaries')
    markdown_dir.mkdir(exist_ok=True)
    markdown_file = markdown_dir / f'{runname}_figures.md'
    with open(markdown_file, 'w') as f:
        f.write(markdown)

    print(f"Markdown snippet saved to: {markdown_file}")
    print("\nMarkdown content:")
    print(markdown)

    return markdown


def main():
    parser = argparse.ArgumentParser(description='Generate figures for CanyonMix analysis')
    parser.add_argument('--runname', type=str, required=True, help='Run name (e.g., Slope2D093)')
    parser.add_argument('--mooringX', nargs='+', type=float,
                       help='Mooring X locations in km (e.g., -55 -45 -35)')
    parser.add_argument('--mooringZ', nargs='+', type=float,
                       help='Mooring depths in m, negative down (e.g., -1750 -1250 -750)')
    parser.add_argument('--skip-layered', action='store_true',
                       help='Skip semi-Lagrangian analysis (if data missing)')
    parser.add_argument('--xlim', nargs=2, type=float, metavar=('XMIN', 'XMAX'),
                       help='X-axis limits for plots (e.g., --xlim -50 50)')
    parser.add_argument('--run-comment', type=str, default=None,
                       help='Optional markdown comment describing what this run is doing')
    parser.add_argument('--uscale', type=float, default=0.2,
                       help='Optional scale for velocity plots (e.g., --uscale 0.2)')
    parser.add_argument('--method', nargs='+', default=['all'],
                       choices=[
                           'all',
                           'eulerian_snapshots',
                           'eulerian_means',
                           'timeseries_moorings',
                           'semilagrangian_snapshots',
                           'semilagrangian_moorings',
                           'semilagrangian_means',
                           'streamfunction',
                           'hovmoller',
                           'markdown',
                       ],
                       help=('Optional one or more methods to run. '
                             'Defaults to all methods.'))

    args = parser.parse_args()

    uscale = args.uscale

    runname = args.runname
    if args.mooringZ is None and args.mooringX is None:
        parser.error('Provide at least one of --mooringX or --mooringZ')

    mooringZ = None if args.mooringZ is None else np.array(args.mooringZ, dtype=float)
    mooringX = None if args.mooringX is None else np.array(args.mooringX, dtype=float)
    xlim = None if args.xlim is None else np.array(args.xlim, dtype=float)
    run_comment = args.run_comment

    all_methods = {
        'eulerian_snapshots',
        'eulerian_means',
        'timeseries_moorings',
        'semilagrangian_snapshots',
        'semilagrangian_moorings',
        'semilagrangian_means',
        'streamfunction',
        'hovmoller',
        'markdown',
    }
    selected_methods = set(args.method)
    if 'all' in selected_methods:
        selected_methods = set(all_methods)

    print(f"Input parameters: runname={runname}, mooringX={mooringX}, mooringZ={mooringZ}, xlim={xlim}, run_comment={run_comment}, methods={sorted(selected_methods)}")


    if mooringZ is not None:
        available_iters = get_available_iterations(runname, 'spinup')
        first_iter = int(available_iters[0])
        with xm.open_mdsdataset(
            f'../results/{runname}/input/',
            prefix=['spinup'], geometry='cartesian', endian='<',
            iters=[first_iter], clear_cache=False
        ) as ds0:
            ds0 = preprocess_run(ds0)
            mooringX = get_mooringX_from_mooringZ(ds0, mooringZ)
            if xlim is None:
                xlim = get_xlimits_from_depth(ds0, target_depth=2000, right_limit=0)

    print(f"\n{'='*60}")
    print(f"Generating figures for run: {runname}")
    if mooringZ is not None:
        print(f"Requested mooring depths (m): {mooringZ}")
    print(f"Mooring locations (km): {mooringX}")
    print(f"X-axis limits: {xlim}")
    print(f"{'='*60}\n")

    # Setup color maps and normalization
    lognorm = mcolors.LogNorm(vmin=1e-9, vmax=1e-5)
    thetalevels = np.arange(20, 28, 0.2)
    thetalevelsmaj = np.arange(20, 28, 1)
    thetalevelspecial = np.array([25.6])
    thetalevels = thetalevels[~np.isin(thetalevels, thetalevelsmaj)]
    cmapKL = plt.get_cmap('hot_r')
    cmapU = plt.get_cmap('RdBu_r')

    layered_methods = {
        'semilagrangian_snapshots',
        'semilagrangian_moorings',
        'semilagrangian_means',
        'streamfunction',
        'hovmoller',
    }
    needs_layered = bool(selected_methods & layered_methods)

    if 'eulerian_snapshots' in selected_methods:
        try:
            generate_eulerian_snapshots(runname, mooringX, cmapU, cmapKL, lognorm,
                                       thetalevels, thetalevelsmaj, thetalevelspecial, xlim=xlim)
        except Exception as e:
            print(f"Error generating Eulerian snapshots: {e}")
            traceback.print_exc()

    if 'eulerian_means' in selected_methods:
        try:
            generate_eulerian_means(runname, mooringX, cmapU, cmapKL, lognorm,
                                   thetalevels, thetalevelsmaj, thetalevelspecial, xlim=xlim, run_comment=run_comment)
        except Exception as e:
            print(f"Error generating Eulerian means: {e}")
            traceback.print_exc()

    if 'timeseries_moorings' in selected_methods:
        try:
            generate_timeseries_moorings(runname, mooringX, cmapU, cmapKL, lognorm,
                                        thetalevels, thetalevelsmaj, thetalevelspecial)
        except Exception as e:
            print(f"Error generating timeseries moorings: {e}")
            traceback.print_exc()

    # Generate Semi-Lagrangian figures if selected and not skipped.
    if needs_layered:
        if args.skip_layered:
            print("Skipping requested layered methods due to --skip-layered")
        else:
            try:
                create_or_update_layered_histogram(runname)
            except Exception as e:
                print(f"Error preparing layered data: {e}")
                traceback.print_exc()

            if 'semilagrangian_snapshots' in selected_methods:
                try:
                    generate_semilagrangian_snapshots(runname, mooringX, cmapU, cmapKL, lognorm,
                                                     thetalevelspecial, xlim=xlim)
                except Exception as e:
                    print(f"Error generating semi-Lagrangian snapshots: {e}")
                    traceback.print_exc()

            if 'semilagrangian_moorings' in selected_methods:
                try:
                    generate_semilagrangian_moorings(runname, mooringX, cmapU, cmapKL, lognorm,
                                                    thetalevelspecial)
                except Exception as e:
                    print(f"Error generating semi-Lagrangian moorings: {e}")
                    traceback.print_exc()

            if 'semilagrangian_means' in selected_methods:
                try:
                    generate_semilagrangian_means(runname, mooringX, cmapU, cmapKL, lognorm,
                                                 thetalevelspecial, xlim=xlim, run_comment=run_comment, uscale=uscale)
                except Exception as e:
                    print(f"Error generating semi-Lagrangian means: {e}")
                    traceback.print_exc()

            if 'streamfunction' in selected_methods:
                try:
                    generate_streamfunction(runname, xlim=xlim, run_comment=run_comment)
                except Exception as e:
                    print(f"Error generating streamfunction: {e}")
                    traceback.print_exc()

            if 'hovmoller' in selected_methods:
                try:
                    plot_hovmoller_velocity_dissipation(runname, thetalevelspecial,
                                                        cmapKL, lognorm, xlim=xlim)
                except Exception as e:
                    print(f"Error generating Hovmoller: {e}")
                    traceback.print_exc()

    # Generate markdown snippet
    if 'markdown' in selected_methods:
        generate_markdown_snippet(runname, mooringX, run_comment=run_comment)

    print(f"\n{'='*60}")
    print("Figure generation complete!")
    print(f"{'='*60}\n")


if __name__ == '__main__':
    main()
