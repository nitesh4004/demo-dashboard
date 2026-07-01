# 🛰️ **PhytoLens** – Geospatial Remote Sensing Analytics Engine

**PhytoLens** is a production-grade remote sensing web application built with a **React (Vite) Frontend** and a **Python FastAPI Backend** leveraging the **Microsoft Planetary Computer (MPC)** STAC API for dynamic satellite data extraction. It enables researchers, GIS engineers, and environmental scientists to process, analyze, and export multi-sensor earth observation data through a premium dark-themed scientific HUD dashboard.

---

## 📋 **Overview & Architecture**

The application is split into two components:
1. **Frontend (`/frontend`)**: A high-fidelity React dashboard styled as a scientific HUD. Pinned with a Leaflet map that supports coordinate acquisitions, base map toggling (Esri Satellite vs OpenStreetMap), and raster layer overlays.
2. **Backend (`/backend`)**: A FastAPI server that queries Microsoft Planetary Computer STAC endpoints, streams and clips Cloud-Optimized GeoTIFFs (COGs) on-the-fly using `rasterio`. The Evapotranspiration tool additionally pulls ERA5-Land meteorology from the **Copernicus Climate Data Store (CDS)**.

**Data sources:** Microsoft Planetary Computer (Sentinel‑1/2, Landsat 8/9, ESA WorldCover, IO LULC, MODIS), AlphaEarth Foundations embeddings, and Copernicus CDS ERA5‑Land (for SEBAL evapotranspiration).

The tools are organized into two groups, selectable from the header:

| Group | Tools |
|-------|-------|
| **Monitoring & Analysis** | Single Scene Scan · Seasonal Trend · LULC Mapping · AI Clustering (AEF) · AI Similarity (AEF) · **Evapotranspiration (SEBAL)** |
| **Disaster Management** | Flood Detection (SAR) · Landslide Susceptibility Map · Deformation Rate Map |

---

## 🎯 **Core Capabilities**

### Monitoring & Analysis

- **🔍 Spectral Monitor** (Single Scene / Seasonal Trend):
  - Optical & Thermal indices: NDVI, GNDVI, NDWI, NDMI, LST (Surface Temperature).
  - Satellites: Sentinel-2 (L2A), Landsat 8/9 (C2 L2), Sentinel-1 (Radar).
  - Dynamic visual stretching (2nd to 98th percentile contrast stretching).
  - Custom algebraic band math expressions (e.g. `(B8 - B4) / (B8 + B4)`).

- **🌿 Evapotranspiration (SEBAL)**:
  - Daily **actual ET (mm/day)** from the SEBAL surface-energy-balance model: `λE = Rn − G0 − H`.
  - Inputs: **Landsat 8/9** C2‑L2 (surface reflectance + thermal ST_B10) from Planetary Computer, plus **ERA5‑Land** overpass meteorology from Copernicus CDS.
  - Both **single‑date** maps and **seasonal time‑series** of mean ET.
  - **FAO‑56 reference ET₀** and implied crop coefficient **Kc = ETa/ET₀** as a validation rail.
  - Scene‑adaptive hot/cold anchor selection (strict thresholds with an NDVI‑quantile fallback) so drier/less‑vegetated scenes still work.
  - **Small ROIs supported**: anchors are calibrated on the surrounding ~13 km and the result is cropped back to the drawn area; overlays render at a minimum display resolution for a smooth, crisply‑clipped map.
  - Requires a Copernicus CDS key — see the **CDS API Key** setup under Quick Start.

- **🗂️ LULC Mapping**: ESA WorldCover (10 m) and Impact Observatory IO‑LULC Annual v02 (10 m) land‑cover classification with per‑class area statistics.

- **🤖 AlphaEarth Foundation AI (AEF)**:
  - **AI Clustering**: Unsupervised segmentation of multi-temporal embeddings into $K$ user-defined clusters to identify crop performance or land cover transitions.
  - **AI Similarity Search**: Compare user-drawn or uploaded multi-geometry queries against target ROIs using 64-dimensional embeddings (cosine similarity).
  - **Local Contrast Mode**: Optional mean-centering of embeddings to rank distinct features accurately across varying or uniform terrain.

### Disaster Management

