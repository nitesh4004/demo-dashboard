

import warnings
warnings.filterwarnings("ignore")

import json  # noqa: F401  (kept for parity with the notebook; ROI is read via geopandas)
import numpy as np
import geopandas as gpd
import matplotlib.pyplot as plt

import planetary_computer as pc
from pystac_client import Client
import rasterio
from rasterio.vrt import WarpedVRT
from rasterio.windows import from_bounds
from rasterio.enums import Resampling

# ---------------------------------------------------------------------------
# Configuration  (the 'sentinel-1-grd' collection is open — no PC key required)
# ---------------------------------------------------------------------------
AOI_PATH = "hadgaon.geojson"
DST_CRS = "EPSG:32643"   # UTM 43N (metres)
RES = 10                 # output pixel size (m)

# Sentinel-1 filters (match the tutorial: VV, IW; descending = tracks that imaged the event)
ORBIT_STATE = "descending"
RELATIVE_ORBIT = None    # None = all descending scenes (as the tutorial does); or set 165 / 63

# Pre-flood vs flood/post composite windows (event reference date: 30 Sep 2025)
PRE_START, PRE_END = "2025-09-01", "2025-09-26"
POST_START, POST_END = "2025-09-27", "2025-10-12"

FLOOD_DB_THRESHOLD = 3.0  # backscatter drop (dB) flagged as candidate new water

STAC_URL = "https://planetarycomputer.microsoft.com/api/stac/v1"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def load_roi_grid():
    """Read the ROI and define the fixed UTM output grid every scene is warped onto."""
    aoi = gpd.read_file(AOI_PATH)
    minx, miny, maxx, maxy = aoi.to_crs(DST_CRS).total_bounds
    W = int(round((maxx - minx) / RES))
    H = int(round((maxy - miny) / RES))
    bbox = list(aoi.to_crs(4326).total_bounds)   # lon/lat for the STAC search
    extent = [minx, maxx, miny, maxy]            # for plotting
    print(f"Output grid: {H} x {W} px at {RES} m  ({DST_CRS})")
    print("AOI bbox (lon/lat):", [round(v, 4) for v in bbox])
    return (minx, miny, maxx, maxy), (H, W), bbox, extent


def search_scenes(catalog, bbox):
    """Find VV/IW/descending GRD scenes over the ROI and split into pre/post windows."""
    query = {"sar:instrument_mode": {"eq": "IW"}, "sat:orbit_state": {"eq": ORBIT_STATE}}
    if RELATIVE_ORBIT is not None:
        query["sat:relative_orbit"] = {"eq": RELATIVE_ORBIT}

    items = list(catalog.search(
        collections=["sentinel-1-grd"],
        bbox=bbox,
        datetime=f"{PRE_START}/{POST_END}",
        query=query,
    ).items())
    items.sort(key=lambda it: it.properties["datetime"])

    print(f"\n{len(items)} {ORBIT_STATE} IW GRD scenes over the ROI:")
    for it in items:
        p = it.properties
        print(f"  {p['datetime'][:10]}  rel-orbit {p.get('sat:relative_orbit')}  {p.get('sar:polarizations')}")

    def day(it):
        return it.properties["datetime"][:10]

    pre_items = [it for it in items if PRE_START <= day(it) <= PRE_END]
    post_items = [it for it in items if POST_START <= day(it) <= POST_END]
    print("\nPre-flood window :", [day(it) for it in pre_items])
    print("Flood/post window:", [day(it) for it in post_items])
    assert pre_items and post_items, "Need at least one scene in each window."
    return pre_items, post_items


def load_grd_vv_db(item, bounds, shape):
    """Warp a Sentinel-1 GRD VV scene to the ROI grid and return backscatter in dB."""
    minx, miny, maxx, maxy = bounds
    H, W = shape
    with rasterio.open(item.assets["vv"].href) as src:
        gcps, gcp_crs = src.gcps
        with WarpedVRT(src, src_crs=gcp_crs, crs=DST_CRS,
                       resampling=Resampling.bilinear) as vrt:
            win = from_bounds(minx, miny, maxx, maxy, vrt.transform)
            dn = vrt.read(1, window=win, out_shape=(H, W),
                          resampling=Resampling.bilinear).astype("float64")
    dn[dn <= 0] = np.nan                 # 0 = no data
    return 20.0 * np.log10(dn)           # amplitude DN -> dB (relative)


