"""This module defines project-level constants for using splat! propgations model."""

# reference: https://www.qsl.net/kd2bd/splat.pdf

DIEL_CONST = 13.0 # Earth Dielectric Constant (Relative permittivity)
EARTH_COND = 0.002 # Earth Conductivity (Siemens per meter)
AT_BEND = 301.00 # Atmospheric Bending Constant (N-units)
RADIO_CLIMATE = 5.0 # Radio Climate (5 = Continental Temperate)
POL = 0.0 # Polarization (0 = Horizontal, 1 = Vertical)
GROUND_CLUTTER = 0.0 # ground clutter in feet
OITM = 0 # propagation model: 0 = IT_WOM, 1= longley_rice
FRAC_OF_SITU = 0.5 # Fraction of situations (50% of locations)
FRAC_OF_TIME = 0.9 # Fraction of time (90% of the time)


# storage folder of the downloaded DEM files
DEM_FILES_PATH = "/home/red3/Downloads/SRTM3_Eurasia_Data/SDF_Files" 
 