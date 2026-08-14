# Analysis: `NewLayers.ipynb`

Exploratory analysis that went into `generate_figures.py`.  Probably will add some more

## Eulerian Buoyancy Terms

Use `eulerian_buoyancy_terms.py` to compare

- $\langle w N^2 \rangle$
- $\langle w \rangle\langle N^2 \rangle$
- $\langle w' N^{2\prime} \rangle = \langle wN^2 \rangle - \langle w \rangle\langle N^2 \rangle$

from `tideave` diagnostics.

Example:

```bash
cd /Users/jklymak/Dropbox/CanyonMix/analysis
python eulerian_buoyancy_terms.py --runname Slope2D103 --xmin -50 --xmax 0 --nt 5
```

Outputs:

- `analysis/doc/{runname}_eulerian_buoyancy_terms.png`
- `analysis/doc/{runname}_eulerian_buoyancy_terms.nc`

Required diagnostics fields in `tideave`:

- `WVEL`
- `DRHODR`

Optional (used as a consistency check if available):

- `WdRHOdP`


# Generate Figures Script

This script automates the figure generation from the `NewLayers.ipynb` notebook analysis.

## Usage

### Basic usage with required arguments:

```bash
cd /Users/jklymak/Dropbox/CanyonMix/analysis
python generate_figures.py --runname Slope2D093 --mooringX -55 -45 -35
```

### Another example:

```bash
python generate_figures.py --runname Slope2D091 --mooringX -36 -31 -24
```

### Skip semi-Lagrangian analysis (if layered data is missing/problematic):

```bash
python generate_figures.py --runname Slope2D093 --mooringX -55 -45 -35 --skip-layered
```

## Arguments

- `--runname`: (Required) Name of the model run (e.g., `Slope2D093`)
- `--mooringX`: (Required) X-coordinates for virtual moorings (space-separated, e.g., `-55 -45 -35`)
- `--skip-layered`: (Optional) Skip semi-Lagrangian (layered) analysis

## Output

The script generates:

1. **Figures** in `analysis/doc/`:
   - `{runname}_U_eps_snap.png` & `.pdf` - Eulerian velocity/dissipation snapshots
   - `{runname}_U_eps_eulerianave.png` & `.pdf` - Eulerian means
   - `{runname}_U_eps_timeseries_moorings.png` & `.pdf` - Time series at moorings
   - `{runname}_U_eps_layered_snap.png` & `.pdf` - Semi-Lagrangian snapshots
   - `{runname}_U_eps_layered_moorings.png` & `.pdf` - Semi-Lagrangian moorings
   - `{runname}_U_eps_layeredave.png` & `.pdf` - Semi-Lagrangian means
   - `{runname}_psi_layered.png` & `.pdf` - Streamfunction

2. **Markdown snippet** in `analysis/doc/{runname}_figures.md`:
   - Contains figure references with captions
   - Ready to paste into `writeup/Notes.md` or other documents

3. **Layered histogram data** (if needed) in `../results/{runname}/input/layered_histograms.nc`:
   - Auto-generated on first run if missing
   - Reused on subsequent runs

## Figures Generated

### Eulerian Analysis
- **Snapshots**: 4 time snapshots showing velocity (left) and dissipation (right) with density contours
- **Means**: Tidal-averaged velocity and dissipation fields
- **Moorings Time Series**: Full time series at each virtual mooring location

### Semi-Lagrangian Analysis (Isopycnal Coordinates)
- **Snapshots**: 4 time snapshots in isopycnal space
- **Moorings Time Series**: Time series and profiles at mooring locations
- **Mean Sections**: Tidal-averaged fields in isopycnal coordinates
- **Streamfunction**: Overturning circulation and buoyancy flux diagnostics

## Requirements

The script requires the following Python packages (already in `pixi.toml`):
- xmitgcm
- xarray
- numpy
- matplotlib
- xhistogram
- jmkfigure (optional, for enhanced figure saving)

## Notes

- The script runs in non-interactive mode (figures are saved, not displayed)
- Computation of layered histogram data can take several minutes on first run
- Progress messages are printed to help track execution
- If jmkfigure is not available, figures are saved using standard matplotlib

## Example Workflow

```bash
# For Run 093
cd /Users/jklymak/Dropbox/CanyonMix/analysis
python generate_figures.py --runname Slope2D093 --mooringX -55 -45 -35

# Check the generated markdown
cat doc/Slope2D093_figures.md

# Paste the markdown content into your Notes.md file
# The figures are now in analysis/doc/ and ready to use
```

## Troubleshooting

**Problem**: Script fails with data loading errors
- **Solution**: Check that the run data exists in `../results/{runname}/input/`

**Problem**: Layered histogram computation fails
- **Solution**: Use `--skip-layered` flag to skip semi-Lagrangian analysis

**Problem**: Out of memory errors
- **Solution**: Close other applications or run on a machine with more RAM

**Problem**: Figures don't match notebook output
- **Solution**: Verify `mooringX` coordinates match those used in the notebook
