"""This module defines project-level constants for using splat! propgations model."""
import os

# reference: https://www.qsl.net/kd2bd/splat.pdf

DIEL_CONST = float(os.environ.get("DIEL_CONST", 13.0)) # Earth Dielectric Constant (Relative permittivity)
EARTH_COND = float(os.environ.get("EARTH_COND", 0.002)) # Earth Conductivity (Siemens per meter)
AT_BEND = float(os.environ.get("AT_BEND", 301.00)) # Atmospheric Bending Constant (N-units)
RADIO_CLIMATE = float(os.environ.get("RADIO_CLIMATE", 5.0)) # Radio Climate (5 = Continental Temperate)
POL = float(os.environ.get("POL", 0.0)) # Polarization (0 = Horizontal, 1 = Vertical)
GROUND_CLUTTER = float(os.environ.get("GROUND_CLUTTER", 0.0)) # ground clutter in feet
OITM = int(os.environ.get("OITM", 0)) # propagation model: 0 = IT_WOM, 1= longley_rice
FRAC_OF_SITU = float(os.environ.get("FRAC_OF_SITU", 0.5)) # Fraction of situations (50% of locations)
FRAC_OF_TIME = float(os.environ.get("FRAC_OF_TIME", 0.9)) # Fraction of time (90% of the time)


# storage folder of the downloaded DEM files
DEM_FILES_PATH = os.environ.get("DEM_FILES_PATH", "/SRTM")