def composite(items, bounds, shape):
    """Per-pixel minimum-VV composite (darkest = wettest; also suppresses speckle)."""
    return np.nanmin(np.stack([load_grd_vv_db(it, bounds, shape) for it in items]), axis=0)


def plot_before_after(before, after, flood, valid, extent, lo, hi):
    """Three-panel before / after / difference figure (saved to flood_hadgaon_pc.png)."""
    fig, ax = plt.subplots(1, 3, figsize=(15, 5))

    im0 = ax[0].imshow(before, cmap="gray", vmin=lo, vmax=hi, extent=extent, origin="upper")
    ax[0].set_title(f"Before VV (dB)\n{PRE_START} .. {PRE_END}")
    plt.colorbar(im0, ax=ax[0], fraction=0.046)

    im1 = ax[1].imshow(after, cmap="gray", vmin=lo, vmax=hi, extent=extent, origin="upper")
    ax[1].set_title(f"After VV (dB)\n{POST_START} .. {POST_END}")
    plt.colorbar(im1, ax=ax[1], fraction=0.046)

    im2 = ax[2].imshow(np.where(valid, flood, np.nan), cmap="Blues", vmin=0, vmax=6,
                       extent=extent, origin="upper")
    ax[2].set_title("flood = before - after\n(>0 = darker/wetter)")
    plt.colorbar(im2, ax=ax[2], fraction=0.046, label="dB")

    for a in ax:
        a.set_xlabel("Easting (m)")
        a.set_ylabel("Northing (m)")
    plt.tight_layout()
    plt.savefig("flood_hadgaon_pc.png", dpi=200, bbox_inches="tight")
    plt.show()


def plot_mask(before, mask, area_km2, extent, lo, hi):
    """Candidate-flood mask overlaid on the pre-flood backscatter."""
    fig, ax = plt.subplots(figsize=(6, 6))
    ax.imshow(before, cmap="gray", vmin=lo, vmax=hi, extent=extent, origin="upper")
    ax.imshow(np.ma.masked_where(~mask, mask), cmap="autumn", vmin=0, vmax=1,
              extent=extent, origin="upper", alpha=0.9)
    ax.set_title(f"Candidate flood (red): {area_km2:.2f} km^2")
    ax.set_xlabel("Easting (m)")
    ax.set_ylabel("Northing (m)")
    plt.tight_layout()
    plt.show()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    bounds, shape, bbox, extent = load_roi_grid()

    catalog = Client.open(STAC_URL, modifier=pc.sign_inplace)
    pre_items, post_items = search_scenes(catalog, bbox)

    # Composites & flood difference
    before = composite(pre_items, bounds, shape)
    after = composite(post_items, bounds, shape)
    flood = before - after                      # positive where it got darker (candidate new water)
    valid = np.isfinite(before) & np.isfinite(after)

    print(f"\nbefore  median dB: {np.nanmedian(before):.1f}")
    print(f"after   median dB: {np.nanmedian(after):.1f}")
    print(f"flood   max dB    : {np.nanmax(np.where(valid, flood, np.nan)):.1f}")

    # Visualise
    lo, hi = np.nanpercentile(np.concatenate([before[valid], after[valid]]), [2, 98])
    plot_before_after(before, after, flood, valid, extent, lo, hi)

    # Threshold to a flood mask & area
    mask = (flood > FLOOD_DB_THRESHOLD) & valid
    area_km2 = int(mask.sum()) * (RES * RES) / 1e6
    pct = 100 * mask.sum() / valid.sum()
    print(f"\nCandidate flood (> {FLOOD_DB_THRESHOLD} dB drop): {area_km2:.2f} km^2  ({pct:.2f}% of ROI)")
    plot_mask(before, mask, area_km2, extent, lo, hi)


if __name__ == "__main__":
    main()
