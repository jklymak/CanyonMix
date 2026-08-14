#!/usr/bin/env python3
"""Compare Eulerian buoyancy-advection terms from MITgcm diagnostics.

Computes and plots:
- <w N^2>
- <w><N^2>
- <w' N^2'> = <w N^2> - <w><N^2>

where N^2 is estimated from DRHODR using:
    N^2 = -(g/rho0) * DRHODR

The script expects DRHODR and WVEL in tideave diagnostics.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import xarray as xr
import xmitgcm as xm


def _choose_dim(da: xr.DataArray, candidates: list[str], field_name: str) -> str:
    for dim in candidates:
        if dim in da.dims:
            return dim
    raise ValueError(f"No valid dimension found for {field_name}. Tried {candidates}, got {da.dims}.")


def _align_vertical(w: xr.DataArray, n2: xr.DataArray) -> tuple[xr.DataArray, xr.DataArray, str]:
    """Ensure w and N2 share the same vertical coordinate for multiplication."""
    z_w = _choose_dim(w, ["Zl", "Z"], "WVEL")
    z_n2 = _choose_dim(n2, ["Zl", "Z"], "N2")

    if z_w == z_n2:
        return w, n2, z_w

    if z_w == "Zl" and z_n2 == "Z":
        n2 = n2.interp(Z=w["Zl"]).rename({"Z": "Zl"})
        return w, n2, "Zl"

    if z_w == "Z" and z_n2 == "Zl":
        w = w.interp(Zl=n2["Z"]).rename({"Zl": "Z"})
        return w, n2, "Z"

    raise ValueError(f"Unhandled vertical alignment: WVEL on {z_w}, N2 on {z_n2}")


def compute_terms(ds: xr.Dataset, xmin: float, xmax: float, g: float, rho0: float) -> xr.Dataset:
    if "WVEL" not in ds:
        raise KeyError("WVEL not found in dataset. Add WVEL to tideave diagnostics.")
    if "DRHODR" not in ds:
        raise KeyError("DRHODR not found in dataset. Add DRHODR to tideave diagnostics.")

    w = ds["WVEL"]
    drhodr = ds["DRHODR"]
    n2 = -(g / rho0) * drhodr

    w, n2, zdim = _align_vertical(w, n2)

    xdim = _choose_dim(w, ["XC", "XG"], "WVEL")

    w_sub = w.sel({xdim: slice(xmin, xmax)})
    n2_sub = n2.sel({xdim: slice(xmin, xmax)})

    wn2 = w_sub * n2_sub

    wn2_mean = wn2.mean("time")
    w_mean = w_sub.mean("time")
    n2_mean = n2_sub.mean("time")

    prof_wn2 = wn2_mean.mean(xdim)
    prof_w_n2 = (w_mean * n2_mean).mean(xdim)
    prof_cov = prof_wn2 - prof_w_n2

    out = xr.Dataset(
        {
            "wn2_mean": prof_wn2,
            "w_mean_n2_mean": prof_w_n2,
            "cov_w_n2": prof_cov,
        }
    )

    if "WdRHOdP" in ds:
        wdrho = ds["WdRHOdP"]
        wdrho, _, _ = _align_vertical(wdrho, n2)
        wdbdz_from_wdrho = -(g / rho0) * wdrho.sel({xdim: slice(xmin, xmax)}).mean(["time", xdim])
        out["wdbdz_from_wdrhodp"] = wdbdz_from_wdrho

    out = out.rename({zdim: "z"})
    return out


def plot_profiles(ds_terms: xr.Dataset, runname: str, out_png: Path) -> None:
    fig, ax = plt.subplots(figsize=(4.5, 5.0), layout="constrained")

    ax.plot(ds_terms["wn2_mean"], ds_terms["z"], lw=2, label=r"$\langle w N^2 \rangle$")
    ax.plot(ds_terms["w_mean_n2_mean"], ds_terms["z"], lw=2, label=r"$\langle w \rangle\langle N^2 \rangle$")
    ax.plot(ds_terms["cov_w_n2"], ds_terms["z"], lw=1.5, ls="--", label=r"$\langle w' N^{2\prime} \rangle$")

    if "wdbdz_from_wdrhodp" in ds_terms:
        ax.plot(ds_terms["wdbdz_from_wdrhodp"], ds_terms["z"], lw=1.0, ls=":", label=r"$-(g/\rho_0)\langle WdRHOdP \rangle$")

    ax.axvline(0.0, color="0.3", lw=0.8)
    ax.grid(True, alpha=0.3)
    ax.set_ylabel("Depth (m)")
    ax.set_xlabel(r"Buoyancy advection term ($s^{-3}$)")
    ax.set_title(f"{runname}: Eulerian buoyancy terms")
    ax.legend(fontsize="small")

    fig.savefig(out_png, dpi=180)
    plt.close(fig)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compare <wN^2> and <w><N^2> from MITgcm tideave diagnostics")
    parser.add_argument("--runname", required=True, help="Run name under ../results (e.g., Slope2D103)")
    parser.add_argument("--xmin", type=float, default=-50.0, help="Left x-limit in km for averaging (default: -50)")
    parser.add_argument("--xmax", type=float, default=0.0, help="Right x-limit in km for averaging (default: 0)")
    parser.add_argument("--nt", type=int, default=5, help="Number of tideave time records from the end (default: 5)")
    parser.add_argument("--rho0", type=float, default=1000.0, help="Reference density for N^2 conversion")
    parser.add_argument("--g", type=float, default=9.81, help="Gravity for N^2 conversion")
    parser.add_argument("--outdir", default="doc", help="Output directory for figure and NetCDF")
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    data_dir = Path("..") / "results" / args.runname / "input"
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    out_png = outdir / f"{args.runname}_eulerian_buoyancy_terms.png"
    out_nc = outdir / f"{args.runname}_eulerian_buoyancy_terms.nc"

    with xm.open_mdsdataset(
        str(data_dir),
        prefix=["tideave"],
        geometry="cartesian",
        endian="<",
        iters="all",
    ) as ds0:
        ds = ds0.isel(YC=0, YG=0)
        ds = ds.isel(time=slice(-args.nt, None))

        xref = ds["XC"].isel(XC=-1)
        ds["XC"] = (ds["XC"] - xref) / 1000.0
        if "XG" in ds:
            ds["XG"] = (ds["XG"] - xref) / 1000.0

        terms = compute_terms(ds, xmin=args.xmin, xmax=args.xmax, g=args.g, rho0=args.rho0)

    terms.to_netcdf(out_nc)
    plot_profiles(terms, args.runname, out_png)

    cov_bulk = float(terms["cov_w_n2"].mean("z").values)
    print(f"Saved: {out_png}")
    print(f"Saved: {out_nc}")
    print(f"Domain-mean covariance <w'N^2'> over selected x,z = {cov_bulk:.3e} s^-3")


if __name__ == "__main__":
    main()
