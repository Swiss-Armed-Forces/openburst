# 
## Compilation with Splat!

### Download SRTM files:
* from: [viewfinderpanoramas.org](http://www.viewfinderpanoramas.org/Coverage%20map%20viewfinderpanoramas_org3.htm)
* as described in: [onetransistor.eu](https://www.onetransistor.eu/2016/07/splat-rf-compile-setup.html)

### Convert SRTM files in batch to sdf files
* as described in: [onetransistor.eu](https://www.onetransistor.eu/2016/07/splat-rf-compile-setup.html)
* for converting the downloaded hgt files to sdf files using the bash script as described in the link above, splat! installation is necessary (sudo apt install splat)

### configure source/DEM/SPLAT_RADIOPROP/splatBurst.h:
 
* replace SDF DEM files path in radterrain/SPLAT_RADIOPROP/splatBurst.h with the correct path to SDF files folder as in:
```
char burst_dem_path[] = "~/Downloads/SRTM3_Eurasia_Data/SDF_Files/";
```
(make sure to have the forward slash "/" at the end of the pathname as above)

* set std-params (a high number as e.g. below so that long distance propagation losses can be calculated):
 
```
#define MAXPAGES = 144 
```
* set HD mode 1 because we use 1arc sec SRTM data with 30m resolution:

```
#define HD_MODE 1
```
   
### set DEM files path in constants/splatconsants.py
```
DEM_FILES_PATH = "~/Downloads/SRTM3_Eurasia_Data/SDF_Files" 
```
(make sure NOT to have the forward slash "/" at the end of the pathname as above)

### build splat-hd 
* in directory radterrain/SPLAT_RADIOPROP (radterrain.py uses ./splat-hd to compute simple point-to-point LoS and propagation)
```
./build splat
```

### build splat 
* edit file radterrain/SPLAT_RADIOPROP/buildBurst to fit your python and boost versions (e.g. for python3.10 in the following lines):
```
PYTHON_VERSION="3.10" 
PYTHON_INC="/usr/include/python3.10" 
BOOST_LIB_FILE="boost_python310"
```
and "-lpython3.10" in the following line:

```
mpiCC -O2 -s -fomit-frame-pointer -ffast-math -pipe -fPIC -march=$cpu $model -I$PYTHON_INC -I$BOOST_INC itwom3.0.cpp splatBurst.cpp -lrt -lboost_system -lpython3.10 -lm -lbz2 -shared -Wl,-soname,$@ -Wl,-rpath,$BOOST_LIB_LOCATION -L$BOOST_LIB_LOCATION -l$BOOST_LIB_FILE  -o libsplathd.so
```   
* run radterrain/SPLAT_RADIOPROP/buildBurst to generate shared library "libsplathd.so":
```
./buildBurst splat_shared_lib
```

### build with mpi 
* edit the build_mpi file to your python, boost versions and installation locations (variables and linker flags) as in lines:
```
PYTHON_VERSION="3.10" 
PYTHON_INC="/usr/include/python3.10" 
BOOST_LIB_FILE="boost_python310" # this means libboost_python310.so should be in the BOOST_LIB_LOCATION #"see build_mpi" 
```
and,  "-lboost_python310" and "-lpython3.10" in lines:
```
mpicxx -O2 -s -fomit-frame-pointer -ffast-math -pipe -march=$cpu $model -I$PYTHON_INC -I$BOOST_INC mpi_los_and_loss.cpp -L./ -lsplathd -lboost_python310 -lboost_system -lpython3.10  -lboost_mpi  -lrt -ldl  -lm -lbz2 -Wl,-soname,$@ -Wl,-rpath,$BOOST_LIB_LOCATION -L$BOOST_LIB_LOCATION -l$BOOST_LIB_FILE  -o mpi_los_and_loss

mpicxx -O2 -s -fomit-frame-pointer -ffast-math -pipe -march=$cpu $model -I$PYTHON_INC -I$BOOST_INC mpi_radial_los_and_loss.cpp -L./ -lsplathd -lboost_python310 -lrt -lboost_system -lpython3.10  -lboost_mpi  -lrt -ldl  -lm -lbz2 -Wl,-soname,$@ -Wl,-rpath,$BOOST_LIB_LOCATION -L$BOOST_LIB_LOCATION -l$BOOST_LIB_FILE  -o mpi_radial_los_and_loss
```

* build twice by running source/DEM/SPLAT_RADIOPROP/build_mpi for parallel computing as grid and as polar: 
```
./build_mpi los_and_loss
```
```
./build_mpi radial_los_and_loss
```

### check compilation
* ensure that the following object files are generated in the folder source/DEM/SPLAT_RADIOPROP/: libsplathd.so, splat, splat-hd, mpi_radial_los_and_loss, mpi_los_and_loss
    
### Notes

* in splatBurst.cpp, the following is the bottelneck for memory allocation...we need one chunk: for MAXPAGES=200 this would be more than 5 Giga!
    ```
    totalDEMsize = 2 * IPPD * IPPD * MAXPAGES; // dem[MAXPAGES].data[IPPD][IPPD], short has size 2 Bytes
    ```

* to change the PROP Loss model from "Longley rice" to "ITWOM" see the struct prop_site in splat.cpp and set the model there.

* Distance function in splat.cpp: distance between the sites in original splat is the great circle distance, meaning antenna height or flight height is not taken into account (test the above with two different antenna heights and look at the result). A new function for distance considering elevation was created: Distance_including_ELevation.

* free_space_loss in Splat!: is the free_space loss between the two sites on earths surface, meaning antenna height (=flight height is not taken into account). Therefore, openburst uses the above new distance function as an input for computing free_space_loss

* use -gc switch for ground clutter (this has not been tested with openburst)




