
#

## Installation

* openBURST was installed and tested on an Intel 12th Gen processor with 12 cores and 32GB memory, Ubuntu 20 and 22 LTS 64-bit installations and python3.8 and python3.10. 
* We recommend similar number of CPU cores, memory, Linux distributions and python versions. Processor and memory intensive tasks include coverage and propagation loss computation of sensors.
* pgadmin4 (administration and development platform for PostgreSQL) seems to need python3.8 installed.

### Install system requirements 

* add the deadsnakes repository for python3.10 installation and your packages are upto date:
```
sudo add-apt-repository ppa:deadsnakes/ppa
sudo apt-get update
sudo apt-get upgrade
```
* from root folder:

check file requirements_system.txt to adapt to your python version (python3.10 is currently used)

```
sudo xargs -a requirements_system.txt -l1 apt install -y
```

### Compile Boost

Openburst makes use of boost for parallel processing using mpi and for python-C++ integration. Install boost using: [boost_install](INSTALL_BOOST.md)

### Compile Splat!

Openburst uses the Splat! library for EM wave propagation loss computations. Openburst extends Splat! code with Boost and MPI libraries to parallelize the task on the available CPUs. Shared memory is used for sharing data between the parallel processes. Please note that Splat! code was extended for openBURST and therefore compilation is to be followed as instructed here: [radio_prop](SPLAT_BURST_BOOST_README.md). Installing Splat! with "sudo apt install splat" is not sufficient.


### openburst Installation

* we strongly suggest the usage of a python virtual environment (see https://docs.python.org/3/tutorial/venv.html)
e.g.:
```
python3.10 -m venv openburst-venv
source openburst-venv/bin/activate
```

* we use the pyproject.toml to build and install openburst and its dependencies. To build package from root folder run (e.g. for python3.10):


* install openburst without building:

```
pip install -e .
```

* check if and where openburst is installed: 

```
pip show openburst
```

* to uninstall openburst run:

```
pip uninstall openburst
```


## Setup 

### Octave

* SET OCTAVE_EXECUTABLE Variable to octave-cli (e.g. in .bashrc)
```
export OCTAVE_EXECUTABLE=/usr/bin/octave-cli
```
### create and adapt openburst_config.py

* in constants/ folder copy openburst_config_local.py to a new file openburst_config.py and replace all required user input values. 


### postgreSQL Datenbank

For setting up your postgresql DB for openburst see:
[postgresql](POSTGRESQL_README.md)

### Port accesses

* allow all LAN connected clients to access port 8888 over tcp (for http access of clients)

## Testing

### Run Tests

* run tests (add flag -s for showing print outputs of test):

```
pytest --pyargs openburst
```
