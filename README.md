# Summary

openBURST is intended to provide the air surveillance sensor community with a framework for the development and testing of sensor coverage and real-time target detection analysis.

openBURST focuses on the overall performance assessment of a sensor network. Besides static coverage diagram computations, openBURST facilitates real-time computation of sensor detection for replayed air pictures. This allows the statistical performance analysis of air picture generation in a given scenario. By providing a flexible and extendable framework to model and simulate active, passive, monostatic and multistatic sensors, it intends to support optimization efforts of sensor portfolios for air surveillance.

openBURST provides a framework consisting of decoupled software modules that can be replaced, extended or deployed independently for air surveillance sensor coverage and real-time detection computations. openBURST uses real-time communication between the distributed modules of the simulation framework, allowing for concurrent updates of target movements and sensor detections. Currently, openBURST supports coverage computation and real-time simulation of active radar and passive radar sensor detections for FM transmitters. openBURST extends the RF signal propagation, loss, and terrain analysis tool [Splat!](https://www.qsl.net/kd2bd/splat.html) for EM signal propagation computations with multi-core parallel processing and graphical user interfacing. openBURST uses openstreetmap [data](https://openstreetmap.org) with [openlayers](https://openlayers.org) for the interactive map. Terrain digital elevation data provided by [GMTED10](https://www.usgs.gov/coastal-changes-and-impacts/gmted2010) is used for Line-of-Sight and propagation loss computations. openBURST implements a client-server architecture, letting browser based clients remain data and implementation agnostic.

openBURST is under active development and welcomes feedback and contributions.

# Documentation

[see openBURST read-the-docs](https://openburst.readthedocs.io/en/latest/)

## Help

* please contact the authors for any advise for common problems or issues

# Authors

Zenon Mathews, Swiss Armed Forces Staff, Defense Portfolio, Data Science and Modelling  
zenon.mathews -at- vtg.admin.ch

Romain Chessex, Swiss Armed Forces Staff, Defense Portfolio, Data Science and Modelling  
romain.chessex -at- vtg.admin.ch

# Version History

* 1.0

# Acknowledgments

We thankfully acknowledge the support from the the Swiss Armed Forces Staff for opensourcing openBURST. We also thank our colleagues at the Swiss Department of Defense, especially from the Swiss Air Force but also from armasuisse Science & Technology. openBURST is deeply indebted to Luca Quiriconi, Swiss Air Force, for theory, implementation and testing support during the very first years of openBURST. An early version of passive radar coverage computation was implemented by Pol Mousel for his master thesis:
```
Passive Radar Coverage Optimization, (Mousel P.) ETH Zurich Master Thesis April 2017
```
We thank the authors of publications that used earlier versions of openBURST:
```
[1] Multi-static passive receiver location optimization in alpine terrain using a parallelized genetic algorithm, (Mathews, Quiriconi, Weber) IEEE Radar Conference 2015

[2] Learning Resource Allocation in Active-Passive Radar Sensor Networks, (Mathews, Quiriconi, Weber), Frontiers in Signal Processing 2022
```
We also thank the editor, [Daniel S. Katz](https://github.com/danielskatz) and the reviewers [Hasan Tahir Abbas](https://github.com/hasantahir) and [Rohit Mendadhala](https://github.com/rvg296) of the openBURST [JOSS paper](https://joss.theoj.org/papers/10.21105/joss.07052). The JOSS review process has helped remarkably to improve openBURST documentation, installation process etc. 
```
[3] openBURST: Real-time air surveillance simulation and analysis for active and passive sensors, (Mathews, Chessex), Journal of Open Source Software, 2024, 9(103), 7052, https://doi.org/10.21105/joss.07052 
```