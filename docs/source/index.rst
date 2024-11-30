.. openburst documentation master file, created by
   sphinx-quickstart on Thu Jun  6 06:58:41 2024.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to openBURST's documentation!
=====================================

.. figure:: /images/openburst_pcl.png
   :scale: 100 %
   :align: center
   :alt: pcl coverage example
..
   Sample sensor coverage and terrain backdrop

openBURST (on [GitHub](https://github.com/Swiss-Armed-Forces/openburst) and [JOSS](https://joss.theoj.org/papers/10.21105/joss.07052)) is intended to provide the air surveillance sensor community with a framework 
for the development and testing of sensor coverage and real-time target detection analysis.  

openBURST focuses on the overall performance assessment of a sensor network. Besides static coverage diagram computations, 
openBURST facilitates real-time computation of sensor detection for replayed air pictures. This allows the statistical 
performance analysis of air picture generation in a given scenario. By providing a flexible and extendable framework to model 
and simulate active, passive, monostatic and multistatic sensors, it intends to support optimization efforts of 
sensor portfolios for air surveillance.  

openBURST is under active development [on GitHub](https://github.com/Swiss-Armed-Forces/openburst) and welcomes feedback and contributions.

.. toctree::
   :maxdepth: 1
   :titlesonly:
   :caption: Introduction:

   README_RTD.md

.. toctree::
   :hidden: 
   
   INSTALL_BOOST.md
   SPLAT_BURST_BOOST_README.md
   POSTGRESQL_README.md
   INSTALL_README.md
   REPLAY_README.md
   SENSOR_CONTROL_README.md
   PCL_Tx_Antennas_README.md
   LOGGING_README.md

..
   Installation, Setup, Testing
   =============================
   .. toctree::
      :maxdepth: 2

      INSTALL_README.md

   Server Information 
   ===================
   .. toctree::
      :maxdepth: 2

      REPLAY_README.md
      SENSOR_CONTROL_README.md
      PCL_Tx_Antennas_README.md
      LOGGING_README.md

.. toctree::
   :maxdepth: 1
   :titlesonly:
   :caption: Framework:

   analytics_modules
   detection_modules
   function_modules
   geoplot_modules
   pcl_modules
   pet_modules 
   radterrain_modules
   replay_modules 
   sensorcontrol_modules
   webserver_modules
   types_modules

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

..
   .. figure:: /images/openburst_splat.png
      :scale: 100 %
      :alt: sample propagation

      Sample wave propagation modelling results (integrating `Splat!`_).
   .. _Splat!: https://www.qsl.net/kd2bd/splat.html


