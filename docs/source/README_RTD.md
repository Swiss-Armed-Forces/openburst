
# Name Origins

BURST is an acronym for "Base Units Readiness Simulation Tool". Burst 1969mASL is a humble yet stunning mountain peak in the Emmentaler Alps of canton Berne, CHE. A Burst signal in communications engineering is a finite number of oscillations of a specific frequency. Bursting, or burst firing, is an extreme diverse and general phenomenon of activity pattern of biological neurons. The opensourced version of the original BURST tool was named openBURST.

# Description

openBURST provides a framework consisting of decoupled software modules that can be replaced, extended or deployed independently for air surveillance sensor coverage and real-time detection computations. openBURST uses real-time communication between the distributed modules of the simulation framework, allowing for concurrent updates of target movements and sensor detections. Currently, openBURST supports coverage computation and real-time simulation of active radar and passive radar sensor detections for FM transmitters. openBURST extends the RF signal propagation, loss, and terrain analysis tool [Splat!](https://www.qsl.net/kd2bd/splat.html) for EM signal propagation computations with multi-core parallel processing and graphical user interfacing. openBURST uses openstreetmap [data](https://openstreetmap.org) with [openlayers](https://openlayers.org) for the interactive map. Terrain digital elevation data provided by [GMTED10](https://www.usgs.gov/coastal-changes-and-impacts/gmted2010) is used for Line-of-Sight and propagation loss computations. openBURST implements a client-server architecture, letting browser based clients remain data and implementation agnostic.

# Getting Started

## Dependencies

* see pyproject.toml and requirements_system.txt

## Installing and Testing

* see [INSTALL_README](./INSTALL_README.md)


## Server Module Infos

* [PCL Transmitter](./PCL_Tx_Antennas_README.md)
* [Logging](./LOGGING_README.md)
* [Target Sim (Replay)](./REPLAY_README.md)
* [Sensor Control](./SENSOR_CONTROL_README.md)

## Executing program

* after installation, please follow [running openBurst](./RUNNING_OPENBURST.md) to check the core functionalities of openBURST.



## Help

* please contact the authors for any advise for common problems or issues

# Authors

Zenon Mathews, Swiss Armed Forces Staff, Defense Portfolio, Data Science and Modelling  
zenon.mathews -at- vtg.admin.ch

Romain Chessex, Swiss Armed Forces Staff, Defense Portfolio, Data Science and Modelling  
romain.chessex -at- vtg.admin.ch

# Version History

* 1.0

# License

openBURST is licensed under GNU General Public License Version 3. See [LICENSE](../../LICENSE) for details.

openBURST explicitly disclaims any warranty for and liability [as in GPLv3 section 16](https://www.gnu.org/licenses/gpl-3.0.en.html) arising from using the program. In no event will the authors of openBURST be liable to you for damages, including any general, special, incidental or consequential damages, arising out of the use or inability to use the program (including but not limited to loss of data or data being rendered inaccurate or losses sustained by you or third parties or a failure of the program to operate with any other programs), even if such holder or other party has been advised of the possibility of such damages. 

openBURST extended the source of the following library licensed as shown below: 

* [Splat!: GPLv2](https://www.qsl.net/kd2bd/splat.html)

openBURST uses the following libraries as source code (with the respective licenses shown below): 

* [jquery: MIT](https://jquery.com/license/) 
* [Openlayers: BSD2](https://raw.githubusercontent.com/openlayers/ol3/master/LICENSE.md) 
* [bootstrap: MIT](https://getbootstrap.com/) 
* [plotly: MIT](https://plotly.com/javascript/is-plotly-free/)


# Acknowledgments

We thankfully acknowledge the support from the the Swiss Armed Forces Staff for opensourcing openBURST. We also thank our colleagues at the Swiss Department of Defense, especially from the Swiss Air Force but also from armasuisse Science & Technology. openBURST is deeply indebted to Luca Quiriconi, Swiss Air Force, for theory, implementation and testing support during the very first years of openBURST. An early version of passive radar coverage computation was implemented by Pol Mousel for his master thesis:
```
Passive Radar Coverage Optimization, (Mousel P.) ETH Zurich Master Thesis April 2017
```
We also thank the authors of publications that used earlier versions of openBURST:
```
[1] Multi-static passive receiver location optimization in alpine terrain using a parallelized genetic algorithm, (Mathews, Quiriconi, Weber) IEEE Radar Conference 2015

[2] Learning Resource Allocation in Active-Passive Radar Sensor Networks, (Mathews, Quiriconi, Weber), Frontiers in Signal Processing 2022
```
We also thank the editor, [Daniel S. Katz](https://github.com/danielskatz) and the reviewers [Hasan Tahir Abbas](https://github.com/hasantahir) and [Rohit Mendadhala](https://github.com/rvg296) of the openBURST [JOSS paper](https://joss.theoj.org/papers/10.21105/joss.07052). The JOSS review process has helped remarkably to improve openBURST documentation, installation process etc. 
```
[3] openBURST: Real-time air surveillance simulation and analysis for active and passive sensors, (Mathews, Chessex), Journal of Open Source Software, 2024, 9(103), 7052, https://doi.org/10.21105/joss.07052 
```