- **🌊 Flood Detection (SAR)**: Sentinel‑1 GRD VV backscatter change between a pre‑event and post‑event scene, with speckle filtering and a calibration‑offset correction; interactive before/after swipe on the map.
- **⛰️ Landslide Susceptibility Map**: Pre‑computed susceptibility raster with per‑district statistics.
- **📈 Deformation Rate Map**: InSAR Sentinel‑1 line‑of‑sight velocity (mm/yr) composites.

### Shared

- **🗺️ Intuitive Polygon Drawing**: Click-to-close by clicking the starting vertex marker (or within a 15‑pixel tolerance); drawn/uploaded ROIs clip every raster result.
- **💾 Data Export**: Instant raw GeoTIFF exports and transparent PNG maps for web-map overlay; CSV export of statistics.

---

## 🚀 **Quick Start**

### **Prerequisites**
- Python 3.9+ (3.11/3.12 recommended for geospatial wheels)
- Node.js (v18+) & npm

### **Option A — One-command launcher (recommended)**
From the root directory:
```bash
python run.py
```
This installs any missing dependencies, frees the ports, and starts **both** servers:
- **Frontend:** http://localhost:6173  *(open this)*
- **Backend API:** http://127.0.0.1:7000  ·  API docs: http://127.0.0.1:7000/docs

Press `Ctrl+C` once to stop both.

### **Option B — Run each server manually**
```bash
# Backend (from the root directory)
python -m pip install -r backend/requirements.txt
python -m uvicorn backend.app:app --reload --host 127.0.0.1 --port 7000

# Frontend (in a second terminal)
cd frontend && npm install && npm run dev
```

### 🔑 **CDS API Key (for Evapotranspiration)**
The Evapotranspiration (SEBAL) tool fetches ERA5‑Land meteorology from the Copernicus Climate Data Store. Every other tool works without it.

1. Create a free account at https://cds.climate.copernicus.eu and copy your **Personal Access Token** from your profile page.
2. Create a file named **`.cdsapirc`** in your home directory (`C:\Users\<you>\.cdsapirc` on Windows, `~/.cdsapirc` on macOS/Linux):
   ```
   url: https://cds.climate.copernicus.eu/api
   key: <your-personal-access-token>
   ```
   > On Windows, make sure the file is exactly `.cdsapirc` (no `.txt`). Easiest: `printf 'url: https://cds.climate.copernicus.eu/api\nkey: %s\n' "<token>" > ~/.cdsapirc`
3. Accept the **ERA5‑Land licence** once at the [dataset download page](https://cds.climate.copernicus.eu/datasets/reanalysis-era5-land?tab=download#manage-licences) → *Manage licences* → **Accept**. Requests return `403` until this is done.

> ERA5‑Land requests are queued by CDS and can take ~1–5 minutes each, so a single‑date ET map takes a couple of minutes and time‑series is capped at a few scenes.

### **Run Automated Tests**
You can verify the STAC query and raster calculations programmatically:
```bash
python backend/verify.py
```

---

## 📂 **Project Structure**

```
PhytoLens/
├── run.py                 # One-command launcher (starts backend + frontend)
├── backend/
│   ├── app.py             # FastAPI routes (spectral, LULC, AEF, flood, ET, LSM, deformation)
│   ├── pc_handler.py      # STAC query, band extraction, index calculation, PNG/GeoTIFF export
│   ├── sebal.py           # SEBAL evapotranspiration model + ERA5-Land (CDS) access
│   ├── verify.py          # Programmatic test script
│   └── requirements.txt   # Python backend dependencies (adds cdsapi, xarray, netCDF4 for ET)
├── frontend/
│   ├── src/
│   │   ├── App.jsx        # Main React dashboard layout, Leaflet maps, and widgets
│   │   ├── index.css      # Core styles (Scientific HUD theme, custom inputs)
│   │   └── main.jsx       # Vite app mounting
│   ├── index.html         # HTML entry point (SEO configured)
│   └── package.json       # React dependencies (Leaflet, Lucide Icons)
└── README.md              # Documentation
```

---

## 🎨 **Visual Design Theme**

- **Dark HUD Cyberpunk Aesthetic**: High-contrast, glowing neon color indicators (Cyan for UI, Green for Active Uplink, Red/Amber for Hazard warnings).
- **Glassmorphic Cards**: Sleek panels with blurred backdrops and subtle borders.
- **Interactive Map**: Quick basemap switching between high-res satellite telemetry and standard streets layout, with coordinate sync overlays.

---

**Made with ❤️ by Nitesh Kumar | GIS Engineer**
