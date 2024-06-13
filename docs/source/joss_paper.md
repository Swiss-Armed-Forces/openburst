---
title: 'openBURST: A software framework for sensor coverage and real-time target detection analysis.'
tags:
  - C++
  - Python
  - air surveillance
  - passive radar
  - active radar
  - radar coverage
  - real-time radar detection

authors:
  - name: Zenon Mathews
    corresponding: true 
    equal-contrib: true
    affiliation: "1" 
  - name: Romain Chessex
    equal-contrib: false 
    affiliation: 1

affiliations:
 - name: Data Science and Modelling, Swiss Armed Forces Staff, Swiss Army, Switzerland
   index: 1
date: 13 June 2024
bibliography: paper.bib

---

# Summary

`openBURST` is intended to provide the air surveillance sensor community with a framework for the development and testing of sensor coverage and real-time target detection analysis. `openBURST` focuses on the overall performance assessment of a sensor network. Besides static coverage diagram computations, `openBURST` facilitates real-time computation of sensor detections for simulated targets. This allows the statistical performance analysis of air picture generation in a given scenario. By providing a flexible and extendable framework to model and simulate active, passive, monostatic and multistatic sensors, it intends to enables the implementation of optimization approaches in sensor portfolios for air surveillance.


# Statement of need

`openBURT` is a software framework to design, deploy and test active/passive radar system networks for detecting simulated or recorded real world air traffic. `openBURST` consists of decoupled software modules that can be replaced, extended or deployed independently for air surveillance sensor coverage and real-time detection computations. `openBURST` uses real-time communication between the distributed modules of the simulation framework, allowing for concurrent updates of target movements and sensor detections. Currently, `openBURST` supports coverage computation and real-time simulation of active radar and passive radar sensor detections for FM transmitters. Extensions with digital transmitters for passive radar and passive emitter tracking sensors are currently planned. `openBURST` extends the RF signal propagation, loss and terrain analysis tool [@{https://www.qsl.net/kd2bd/splat.html}, Splat!] for EM signal propagation computations with multi-core parallel processing and graphical user interfacing. `openBURST` uses openstreetmap [@{https://openstreetmap.org}, data] with [@{https://openlayers.org}, openlayers] for the interactive map. Terrain digital elevation data provided by [@{https://www.usgs.gov/coastal-changes-and-impacts/gmted2010}, GMTED10] is used for Line-of-Sight and propagation loss computations. `openBURST`implements a client-server architecture, letting browser based clients remain data and implementation agnostic. 

On contrary to a number of existing open source tools for detailed simulations of single sensors, `openBURST` provides a single extendable framework for diverse sensor and target simulations. Also, by parallelizing computationally intensive steps and by providing a user-firendly brower based interface, `openBURST` considerably simplifies sensor network and target simulations. In summary, `openBURST` facilitates new exciting scientific explorations of sensor network/fusion performance studies and sensor network performance benchmarking. During its development, `openBURST` has been used in a number of studies for passive radar location optimization and learning resource allocation in active/passive sensor networks [@Mathews:2022; @Mathews:2015; @Mousel:2017]. 

# Acknowledgements

We thankfully acknowledge the support from the the Swiss Armed Forces Staff for opensourcing `openBURST`. We also thank our colleagues at the Swiss Department of Defense, especially from the Swiss Air Force and  armasuisse Science & Technology. We acknowledge the early work for passive radar coverage computation implemented by the master thesis [@Mousel:2017].

# References