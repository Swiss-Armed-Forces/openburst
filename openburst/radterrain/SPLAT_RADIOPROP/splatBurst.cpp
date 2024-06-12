/**************************************************************************** \
* 	   derived from SPLAT!: An RF Signal Path Loss And Terrain Analysis Tool *
*       to parallelize the computation and to enable usage from Python       *
******************************************************************************
*	       												     			     *
*			  Last update: 22-March-2024								     *
******************************************************************************

******************************************************************************
*                                                                            *
*  This program is free software; you can redistribute it and/or modify it   *
*  under the terms of the GNU General Public License as published by the     *
*  Free Software Foundation; either version 2 of the License or any later    *
*  version.								     *
* 									     *
*  This program is distributed in the hope that it will useful, but WITHOUT  *
*  ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or     *
*  FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License     *
*  for more details.							                             *
*									                                         *
\****************************************************************************/


#include "splatBurst.h"


std::vector<float> GetLosAndLossReturn::readLosMatrix(){
  return this->los;
}
std::vector<float> GetLosAndLossReturn::readLossMatrix(){
  return this->loss;
}
std::vector<float> GetLosAndLossReturn::readFreeLossMatrix(){
  return this->free_loss;
}
std::vector<float> GetLosAndLossReturn::readDistMatrix(){
  return this->dist;
}

prop_site::prop_site()   // define default constructor
{
 }




void prop_site::initialize_light( float diel_const, float earth_cond, float at_bend, float radio_climate,float pol,float frac_of_situ,float frac_of_time,float ground_clutter){
    this->diel_const = diel_const;
    this->earth_cond = earth_cond;
    this->at_bend=at_bend;
    this->radio_climate=radio_climate;
    this->pol=pol;
    this->frac_of_situ = frac_of_situ;
    this->frac_of_time=frac_of_time;
    this->ground_clutter=ground_clutter;
    this->oitm = 1;// propagation model: 0 = IT_WOM, 1= longley_rice
 
    ippd=IPPD;		/* pixels per degree (integer) */
    ppd=(double)ippd;	/* pixels per degree (double)  */
    dpp=1.0/ppd;		/* degrees per pixel */
    mpi=ippd-1;		/* maximum pixel index per degree */

        
    // for reading shared mem DEM attributes in GetElevation 
    attrs_region_p_site = bi::mapped_region{shm_attrs_read, bi::read_only};;
    attrs_pMem_read_p_site = attrs_region_p_site.get_address();
    attrs_arr_read_p_site = static_cast<int*>(attrs_pMem_read_p_site);

    // for reading shred mem DEM in GetElevation 
    dem_region_read = bi::mapped_region{shm_read, bi::read_only}; 
    dem_pMem_read = dem_region_read.get_address(); 
    dem_arr_read = static_cast<short*>(dem_pMem_read); 
   
}

void prop_site::initialize_heavy(int min_lat, int max_lat, int min_lon, int max_lon, float diel_const, float earth_cond, float at_bend, float radio_climate,float pol,float frac_of_situ,float frac_of_time,float ground_clutter){
    this->diel_const = diel_const;
    this->earth_cond = earth_cond;
    this->at_bend=at_bend;
    this->radio_climate=radio_climate;
    this->pol=pol;
    this->frac_of_situ = frac_of_situ;
    this->frac_of_time=frac_of_time;
    this->ground_clutter=ground_clutter;
    this->oitm = 1;// propagation model: 0 = IT_WOM, 1= longley_rice

    
 
    ippd=IPPD;		/* pixels per degree (integer) */
    ppd=(double)ippd;	/* pixels per degree (double)  */
    dpp=1.0/ppd;		/* degrees per pixel */
    mpi=ippd-1;		/* maximum pixel index per degree */


    

    
    for (int x=0; x<MAXPAGES; x++)
      {
	dem[x].min_el=32768;
	dem[x].max_el=-32768;
	dem[x].min_north=90;
	dem[x].max_north=-90;
	dem[x].min_west=360;
	dem[x].max_west=-1;

      }

    strncpy(sdf_path, burst_dem_path, 253);
    
    
   
    // get total needed size of shared memory
    unsigned int totalDEMsize;
    totalDEMsize = 0;

    // THIS IS THE BOTTLENECK for memory allocation...we need one chunk: for MAXPAGES=200 this would be more than 5 Giga..NOT POSIIBLE
    totalDEMsize = 2 * IPPD * IPPD * MAXPAGES; // dem[MAXPAGES].data[IPPD][IPPD], short has size 2 Bytes
    fprintf(stdout, ":::::::: total DEM size = %u \n", totalDEMsize);//, IPPD, MAXPAGES); 

    /////////////// get shared mem for dem ////////////
    try{
      shm.truncate(totalDEMsize); 
    }
    catch (const std::exception& e) { fprintf(stdout, " could not truncate dem.data. excep = %s \n ", e.what());}
   
    
    auto region = bi::mapped_region{shm, bi::read_write};
    void* pMem = region.get_address();
    short* arr = new (pMem) short [IPPD * IPPD * MAXPAGES];
    dem_arr = arr; // sET GLOBAL array
    ////////////////////////////////////////////////

    /////////////// get shared mem for dem attrs////////////
    int attrs_size;
    attrs_size = 4 * 6 * MAXPAGES; // min_north, max_north, min_west, max_west, max_el, min_el (all int = 4 Bytes)
     try{
      shm_attrs.truncate(attrs_size); 
    }
     catch (const std::exception& e) { fprintf(stdout, " could not truncate dem attrs. excep = %s \n ", e.what());}

     
    auto attrs_region = bi::mapped_region{shm_attrs, bi::read_write};
    void* pMem_attrs = attrs_region.get_address();
    int* attrs_arr = new (pMem_attrs) int [6 * MAXPAGES]; //min_north, max_north, min_west, max_west, max_el, min_el (all int)
    dem_attrs_arr = attrs_arr;
    /////////////////////////////////////////////////
    
    unsigned int  pushed = 0;
    int attrs_pushed = 0;
    // initialize the short array with -999
    for (int x=0; x<MAXPAGES; x++)
      {
	try {
	  for (int y=0; y<IPPD; y++){
	    for (int yy=0; yy<IPPD; yy++){
	      try {
		arr[pushed] = -999; //dem[x].data[y][yy];
		pushed = pushed + 1;
	      }
	      catch (const std::exception& e) { 
		fprintf(stdout, "............stuck at pushing no:  %u", pushed);
		fprintf(stdout, "............e.what = %s \n", e.what()); 
	      }
	    }
	  }
	}
	catch (const std::exception& e) { fprintf(stdout, "push error = %s \n ", e.what());}
	// now push the attrs
	for (int ii =0; ii < 6; ii++){
	  attrs_arr[attrs_pushed + ii] = -111; //min_north, max_north, min_west, max_west, max_el, min_el;
	}
	attrs_pushed = attrs_pushed + 6;
      }
    sizeof_mem_dem_array = pushed;
    sizeof_mem_dem_attrs_array = attrs_pushed;
    
    fprintf(stdout, "ok2: going to load topo \n ");
 
    // now load data into this shared mem
    LoadTopoData(max_lon, min_lon, max_lat, min_lat);
    fprintf(stdout, "topo loaded..printing dem attrs \n");

    // now copy the dem attrs to shared mem
    for (int x=0; x<MAXPAGES; x++)
      {
		
	attrs_arr[x*6 + 5] = dem[x].min_el;
	attrs_arr[x*6 + 4] = dem[x].max_el;
	attrs_arr[x*6 + 3] = dem[x].max_west;
	attrs_arr[x*6 + 2] = dem[x].min_west;
	attrs_arr[x*6 + 1] = dem[x].max_north;
	attrs_arr[x*6 + 0] = dem[x].min_north;
      }


    // for reading shared DEM attributes in GetElevation
    attrs_region_p_site = bi::mapped_region{shm_attrs_read, bi::read_only};;
    attrs_pMem_read_p_site = attrs_region_p_site.get_address();
    attrs_arr_read_p_site = static_cast<int*>(attrs_pMem_read_p_site);


    // for reading shared mem DEM in GetElevation 
    dem_region_read = bi::mapped_region{shm_read, bi::read_only}; 
    dem_pMem_read = dem_region_read.get_address(); 
    dem_arr_read = static_cast<short*>(dem_pMem_read); 
    
}


short prop_site::getElevationAtLoc(float lat, float lon){
    this->initialize_heavy((int)floor(lat), (int)floor(lat), (int)floor(lon), (int)floor(lon), 0,0,0,0,0,0,0,0);
    struct site tx;
    tx.lat= lat;
    tx.lon = lon;
    float elev_tx = GetElevation(tx); //
    return (short)(elev_tx *METERS_PER_FOOT);
}


short prop_site::getElevationAtLocWithoutLoadingDEM(float lat, float lon){
    struct site tx;
    tx.lat= lat;
    tx.lon = lon;
    float elev_tx = GetElevation(tx); //
    return (short)(elev_tx *METERS_PER_FOOT);
}


  // alt should be given in feet! asl = 1 measn alts given as ASL, otherwise AGL, set reverseDirection to "1" to compute propagation (and loss) from rx to tx
std::vector<float> prop_site::getLosAndLoss(float tx_lat, float tx_lon, float tx_alt, float rx_lat, float rx_lon, float rx_alt, float freq, int asl, int justLos, int reverseDirection)
{

  //fprintf(stdout, "======================================C++: in prop_site::getLosAndLoss \n");
  struct site tx, rx;
    tx.lat= tx_lat;
    tx.lon = tx_lon;
    rx.lat= rx_lat;
    rx.lon = rx_lon;
   float elev_tx = GetElevation(tx);
   float elev_rx = GetElevation(rx);

  if (asl == 1){ // convert to AGL for source and destination
    tx_alt = tx_alt - elev_tx;
    rx_alt = rx_alt - elev_rx;
    float max_below_ground_meters = 10; // maxmially 10m under ground is allowed due to rounding errors
    float h_thresh = -1 * max_below_ground_meters / 0.30479999999999996; //  in feet


    if ((tx_alt < h_thresh) || (rx_alt < h_thresh)){
      int losret = -2;
      if ((tx_alt < h_thresh) && (rx_alt < h_thresh))
	    losret = -4;
      if ((tx_alt < h_thresh) && (rx_alt > h_thresh))
	    losret = -3;
      if ((tx_alt > h_thresh) && (rx_alt < h_thresh))
	    losret = -2;

      
      if (justLos == 1){
	    tx.alt = tx_alt;
	    rx.alt = rx_alt;

	    std::vector<float> ret_b { losret, losret, -99998, -99999};

      	return ret_b;
      }
      else{
        //fprintf(stdout, "splatBurst.cpp: getLosAndLoss: underground request: tx_alt: %f, rx_alt = %f: , h_thresh: %f \n", tx_alt, rx_alt, h_thresh);
        // return format: los, propagation_path_loss, free_space_loss, surface_distance, source_elevation, dest_elevation, point_to_point_distance, first_fresnel_zone_clear
	    std::vector<float> ret_b { losret, -1, -1, -99998, tx_alt, rx_alt, -99999, 0};
	    return ret_b;
      }
    }
  }
  else{ // this means both tx and rx are given in AGL already, so do not do anything
     
  }


    int x, y, z=0, min_lat, min_lon, max_lat, max_lon,
      rxlat, rxlon, txlat, txlon, west_min, west_max,
      north_min, north_max;
    
    unsigned char	coverage=0, LRmap=0, terrain_plot=0,
      elevation_plot=0, height_plot=0, map=0,
      longley_plot=0, cities=0, bfs=0, txsites=0,
      norm=0, topomap=0, geo=0, kml=0, pt2pt_mode=0,
      area_mode=0, max_txsites, ngs=0, nolospath=0,
      nositereports=0, fresnel_plot=1, command_line_log=0;
    
    char mapfile[255], header[80], city_file[5][255],
      elevation_file[255], height_file[255],
      longley_file[255], terrain_file[255],
      string[255], rxfile[255], *env=NULL,
      txfile[255], boundary_file[5][255],
      udt_file[255], rxsite=0, ani_filename[255],
      ano_filename[255], ext[20], logfile[255];
    
    double		altitude=0.0, altitudeLR=0.0, tx_range=0.0,
      rx_range=0.0, deg_range=0.0, deg_limit=0.0,
      deg_range_lon, er_mult;
    
    struct		site tx_site, rx_site;

    this->freq = freq;
    
    FILE		*fd;
    
    
    
    olditm= oitm;
    kml=0;
    geo=0;
    dbm=0;
    gpsav=0;
    metric=0;
    rxfile[0]=0;
    txfile[0]=0;
    string[0]=0;
    mapfile[0]=0;
    clutter=ground_clutter;
    forced_erp=-1.0;
    forced_freq=0.0;
    elevation_file[0]=0;
    terrain_file[0]=0;
    sdf_path[0]=0;
    udt_file[0]=0;
    path.length=0;
    max_txsites=30;
    fzone_clearance=0.6;
    contour_threshold=0;
    rx_site.lat=91.0;
    rx_site.lon=361.0;
    longley_file[0]=0;
    ano_filename[0]=0;
    ani_filename[0]=0;
    smooth_contours=0;
    earthradius=EARTHRADIUS*1.333; // this is done in the original splat.cpp upon input -m 1.333. we want to consider this always as we are using splat mainly for radar coverage computations
    
    ippd=IPPD;		/* pixels per degree (integer) */
    ppd=(double)ippd;	/* pixels per degree (double)  */
    dpp=1.0/ppd;	/* degrees per pixel */
    mpi=ippd-1;		/* maximum pixel index per degree */
    
    
  
    tx_site.lat= tx_lat;
    tx_site.lon= tx_lon;
    tx_site.alt = tx_alt;
    
    rx_site.lat= rx_lat;
    rx_site.lon= rx_lon;
    rx_site.alt = rx_alt;
  

    if (justLos == 1){ // this is just for LoS computation, no propagation
      // freq is needed to check if first Fresnel zone is clear, returns also distance in km
      ObstructionAnalysisReturn obstRet = ObstructionAnalysisBURST(tx_site, rx_site, this->freq);

      std::vector<float> ret_b { obstRet.los, obstRet.first_fresnel_zone_clear, obstRet.surface_distance, obstRet.point_to_point_distance};
      return ret_b; // returns los and if first Fresnel zone is clear
    }

    
    else{ // this is LoS and propagation
      /***** Let the SPLATting begin! *****/
      PlaceMarker(rx_site);
      PlaceMarker(tx_site);
      
      LR.eps_dielect=this->diel_const;
      LR.sgm_conductivity=this->earth_cond;
      LR.eno_ns_surfref=this->at_bend;
      LR.frq_mhz=this->freq;
      LR.radio_climate=this->radio_climate;
      LR.pol=this->pol;
      LR.conf=this->frac_of_situ;
      LR.rel=this->frac_of_time;
      LR.erp=0.0;
    

      if (reverseDirection == 0){
        //fprintf(stdout,"debug1\n");
        Pt2PtReturn ret = PathReportBURST(tx_site,rx_site);
         std::vector<float> ret_b { ret.los, ret.propagation_path_loss, ret.free_space_loss, ret.surface_distance, ret.source_elevation, ret.dest_elevation, ret.point_to_point_distance, ret.first_fresnel_zone_clear};
         //if (std::isnan(ret.propagation_path_loss)){
            //fprintf(stdout,"splatBurst.cpp: returning NAN from C++ array : LOS[0/1]:%f, PROP_LOSS[dB]%f, FREE_SPACE_LOSS[dB]%f, dist[m]: %f, source_elev[masl]: %f, dest_elev[masl]: %f, p_to_pdist[m]: %f, first_fresnel_zone_free: %f\n", ret_b[0], ret_b[1], ret_b[2], ret_b[3],ret_b[4], ret_b[5], ret_b[6], ret_b[7]);
         //}
		 //fprintf(stdout,"splatBurst.cpp lo: returning from C++ array : LOS[0/1]:%f, PROP_LOSS[dB]%f, FREE_SPACE_LOSS[dB]%f, dist[m]: %f, source_elev[masl]: %f, dest_elev[masl]: %f, p_to_pdist[m]: %f, first_fresnel_zone_free: %f\n", ret_b[0], ret_b[1], ret_b[2], ret_b[3],ret_b[4], ret_b[5], ret_b[6], ret_b[7]);
    
        return ret_b;
      }

      else{ // this means the propgation loss should be computed in the reverse direction

        Pt2PtReturn ret = PathReportBURST(rx_site, tx_site);
        std::vector<float> ret_b {ret.los, ret.propagation_path_loss, ret.free_space_loss, ret.surface_distance, ret.source_elevation, ret.dest_elevation, ret.point_to_point_distance, ret.first_fresnel_zone_clear};
        fprintf(stdout,"splatBurst.cpp: propagation loss reverse direction! returning from C++ array : LOS[0/1]:%f, PROP_LOSS[dB]%f, FREE_SPACE_LOSS[dB]%f, dist[m]: %f, source_elev[masl]: %f, dest_elev[masl]: %f, p_to_pdist[m]: %f, first_fresnel_zone_free: %f\n", ret_b[0], ret_b[1], ret_b[2], ret_b[3],ret_b[4], ret_b[5], ret_b[6], ret_b[7]);
        return ret_b;
      }


    }
}

void prop_site::setLatLonBoundaries(float minlat, float maxlat, float minlon, float maxlon){
  this->minlat = minlat;
  this->maxlat = maxlat;
  this->minlon = minlon;
  this->maxlon = maxlon;
  
}
std::vector<float> prop_site::getElevationsMatrix(boost::python::list& dest_lat_arr, boost::python::list& dest_lon_arr){
    struct site tx;
    std::vector<float> elevs;
    for (int x=0; x< len(dest_lat_arr); x++){
       float curr_lat = static_cast<float>(boost::python::extract<float>(dest_lat_arr[x]));
	   float curr_lon = static_cast<float>(boost::python::extract<float>(dest_lon_arr[x]));
       tx.lat= curr_lat;
       tx.lon = curr_lon;
       float elev = GetElevation(tx) *METERS_PER_FOOT;
       elevs.push_back(elev); //
	 }

    return elevs;

}


//float minlat, float maxlat, float minlon, float maxlon, 
// alt should be given in feet! asl=1 means the alts are given in ASL, otherwise mAGL
GetLosAndLossReturn* prop_site::getLosAndLossRadial(float src_lat, float src_lon, float src_alt, boost::python::list& dest_lat_arr, boost::python::list& dest_lon_arr, float dest_alt, float freq, int asl, int nof_processes, int justLos, int nofPointsPerRay, int stopAtFirstLoS){
  		// the already existing boost shared memory dem array will be read by mpi processes
        //----------------------------------------------------------------------------------------------------------------------------------------
        //----------------------------------------------------------------------------------------------------------------------------------------
     	//----------------------------------- create a boost shared memory for lat array (will be read by mpi processes) --------------------------
     	//----------------------------------------------------------------------------------------------------------------------------------------
     	//----------------------------------------------------------------------------------------------------------------------------------------
     	
     auto lats_shm = bi::shared_memory_object{	
        bi::open_or_create,
        "lats_shared_memory_segment",
        bi::read_write
	};
     auto lats_shm_remove = SharedMemoryCleaner("lats_shared_memory_segment");
     // get total needed size of shared memory
     try{
       lats_shm.truncate(4 * len(dest_lat_arr)); // 4 bytes per float
     }
     catch (const std::exception& e) { fprintf(stdout, " could not truncate lats shm. excep = %s \n ", e.what());}
     auto lats_region = bi::mapped_region{lats_shm, bi::read_write};
     void* lats_pMem = lats_region.get_address();
     float* lats_arr = new (lats_pMem) float [len(dest_lat_arr)];
     unsigned int  lats_pushed = 0;
     // fill the lats shared array
     for (int x=0; x<len(dest_lat_arr); x++)
       {
	 try {
	   lats_arr[lats_pushed] = static_cast<float>(boost::python::extract<float>(dest_lat_arr[x]));
	   lats_pushed = lats_pushed + 1;
	 }
	catch (const std::exception& e) { 
	  fprintf(stdout, "............stuck at pushing lats no:  %u", lats_pushed);
	}
      }

    //----------------------------------------------------------------------------------------------------------------------------------------
    //----------------------------------------------------------------------------------------------------------------------------------------
    // ------------------------create a boost shared memory for lon array (will be read by mpi processes)
    //----------------------------------------------------------------------------------------------------------------------------------------
    //----------------------------------------------------------------------------------------------------------------------------------------
     auto lons_shm = bi::shared_memory_object{	
        bi::open_or_create,
        "lons_shared_memory_segment",
        bi::read_write
	};
     auto lons_shm_remove = SharedMemoryCleaner("lons_shared_memory_segment");
     // get total needed size of shared memory
     try{
       lons_shm.truncate(4 * len(dest_lon_arr)); // 4 bytes per float
     }
     catch (const std::exception& e) { fprintf(stdout, " could not truncate lons shm. excep = %s \n ", e.what());}
     auto lons_region = bi::mapped_region{lons_shm, bi::read_write};
     void* lons_pMem = lons_region.get_address();
     float* lons_arr = new (lons_pMem) float [len(dest_lon_arr)];
     unsigned int  lons_pushed = 0;
     // fill the lons shared array
     for (int x=0; x<len(dest_lon_arr); x++)
       {
	 try {
	   lons_arr[lons_pushed] = static_cast<float>(boost::python::extract<float>(dest_lon_arr[x]));
	   lons_pushed = lons_pushed + 1;
	 }
	catch (const std::exception& e) { 
	  fprintf(stdout, "............stuck at pushing lons no:  %u", lons_pushed);
	}
      }

    //----------------------------------------------------------------------------------------------------------------------------------------
    //----------------------------------------------------------------------------------------------------------------------------------------
    //------------------create a boost shared memory for distance array (will be written by mpi processes). this array is supposed to be lats_pushed*lon_pushed long
    //----------------------------------------------------------------------------------------------------------------------------------------
	//----------------------------------------------------------------------------------------------------------------------------------------

     auto dist_shm = bi::shared_memory_object{	
        bi::open_or_create,
        "dist_shared_memory_segment",
        bi::read_write
	};
     auto dist_shm_remove = SharedMemoryCleaner("dist_shared_memory_segment");
     // get total needed size of shared memory
     try{
       dist_shm.truncate(4 * len(dest_lon_arr)); // 4 bytes per float
     }
     catch (const std::exception& e) { fprintf(stdout, " could not truncate dist shm. excep = %s \n ", e.what());}
     auto dist_region = bi::mapped_region{dist_shm, bi::read_write};
     void* dist_pMem = dist_region.get_address();
     float* dist_arr = new (dist_pMem) float [len(dest_lon_arr)];
     unsigned int  dist_pushed = 0;
     // fill the los shared array with -1
     for (int x=0; x<(len(dest_lon_arr)); x++)
       {
	 try {
	   dist_arr[dist_pushed] = -1.0;
	   dist_pushed = dist_pushed + 1;
	 }
	catch (const std::exception& e) { 
	  fprintf(stdout, "............stuck at pushing dist no:  %u", dist_pushed);
	}
      }

    //----------------------------------------------------------------------------------------------------------------------------------------
    //----------------------------------------------------------------------------------------------------------------------------------------
    //------------------create a boost shared memory for LoS array (will be written by mpi processes). this array is supposed to be lats_pushed*lon_pushed long
    //----------------------------------------------------------------------------------------------------------------------------------------
	//----------------------------------------------------------------------------------------------------------------------------------------
     auto los_shm = bi::shared_memory_object{	
        bi::open_or_create,
        "los_shared_memory_segment",
        bi::read_write
	};
     auto los_shm_remove = SharedMemoryCleaner("los_shared_memory_segment");
     // get total needed size of shared memory
     try{
       los_shm.truncate(4 * len(dest_lon_arr)); // 4 bytes per float
     }
     catch (const std::exception& e) { fprintf(stdout, " could not truncate los shm. excep = %s \n ", e.what());}
     auto los_region = bi::mapped_region{los_shm, bi::read_write};
     void* los_pMem = los_region.get_address();
     float* los_arr = new (los_pMem) float [len(dest_lon_arr)];
     unsigned int  los_pushed = 0;
     // fill the los shared array with -1
     for (int x=0; x<(len(dest_lon_arr)); x++)
       {
	 try {
	   los_arr[los_pushed] = 1.0; //// instantiate to one, to make use of the fact that for coverage above radar only until the first LoS=1.0 has to be computed starting from the farthest point
	   los_pushed = los_pushed + 1;
	 }
	catch (const std::exception& e) { 
	  fprintf(stdout, "............stuck at pushing los no:  %u", los_pushed);
	}
      }


     float* free_loss_arr;
     float* loss_arr;

    //----------------------------------------------------------------------------------------------------------------------------------------
    //----------------------------------------------------------------------------------------------------------------------------------------
    //------------------create a boost shared memory for PROP LOSS array (will be written by mpi processes). this array is supposed to be lats_pushed*lon_pushed long
    //----------------------------------------------------------------------------------------------------------------------------------------
	//----------------------------------------------------------------------------------------------------------------------------------------
     auto loss_shm = bi::shared_memory_object{	
       bi::open_or_create,
       "loss_shared_memory_segment",
       bi::read_write
     };
     auto loss_shm_remove = SharedMemoryCleaner("loss_shared_memory_segment");
     // get total needed size of shared memory
     try{
       loss_shm.truncate(4 * len(dest_lon_arr)); // 4 bytes per float
     }
     catch (const std::exception& e) { fprintf(stdout, " could not truncate loss shm. excep = %s \n ", e.what());}
     auto loss_region = bi::mapped_region{loss_shm, bi::read_write};
     void* loss_pMem = loss_region.get_address();
     loss_arr = new (loss_pMem) float [len(dest_lon_arr)];
     unsigned int  loss_pushed = 0;
       // fill the loss shared array with -1
     for (int x=0; x<(len(dest_lon_arr)); x++)
       {
	 try {
	     loss_arr[los_pushed] = -1.0;
	     loss_pushed = loss_pushed + 1;
	 }
	 catch (const std::exception& e) { 
	     fprintf(stdout, "............stuck at pushing loss no:  %u", loss_pushed);
	 }
       }

    //----------------------------------------------------------------------------------------------------------------------------------------
    //----------------------------------------------------------------------------------------------------------------------------------------
    //------------------create a boost shared memory for FREE SPACE LOSS array (will be written by mpi processes). this array is supposed to be lats_pushed*lon_pushed long
    //----------------------------------------------------------------------------------------------------------------------------------------
    //----------------------------------------------------------------------------------------------------------------------------------------
     auto free_loss_shm = bi::shared_memory_object{	
       bi::open_or_create,
       "free_loss_shared_memory_segment",
       bi::read_write
     };
     auto free_loss_shm_remove = SharedMemoryCleaner("free_loss_shared_memory_segment");
     // get total needed size of shared memory
     try{
       free_loss_shm.truncate(4 * len(dest_lon_arr)); // 4 bytes per float
     }
     catch (const std::exception& e) { fprintf(stdout, " could not truncate free_loss shm. excep = %s \n ", e.what());}
     auto free_loss_region = bi::mapped_region{free_loss_shm, bi::read_write};
     void* free_loss_pMem = free_loss_region.get_address();
     free_loss_arr = new (free_loss_pMem) float [len(dest_lon_arr)];
     unsigned int  free_loss_pushed = 0;
     // fill the loss shared array with -1
     for (int x=0; x<(len(dest_lon_arr)); x++)
       {
	 try {
	   free_loss_arr[free_loss_pushed] = -1.0;
	   free_loss_pushed = free_loss_pushed + 1;
	 }
	 catch (const std::exception& e) { 
	   fprintf(stdout, "............stuck at pushing free_loss no:  %u", free_loss_pushed);
	 }
       }
     
    //----------------------------------------------------------------------------------------------------------------------------------------
    //----------------------------------------------------------------------------------------------------------------------------------------
    //////////////////////// start MPI processing of LOS computation /////////////////////////////////////////

 
    std::string s("mpiexec -np " + std::to_string(nof_processes) + " ./SPLAT_RADIOPROP/mpi_radial_los_and_loss " + std::to_string(sizeof_mem_dem_array) + " " + std::to_string(lats_pushed)+ " " + std::to_string(lons_pushed) + " " + std::to_string(src_lat) + " " + std::to_string(src_lon) + " " +  std::to_string(src_alt) + " " +  std::to_string(dest_alt) + " " +  std::to_string(freq) + " " + std::to_string(asl)+ " " + std::to_string(nofPointsPerRay)+ " " + std::to_string(stopAtFirstLoS)+ " " + std::to_string(justLos) + " " + std::to_string(this->minlat) + " " + std::to_string(this->maxlat) + " " + std::to_string(this->minlon)+ " " + std::to_string(this->maxlon) );



       
    int a = std::system(s.c_str());
    fprintf(stdout, "returned from mpi call = %d \n", a);
       

         
     // now read the shared mem arrays and return them
     GetLosAndLossReturn* ret = new GetLosAndLossReturn();
     for (int x=0; x< los_pushed; x++){
       ret->los.push_back(los_arr[x]);
       ret->dist.push_back(dist_arr[x]);

       if (justLos == 0){
	    ret->loss.push_back(loss_arr[x]);
	    ret->free_loss.push_back(free_loss_arr[x]);
       }

     }
     return ret;
     
}
  // alt should be given in feet! asl=1 means the alts are given in ASL, otherwise mAGL
 GetLosAndLossReturn* prop_site::getLosAndLossMatrix(float src_lat, float src_lon, float src_alt, boost::python::list& dest_lat_arr, boost::python::list& dest_lon_arr, float dest_alt, float freq, int asl, int nof_processes, int justLos, int reverseDirection = 0){

     // the already existing boost shared memory dem array will be read by mpi processes
     //----------------------------------- create a boost shared memory for lat array (will be read by mpi processes) --------------------------
     auto lats_shm = bi::shared_memory_object{	
        bi::open_or_create,
        "lats_shared_memory_segment",
        bi::read_write
	};
     auto lats_shm_remove = SharedMemoryCleaner("lats_shared_memory_segment");
     // get total needed size of shared memory
     try{
       lats_shm.truncate(4 * len(dest_lat_arr)); // 4 bytes per float
     }
     catch (const std::exception& e) { fprintf(stdout, " could not truncate lats shm. excep = %s \n ", e.what());}
     auto lats_region = bi::mapped_region{lats_shm, bi::read_write};
     void* lats_pMem = lats_region.get_address();
     float* lats_arr = new (lats_pMem) float [len(dest_lat_arr)];
     unsigned int  lats_pushed = 0;
     // fill the lats shared array
     for (int x=0; x<len(dest_lat_arr); x++)
       {
	 try {
	   lats_arr[lats_pushed] = static_cast<float>(boost::python::extract<float>(dest_lat_arr[x]));
	   lats_pushed = lats_pushed + 1;
	 }
	catch (const std::exception& e) { 
	  fprintf(stdout, "............stuck at pushing lats no:  %u", lats_pushed);
	}
      }

     
     // ------------------------create a boost shared memory for lon array (will be read by mpi processes)
     auto lons_shm = bi::shared_memory_object{	
        bi::open_or_create,
        "lons_shared_memory_segment",
        bi::read_write
	};
     auto lons_shm_remove = SharedMemoryCleaner("lons_shared_memory_segment");
     // get total needed size of shared memory
     try{
       lons_shm.truncate(4 * len(dest_lon_arr)); // 4 bytes per float
     }
     catch (const std::exception& e) { fprintf(stdout, " could not truncate lons shm. excep = %s \n ", e.what());}
     auto lons_region = bi::mapped_region{lons_shm, bi::read_write};
     void* lons_pMem = lons_region.get_address();
     float* lons_arr = new (lons_pMem) float [len(dest_lon_arr)];
     unsigned int  lons_pushed = 0;
     // fill the lons shared array
     for (int x=0; x<len(dest_lon_arr); x++)
       {
	 try {
	   lons_arr[lons_pushed] = static_cast<float>(boost::python::extract<float>(dest_lon_arr[x]));
	   lons_pushed = lons_pushed + 1;
	 }
	catch (const std::exception& e) { 
	  fprintf(stdout, "............stuck at pushing lons no:  %u", lons_pushed);
	}
      }

     //------------------create a boost shared memory for distance array (will be written by mpi processes). this array is supposed to be lats_pushed*lon_pushed long
     auto dist_shm = bi::shared_memory_object{	
        bi::open_or_create,
        "dist_shared_memory_segment",
        bi::read_write
	};
     auto dist_shm_remove = SharedMemoryCleaner("dist_shared_memory_segment");
     // get total needed size of shared memory
     try{
       dist_shm.truncate(4 * len(dest_lon_arr)* len(dest_lat_arr)); // 4 bytes per float
     }
     catch (const std::exception& e) { fprintf(stdout, " could not truncate dist shm. excep = %s \n ", e.what());}
     auto dist_region = bi::mapped_region{dist_shm, bi::read_write};
     void* dist_pMem = dist_region.get_address();
     float* dist_arr = new (dist_pMem) float [len(dest_lon_arr)*len(dest_lat_arr)];
     unsigned int  dist_pushed = 0;
     // fill the los shared array with -1
     for (int x=0; x<(len(dest_lon_arr)*len(dest_lat_arr)); x++)
       {
	 try {
	   dist_arr[dist_pushed] = -1.0;
	   dist_pushed = dist_pushed + 1;
	 }
	catch (const std::exception& e) { 
	  fprintf(stdout, "............stuck at pushing dist no:  %u", dist_pushed);
	}
      }
     
     //------------------create a boost shared memory for los array (will be written by mpi processes). this array is supposed to be lats_pushed*lon_pushed long
     auto los_shm = bi::shared_memory_object{	
        bi::open_or_create,
        "los_shared_memory_segment",
        bi::read_write
	};
     auto los_shm_remove = SharedMemoryCleaner("los_shared_memory_segment");
     // get total needed size of shared memory
     try{
       los_shm.truncate(4 * len(dest_lon_arr)* len(dest_lat_arr)); // 4 bytes per float
     }
     catch (const std::exception& e) { fprintf(stdout, " could not truncate los shm. excep = %s \n ", e.what());}
     auto los_region = bi::mapped_region{los_shm, bi::read_write};
     void* los_pMem = los_region.get_address();
     float* los_arr = new (los_pMem) float [len(dest_lon_arr)*len(dest_lat_arr)];
     unsigned int  los_pushed = 0;
     // fill the los shared array with -1
     for (int x=0; x<(len(dest_lon_arr)*len(dest_lat_arr)); x++)
       {
	 try {
	   los_arr[los_pushed] = -1.0;
	   los_pushed = los_pushed + 1;
	 }
	catch (const std::exception& e) { 
	  fprintf(stdout, "............stuck at pushing los no:  %u", los_pushed);
	}
      }


     float* free_loss_arr;
     float* loss_arr;
     
     //------------------create a boost shared memory for PROP LOSS array (will be written by mpi processes). this array is supposed to be lats_pushed*lon_pushed long
     auto loss_shm = bi::shared_memory_object{	
       bi::open_or_create,
       "loss_shared_memory_segment",
       bi::read_write
     };
     auto loss_shm_remove = SharedMemoryCleaner("loss_shared_memory_segment");
     // get total needed size of shared memory
     try{
       loss_shm.truncate(4 * len(dest_lon_arr)* len(dest_lat_arr)); // 4 bytes per float
     }
     catch (const std::exception& e) { fprintf(stdout, " could not truncate loss shm. excep = %s \n ", e.what());}
     auto loss_region = bi::mapped_region{loss_shm, bi::read_write};
     void* loss_pMem = loss_region.get_address();
     loss_arr = new (loss_pMem) float [len(dest_lon_arr)*len(dest_lat_arr)];
     unsigned int  loss_pushed = 0;
       // fill the loss shared array with -1
     for (int x=0; x<(len(dest_lon_arr)*len(dest_lat_arr)); x++)
       {
	 try {
	     loss_arr[los_pushed] = -1.0;
	     loss_pushed = loss_pushed + 1;
	 }
	 catch (const std::exception& e) { 
	     fprintf(stdout, "............stuck at pushing loss no:  %u", loss_pushed);
	 }
       }
     //------------------create a boost shared memory for FREE SPACE LOSS array (will be written by mpi processes). this array is supposed to be lats_pushed*lon_pushed long
     auto free_loss_shm = bi::shared_memory_object{	
       bi::open_or_create,
       "free_loss_shared_memory_segment",
       bi::read_write
     };
     auto free_loss_shm_remove = SharedMemoryCleaner("free_loss_shared_memory_segment");
     // get total needed size of shared memory
     try{
       free_loss_shm.truncate(4 * len(dest_lon_arr)* len(dest_lat_arr)); // 4 bytes per float
     }
     catch (const std::exception& e) { fprintf(stdout, " could not truncate free_loss shm. excep = %s \n ", e.what());}
     auto free_loss_region = bi::mapped_region{free_loss_shm, bi::read_write};
     void* free_loss_pMem = free_loss_region.get_address();
     free_loss_arr = new (free_loss_pMem) float [len(dest_lon_arr)*len(dest_lat_arr)];
     unsigned int  free_loss_pushed = 0;
     // fill the loss shared array with -1
     for (int x=0; x<(len(dest_lon_arr)*len(dest_lat_arr)); x++)
       {
	 try {
	   free_loss_arr[free_loss_pushed] = -1.0;
	   free_loss_pushed = free_loss_pushed + 1;
	 }
	 catch (const std::exception& e) { 
	   fprintf(stdout, "............stuck at pushing free_loss no:  %u", free_loss_pushed);
	 }
       }
     
     
     ///////////////////////// start MPI processing of LOS computation /////////////////////////////////////////
     
     //Launch mpi application (TBD: LD_LIBRARY PATH has to be set so that the mpi app find the .so library)
     // it  does not work as tried here
     //std::string ss("export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:/home/radaruser/Projects/OPENBURST/DEM/SPLAT_RADIOPROP");
     //int aa = std::system(ss.c_str());

     fprintf(stdout, "================================= getLosAndLossMatrix: calling mpiexec \n");
     std::string s("mpiexec -np " + std::to_string(nof_processes) + " ./SPLAT_RADIOPROP/mpi_los_and_loss " + std::to_string(sizeof_mem_dem_array) + " " + std::to_string(lats_pushed)+ " " + std::to_string(lons_pushed) + " " + std::to_string(src_lat) + " " + std::to_string(src_lon) + " " +  std::to_string(src_alt) + " " +  std::to_string(dest_alt) + " " +  std::to_string(freq) + " " + std::to_string(asl) + " " + std::to_string(justLos)+ " " + std::to_string(this->minlat) + " " + std::to_string(this->maxlat) + " " + std::to_string(this->minlon)+ " " + std::to_string(this->maxlon) + " " + std::to_string(reverseDirection));
     int a = std::system(s.c_str());
     fprintf(stdout, "returned from mpi call = %d \n", a);

         
     // now read the shared mem arrays and return them
     GetLosAndLossReturn* ret = new GetLosAndLossReturn();
     
     for (int x=0; x< los_pushed; x++){
       ret->los.push_back(los_arr[x]);
       ret->dist.push_back(dist_arr[x]);

       if (justLos == 0){
	    ret->loss.push_back(loss_arr[x]);
	    ret->free_loss.push_back(free_loss_arr[x]);
       }
       
     }
     return ret;
  }
  



void point_to_point(double elev[], double tht_m, double rht_m,
	  double eps_dielect, double sgm_conductivity, double eno_ns_surfref,
	  double frq_mhz, int radio_climate, int pol, double conf,
	  double rel, double &dbloss, char *strmode, int &errnum);

void point_to_point_ITM(double elev[], double tht_m, double rht_m,
	  double eps_dielect, double sgm_conductivity, double eno_ns_surfref,
	  double frq_mhz, int radio_climate, int pol, double conf,
	  double rel, double &dbloss, char *strmode, int &errnum);

double ITWOMVersion();

int interpolate(int y0, int y1, int x0, int x1, int n)
{
	/* Perform linear interpolation between quantized contour
	   levels displayed in field strength and path loss maps.
	   If signal level x0 corresponds to color level y0, signal
	   level x1 corresponds to color level y1, and signal level
	   n falls somewhere between x0 and x1, determine what
	   color value n corresponds to between y0 and y1. */

	int result=0;
	double delta_x, delta_y;

	if (n<=x0)
		return y0;

	if (n>=x1)
		return y1;

	if (y0==y1)
		return y0;

	if (x0==x1)
		return y0;

	delta_y=(double)(y0-y1);
	delta_x=(double)(x0-x1);

	result=y0+(int)ceil((delta_y/delta_x)*(n-x0));

	return result;
}

double arccos(double x, double y)
{
	/* This function implements the arc cosine function,
	   returning a value between 0 and TWOPI. */

	double result=0.0;

	if (y>0.0)
		result=acos(x/y);

	if (y<0.0)
		result=PI+acos(x/y);

	return result;
}

int ReduceAngle(double angle)
{
	/* This function normalizes the argument to
	   an integer angle between 0 and 180 degrees */

	double temp;

	temp=acos(cos(angle*DEG2RAD));

	return (int)rint(temp/DEG2RAD);
}

double LonDiff(double lon1, double lon2)
{
	/* This function returns the short path longitudinal
	   difference between longitude1 and longitude2 
	   as an angle between -180.0 and +180.0 degrees.
	   If lon1 is west of lon2, the result is positive.
	   If lon1 is east of lon2, the result is negative. */

	double diff;

	diff=lon1-lon2;

	if (diff<=-180.0)
		diff+=360.0;

	if (diff>=180.0)
		diff-=360.0;

	return diff;
}

char *dec2dms(double decimal)
{
	/* Converts decimal degrees to degrees, minutes, seconds,
	   (DMS) and returns the result as a character string. */

	char	sign;
	int	degrees, minutes, seconds;
	double	a, b, c, d;

	if (decimal<0.0)
	{
		decimal=-decimal;
		sign=-1;
	}

	else
		sign=1;

	a=floor(decimal);
	b=60.0*(decimal-a);
	c=floor(b);
	d=60.0*(b-c);

	degrees=(int)a;
	minutes=(int)c;
	seconds=(int)d;

	if (seconds<0)
		seconds=0;

	if (seconds>59)
		seconds=59;

	string[0]=0;
	snprintf(string,250,"%d%c %d\' %d\"", degrees*sign, 176, minutes, seconds);
	return (string);
}

int PutMask(double lat, double lon, int value)
{
	/* Lines, text, markings, and coverage areas are stored in a
	   mask that is combined with topology data when topographic
	   maps are generated by SPLAT!.  This function sets and resets
	   bits in the mask based on the latitude and longitude of the
	   area pointed to. */

	int	x, y, indx;
	char	found;

	for (indx=0, found=0; indx<MAXPAGES && found==0;)
	{
		x=(int)rint(ppd*(lat-dem[indx].min_north));
		y=mpi-(int)rint(ppd*(LonDiff(dem[indx].max_west,lon)));

		if (x>=0 && x<=mpi && y>=0 && y<=mpi)
			found=1;
		else
			indx++;
	}

	if (found)
	{
		dem[indx].mask[x][y]=value;
		return ((int)dem[indx].mask[x][y]);
	}

	else
		return -1;
}

int OrMask(double lat, double lon, int value)
{
	/* Lines, text, markings, and coverage areas are stored in a
	   mask that is combined with topology data when topographic
	   maps are generated by SPLAT!.  This function sets bits in
	   the mask based on the latitude and longitude of the area
	   pointed to. */

	int	x, y, indx;
	char	found;

	for (indx=0, found=0; indx<MAXPAGES && found==0;)
	{
		x=(int)rint(ppd*(lat-dem[indx].min_north));
		y=mpi-(int)rint(ppd*(LonDiff(dem[indx].max_west,lon)));

		if (x>=0 && x<=mpi && y>=0 && y<=mpi)
			found=1;
		else
			indx++;
	}

	if (found)
	{
		dem[indx].mask[x][y]|=value;
		return ((int)dem[indx].mask[x][y]);
	}

	else
		return -1;
}

int GetMask(double lat, double lon)
{
	/* This function returns the mask bits based on the latitude
	   and longitude given. */

	return (OrMask(lat,lon,0));
}

int PutSignal(double lat, double lon, unsigned char signal)
{
	/* This function writes a signal level (0-255)
	   at the specified location for later recall. */

	int	x, y, indx;
	char	found;

	for (indx=0, found=0; indx<MAXPAGES && found==0;)
	{
		x=(int)rint(ppd*(lat-dem[indx].min_north));
		y=mpi-(int)rint(ppd*(LonDiff(dem[indx].max_west,lon)));

		if (x>=0 && x<=mpi && y>=0 && y<=mpi)
			found=1;
		else
			indx++;
	}

	if (found)
	{
		dem[indx].signal[x][y]=signal;
		return (dem[indx].signal[x][y]);
	}

	else
		return 0;
}

unsigned char GetSignal(double lat, double lon)
{
	/* This function reads the signal level (0-255) at the
	   specified location that was previously written by the
	   complimentary PutSignal() function. */

	int	x, y, indx;
	char	found;

	for (indx=0, found=0; indx<MAXPAGES && found==0;)
	{
		x=(int)rint(ppd*(lat-dem[indx].min_north));
		y=mpi-(int)rint(ppd*(LonDiff(dem[indx].max_west,lon)));

		if (x>=0 && x<=mpi && y>=0 && y<=mpi)
			found=1;
		else
			indx++;
	}

	if (found)
		return (dem[indx].signal[x][y]);
	else
		return 0;
}


/// this function has to be highly parallizable to be used with BOOST MPI. We use boost shared mem access
double GetElevation(struct site location)
{
	/* This function returns the elevation (in feet) of any location
	   represented by the digital elevation model data in memory.
	   Function returns -5000.0 for locations not found in memory. */

  try{
	char	found;
	int	x, y, indx;
	double	elevation;//, elevation1, elevation2;

	int* attrs_arr_read = attrs_arr_read_p_site; // this is shared memory read of DEM attributes
		
	for (indx=0, found=0; indx<MAXPAGES && found==0;)
	{
	  x=(int)rint(ppd*(location.lat-attrs_arr_read[indx*6 + 0]));
	  y=mpi-(int)rint(ppd*(LonDiff(attrs_arr_read[indx*6 + 3],location.lon))); 
	  
	  if (x>=0 && x<=mpi && y>=0 && y<=mpi)
	    found=1;
	  else
	    indx++;

	}

	if (found){
	  short* arr_read = dem_arr_read; // this is shared memory read of DEM
	  elevation=3.28084*arr_read[indx*IPPD*IPPD+x*IPPD+y]; // parallelizable
	}
	else{
		elevation=-5000.0;

	}

	return elevation;
  }

  catch (const std::exception& e) {
    fprintf(stdout, " could not get Elevation excp= %s \n ", e.what());
    exit(0);
  }
}

int AddElevation(double lat, double lon, double height)
{
	/* This function adds a user-defined terrain feature
	   (in meters AGL) to the digital elevation model data
	   in memory.  Does nothing and returns 0 for locations
	   not found in memory. */

	char	found;
	int	x, y, indx;

	for (indx=0, found=0; indx<MAXPAGES && found==0;)
	{
		x=(int)rint(ppd*(lat-dem[indx].min_north));
		y=mpi-(int)rint(ppd*(LonDiff(dem[indx].max_west,lon)));

		if (x>=0 && x<=mpi && y>=0 && y<=mpi)
			found=1;
		else
			indx++;
	}

	if (found)
		dem[indx].data[x][y]+=(short)rint(height);

	return found;
}

double Distance(struct site site1, struct site site2)
{
	/* This function returns the great circle distance
	   in miles between any two site locations. */

	double	lat1, lon1, lat2, lon2, distance;

	lat1=site1.lat*DEG2RAD;
	lon1=site1.lon*DEG2RAD;
	lat2=site2.lat*DEG2RAD;
	lon2=site2.lon*DEG2RAD;

	distance=3959.0*acos(sin(lat1)*sin(lat2)+cos(lat1)*cos(lat2)*cos((lon1)-(lon2)));

	return distance;
}

double Azimuth(struct site source, struct site destination)
{
	/* This function returns the azimuth (in degrees) to the
	   destination as seen from the location of the source. */

	double	dest_lat, dest_lon, src_lat, src_lon,
		beta, azimuth, diff, num, den, fraction;

	dest_lat=destination.lat*DEG2RAD;
	dest_lon=destination.lon*DEG2RAD;

	src_lat=source.lat*DEG2RAD;
	src_lon=source.lon*DEG2RAD;
		
	/* Calculate Surface Distance */

	beta=acos(sin(src_lat)*sin(dest_lat)+cos(src_lat)*cos(dest_lat)*cos(src_lon-dest_lon));

	/* Calculate Azimuth */

	num=sin(dest_lat)-(sin(src_lat)*cos(beta));
	den=cos(src_lat)*sin(beta);
	fraction=num/den;

	/* Trap potential problems in acos() due to rounding */

	if (fraction>=1.0)
		fraction=1.0;

	if (fraction<=-1.0)
		fraction=-1.0;

	/* Calculate azimuth */

	azimuth=acos(fraction);

	/* Reference it to True North */

	diff=dest_lon-src_lon;

	if (diff<=-PI)
		diff+=TWOPI;

	if (diff>=PI)
		diff-=TWOPI;

	if (diff>0.0)
		azimuth=TWOPI-azimuth;

	return (azimuth/DEG2RAD);		
}


// the solution below is not exactly correct, but good enough for our purposes
// for large geodesic distances (ie large distance on the ellipsoid surface) the difference is less than a few hundred meters
// assuming Earth's mean radius 6,371 km, adding 10 km to that adds about 0.16% to the geometric distance at 10 km altitude, ie about 300m
// see e.g. http://cosinekitty.com/compass.html

float Distance_including_ELevation(struct site source, struct site destination){
	/* This function returns the distance in meters from the destination to the source location considering also the elevation of the points.
	The original Distance function does not consider elevation.
	    */
  	register double a, b, dx;

	a=GetElevation(destination)+destination.alt+earthradius;
	b=GetElevation(source)+source.alt+earthradius;


 	dx=5280.0*Distance(source,destination); // Distance returns miles. multiply by 5280 to get feet
  
	// compute earth surface angular change (Sandia Report)//
	float phi_e = dx/earthradius;
	
	// now use law of cosines to find distance between source and destination including elevation
	float dist_src_dst_meters = METERS_PER_FOOT * sqrt(a*a + b*b - 2 * a * b * cos(phi_e));
	
	float pytha_dist = METERS_PER_FOOT * sqrt(dx*dx + (a-b)*(a-b));
	
	////////////////////////////////////////
	if (cos(phi_e) < 0.98){ 
	  return dist_src_dst_meters;
	}
	else{ // if cos(phi_e) == 1, law of cosine calculation does not hold
	  return pytha_dist;
	}
}



double ElevationAngle(struct site source, struct site destination)
{
	/* This function returns the angle of elevation (in degrees)
	   of the destination as seen from the source location.
	   A positive result represents an angle of elevation (uptilt),
	   while a negative result represents an angle of depression
	   (downtilt), as referenced to a normal to the center of
	   the earth. */
	   
	register double a, b, dx;

	a=GetElevation(destination)+destination.alt+earthradius;
	b=GetElevation(source)+source.alt+earthradius;

 	dx=5280.0*Distance(source,destination); // Distance returns miles. multiply by 5280 to get feet

	

	/* Apply the Law of Cosines */

	return ((180.0*(acos(((b*b)+(dx*dx)-(a*a))/(2.0*b*dx)))/PI)-90.0);
}



void ReadPathBURST(struct site source, struct site destination, struct pathBurst& currPath)
{

/* same as the original ReadPath but here we do not modify teh global path struct variable but a local variable currPath called by reference
    This function generates a sequence of latitude and
	   longitude positions between source and destination
	   locations along a great circle path, and stores
	   elevation and distance information for points
	   along that path in the "currPath" structure. */

    int	c;
	double	azimuth, distance, lat1, lon1, beta, den, num,
		lat2, lon2, total_distance, dx, dy, path_length,
		miles_per_sample, samples_per_radian=68755.0;
	struct	site tempsite;

	lat1=source.lat*DEG2RAD;
	lon1=source.lon*DEG2RAD;

	lat2=destination.lat*DEG2RAD;
	lon2=destination.lon*DEG2RAD;

	if (ppd==1200.0)
		samples_per_radian=68755.0;

	if (ppd==3600.0)
		samples_per_radian=206265.0;

	azimuth=Azimuth(source,destination)*DEG2RAD;

	total_distance=Distance(source,destination);

	if (total_distance>(30.0/ppd))		/* > 0.5 pixel distance */
	{
		dx=samples_per_radian*acos(cos(lon1-lon2));
		dy=samples_per_radian*acos(cos(lat1-lat2));

		path_length=sqrt((dx*dx)+(dy*dy));		/* Total number of samples */

		miles_per_sample=total_distance/path_length;	/* Miles per sample */
	}

	else
	{
		c=0;
		dx=0.0;
		dy=0.0;
		path_length=0.0;
		miles_per_sample=0.0;
		total_distance=0.0;

		lat1=lat1/DEG2RAD;
		lon1=lon1/DEG2RAD;

		currPath.lat[c]=lat1;
		currPath.lon[c]=lon1;
		currPath.elevation[c]=GetElevation(source);
		currPath.distance[c]=0.0;
	}

	for (distance=0.0, c=0; (total_distance!=0.0 && distance<=total_distance && c<ARRAYSIZE); c++, distance=miles_per_sample*(double)c)
	{
		beta=distance/3959.0;
		lat2=asin(sin(lat1)*cos(beta)+cos(azimuth)*sin(beta)*cos(lat1));
		num=cos(beta)-(sin(lat1)*sin(lat2));
		den=cos(lat1)*cos(lat2);

		if (azimuth==0.0 && (beta>HALFPI-lat1))
			lon2=lon1+PI;

		else if (azimuth==HALFPI && (beta>HALFPI+lat1))
				lon2=lon1+PI;

		else if (fabs(num/den)>1.0)
				lon2=lon1;

		else
		{
			if ((PI-azimuth)>=0.0)
				lon2=lon1-arccos(num,den);
			else
				lon2=lon1+arccos(num,den);
		}

		while (lon2<0.0)
			lon2+=TWOPI;

		while (lon2>TWOPI)
			lon2-=TWOPI;

		lat2=lat2/DEG2RAD;
		lon2=lon2/DEG2RAD;

		currPath.lat[c]=lat2;
		currPath.lon[c]=lon2;
		tempsite.lat=lat2;
		tempsite.lon=lon2;
		currPath.elevation[c]=GetElevation(tempsite);
		currPath.distance[c]=distance;
	}

	/* Make sure exact destination point is recorded at currPath.length-1 */

	if (c<ARRAYSIZE)
	{
		currPath.lat[c]=destination.lat;
		currPath.lon[c]=destination.lon;
		currPath.elevation[c]=GetElevation(destination);
		currPath.distance[c]=total_distance;
		c++;
	}

	if (c<ARRAYSIZE)
		currPath.length=c;
	else
		currPath.length=ARRAYSIZE-1;

}

void ReadPath(struct site source, struct site destination)
{
	/* This function generates a sequence of latitude and
	   longitude positions between source and destination
	   locations along a great circle path, and stores
	   elevation and distance information for points
	   along that path in the "path" structure. */

	int	c;
	double	azimuth, distance, lat1, lon1, beta, den, num,
		lat2, lon2, total_distance, dx, dy, path_length,
		miles_per_sample, samples_per_radian=68755.0;
	struct	site tempsite;

	lat1=source.lat*DEG2RAD;
	lon1=source.lon*DEG2RAD;

	lat2=destination.lat*DEG2RAD;
	lon2=destination.lon*DEG2RAD;

	if (ppd==1200.0)
		samples_per_radian=68755.0;

	if (ppd==3600.0)
		samples_per_radian=206265.0;

	azimuth=Azimuth(source,destination)*DEG2RAD;

	total_distance=Distance(source,destination);

	if (total_distance>(30.0/ppd))		/* > 0.5 pixel distance */
	{
		dx=samples_per_radian*acos(cos(lon1-lon2));
		dy=samples_per_radian*acos(cos(lat1-lat2));

		path_length=sqrt((dx*dx)+(dy*dy));		/* Total number of samples */

		miles_per_sample=total_distance/path_length;	/* Miles per sample */
	}

	else
	{
		c=0;
		dx=0.0;
		dy=0.0;
		path_length=0.0;
		miles_per_sample=0.0;
		total_distance=0.0;

		lat1=lat1/DEG2RAD;
		lon1=lon1/DEG2RAD;

		path.lat[c]=lat1;
		path.lon[c]=lon1;
		path.elevation[c]=GetElevation(source);
		path.distance[c]=0.0;
	}

	for (distance=0.0, c=0; (total_distance!=0.0 && distance<=total_distance && c<ARRAYSIZE); c++, distance=miles_per_sample*(double)c)
	{
		beta=distance/3959.0;
		lat2=asin(sin(lat1)*cos(beta)+cos(azimuth)*sin(beta)*cos(lat1));
		num=cos(beta)-(sin(lat1)*sin(lat2));
		den=cos(lat1)*cos(lat2);

		if (azimuth==0.0 && (beta>HALFPI-lat1))
			lon2=lon1+PI;

		else if (azimuth==HALFPI && (beta>HALFPI+lat1))
				lon2=lon1+PI;

		else if (fabs(num/den)>1.0)
				lon2=lon1;

		else
		{
			if ((PI-azimuth)>=0.0)
				lon2=lon1-arccos(num,den);
			else
				lon2=lon1+arccos(num,den);
		}
	
		while (lon2<0.0)
			lon2+=TWOPI;

		while (lon2>TWOPI)
			lon2-=TWOPI;
 
		lat2=lat2/DEG2RAD;
		lon2=lon2/DEG2RAD;

		path.lat[c]=lat2;
		path.lon[c]=lon2;
		tempsite.lat=lat2;
		tempsite.lon=lon2;
		path.elevation[c]=GetElevation(tempsite);
		path.distance[c]=distance;
	}

	/* Make sure exact destination point is recorded at path.length-1 */

	if (c<ARRAYSIZE)
	{
		path.lat[c]=destination.lat;
		path.lon[c]=destination.lon;
		path.elevation[c]=GetElevation(destination);
		path.distance[c]=total_distance;
		c++;
	}

	if (c<ARRAYSIZE)
		path.length=c;
	else
		path.length=ARRAYSIZE-1;
}

double ElevationAngleTwo(struct site source, struct site destination, double er)
{
	/* This function returns the angle of elevation (in degrees)
	   of the destination as seen from the source location, UNLESS
	   the path between the sites is obstructed, in which case, the
	   elevation angle to the first obstruction is returned instead.
	   "er" represents the earth radius. */
    //std::cout << "db elevAngle2: 0" << std::endl;

	int	x;
	char	block=0;
	double	source_alt, destination_alt, cos_xmtr_angle,
		cos_test_angle, test_alt, elevation, distance,
		source_alt2, first_obstruction_angle=0.0;

	struct pathBurst currPath;
	currPath.lat = new double[ARRAYSIZE];
    currPath.lon = new double[ARRAYSIZE];
    currPath.elevation = new double[ARRAYSIZE];
    currPath.distance = new double[ARRAYSIZE];

	ReadPathBURST(source, destination, currPath);

	distance=5280.0*Distance(source,destination);
	source_alt=er+source.alt+GetElevation(source);
	destination_alt=er+destination.alt+GetElevation(destination);
	source_alt2=source_alt*source_alt;

	/* Calculate the cosine of the elevation angle of the
	   destination (receiver) as seen by the source (transmitter). */

	cos_xmtr_angle=((source_alt2)+(distance*distance)-(destination_alt*destination_alt))/(2.0*source_alt*distance);

	/* Test all points in between source and destination locations to
	   see if the angle to a topographic feature generates a higher
	   elevation angle than that produced by the destination.  Begin
	   at the source since we're interested in identifying the FIRST
	   obstruction along the path between source and destination. */


    for (x=2, block=0; x<currPath.length && block==0; x++)
	{
		distance=5280.0*currPath.distance[x];

		test_alt=earthradius+(currPath.elevation[x]==0.0?currPath.elevation[x]:currPath.elevation[x]+clutter);

		cos_test_angle=((source_alt2)+(distance*distance)-(test_alt*test_alt))/(2.0*source_alt*distance);

		if (cos_xmtr_angle>=cos_test_angle)
		{
			block=1;
			first_obstruction_angle=((acos(cos_test_angle))/DEG2RAD)-90.0;
		}
	}

	if (block)
		elevation=first_obstruction_angle;

	else
		elevation=((acos(cos_xmtr_angle))/DEG2RAD)-90.0;


    delete currPath.lat;
    delete currPath.lon;
    delete currPath.elevation;
    delete currPath.distance;

	return elevation;

}

double AverageTerrain(struct site source, double azimuthx, double start_distance, double end_distance)
{
	/* This function returns the average terrain calculated in
	   the direction of "azimuth" (degrees) between "start_distance"
	   and "end_distance" (miles) from the source location.  If
	   the terrain is all water (non-critical error), -5000.0 is
	   returned.  If not enough SDF data has been loaded into
	   memory to complete the survey (critical error), then
	   -9999.0 is returned. */
 
	int	c, samples, endpoint;
	double	beta, lat1, lon1, lat2, lon2, num, den, azimuth, terrain=0.0;
	struct	site destination;

	lat1=source.lat*DEG2RAD;
	lon1=source.lon*DEG2RAD;

	/* Generate a path of elevations between the source
	   location and the remote location provided. */

	beta=end_distance/3959.0;

	azimuth=DEG2RAD*azimuthx;

	lat2=asin(sin(lat1)*cos(beta)+cos(azimuth)*sin(beta)*cos(lat1));
	num=cos(beta)-(sin(lat1)*sin(lat2));
	den=cos(lat1)*cos(lat2);

	if (azimuth==0.0 && (beta>HALFPI-lat1))
		lon2=lon1+PI;

	else if (azimuth==HALFPI && (beta>HALFPI+lat1))
			lon2=lon1+PI;

	else if (fabs(num/den)>1.0)
			lon2=lon1;

	else
	{
		if ((PI-azimuth)>=0.0)
			lon2=lon1-arccos(num,den);
		else
			lon2=lon1+arccos(num,den);
	}
	
	while (lon2<0.0)
		lon2+=TWOPI;

	while (lon2>TWOPI)
		lon2-=TWOPI;
 
	lat2=lat2/DEG2RAD;
	lon2=lon2/DEG2RAD;

	destination.lat=lat2;
	destination.lon=lon2;

	/* If SDF data is missing for the endpoint of
	   the radial, then the average terrain cannot
	   be accurately calculated.  Return -9999.0 */

	if (GetElevation(destination)<-4999.0)
		return (-9999.0);
	else
	{
		ReadPath(source,destination);

		endpoint=path.length;

		/* Shrink the length of the radial if the
		   outermost portion is not over U.S. land. */

		for (c=endpoint-1; c>=0 && path.elevation[c]==0.0; c--);

		endpoint=c+1;

		for (c=0, samples=0; c<endpoint; c++)
		{
			if (path.distance[c]>=start_distance)
			{
				terrain+=(path.elevation[c]==0.0?path.elevation[c]:path.elevation[c]+clutter);
				samples++;
			}
		}

		if (samples==0)
			terrain=-5000.0;  /* No land */
		else
			terrain=(terrain/(double)samples);

		return terrain;
	}
}

double haat(struct site antenna)
{
	/* This function returns the antenna's Height Above Average
	   Terrain (HAAT) based on FCC Part 73.313(d).  If a critical
	   error occurs, such as a lack of SDF data to complete the
	   survey, -5000.0 is returned. */

	int	azi, c;
	char	error=0;
	double	terrain, avg_terrain, haat, sum=0.0;

	/* Calculate the average terrain between 2 and 10 miles
	   from the antenna site at azimuths of 0, 45, 90, 135,
	   180, 225, 270, and 315 degrees. */

	for (c=0, azi=0; azi<=315 && error==0; azi+=45)
	{
		terrain=AverageTerrain(antenna, (double)azi, 2.0, 10.0);

		if (terrain<-9998.0)  /* SDF data is missing */
			error=1;

		if (terrain>-4999.0)  /* It's land, not water */
		{
			sum+=terrain;  /* Sum of averages */
			c++;
		}
	}

	if (error)
		return -5000.0;
	else
	{
		avg_terrain=(sum/(double)c);
		haat=(antenna.alt+GetElevation(antenna))-avg_terrain;
		return haat;
	}
}

void PlaceMarker(struct site location)
{
	/* This function places text and marker data in the mask array
	   for illustration on topographic maps generated by SPLAT!.
	   By default, SPLAT! centers text information BELOW the marker,
	   but may move it above, to the left, or to the right of the
	   marker depending on how much room is available on the map,
	   or depending on whether the area is already occupied by
	   another marker or label.  If no room or clear space is
	   available on the map to place the marker and its associated
	   text, then the marker and text are not written to the map. */
 
	int	a, b, c, byte;
	char	ok2print, occupied;
	double	x, y, lat, lon, textx=0.0, texty=0.0, xmin, xmax,
		ymin, ymax, p1, p3, p6, p8, p12, p16, p24, label_length;

	xmin=(double)min_north;
	xmax=(double)max_north;
	ymin=(double)min_west;
	ymax=(double)max_west;
	lat=location.lat;
	lon=location.lon;

	if (lat<xmax && lat>=xmin && (LonDiff(lon,ymax)<=0.0) && (LonDiff(lon,ymin)>=dpp))
	{
		p1=1.0/ppd;
		p3=3.0/ppd;
		p6=6.0/ppd;
		p8=8.0/ppd;
		p12=12.0/ppd;
		p16=16.0/ppd;
		p24=24.0/ppd;

		ok2print=0;
		occupied=0;

		/* Is Marker Position Clear Of Text Or Other Markers? */

		for (a=0, x=lat-p3; (x<=xmax && x>=xmin && a<7); x+=p1, a++)
			for (b=0, y=lon-p3; (LonDiff(y,ymax)<=0.0) && (LonDiff(y,ymin)>=dpp) && b<7; y+=p1, b++)
				occupied|=(GetMask(x,y)&2);

		if (occupied==0)
		{
			/* Determine Where Text Can Be Positioned */

			/* label_length=length in pixels.
			   Each character is 8 pixels wide. */

			label_length=p1*(double)(strlen(location.name)<<3);

			if ((LonDiff(lon+label_length,ymax)<=0.0) && (LonDiff(lon-label_length,ymin)>=dpp))
			{
				/* Default: Centered Text */

				texty=lon+label_length/2.0;

				if ((lat-p8)>=p16)
				{
					/* Position Text Below The Marker */

					textx=lat-p8;

					x=textx;
					y=texty;
	
					/* Is This Position Clear Of
					   Text Or Other Markers? */

					for (a=0, occupied=0; a<16; a++)
					{
						for (b=0; b<(int)strlen(location.name); b++)
							for (c=0; c<8; c++, y-=p1)
								occupied|=(GetMask(x,y)&2);
						x-=p1;
						y=texty;
					}

					x=textx;
					y=texty;

					if (occupied==0)
						ok2print=1;
				}

				else
				{
					/* Position Text Above The Marker */

					textx=lat+p24;

					x=textx;
					y=texty;
	
					/* Is This Position Clear Of
					   Text Or Other Markers? */

					for (a=0, occupied=0; a<16; a++)
					{
						for (b=0; b<(int)strlen(location.name); b++)
							for (c=0; c<8; c++, y-=p1)
								occupied|=(GetMask(x,y)&2);
						x-=p1;
						y=texty;
					}

					x=textx;
					y=texty;

					if (occupied==0)
						ok2print=1;
				}
			}

			if (ok2print==0)
			{
				if (LonDiff(lon-label_length,ymin)>=dpp)
				{
					/* Position Text To The
					   Right Of The Marker */

					textx=lat+p6;
					texty=lon-p12;

					x=textx;
					y=texty;
	
					/* Is This Position Clear Of
					   Text Or Other Markers? */

					for (a=0, occupied=0; a<16; a++)
					{
						for (b=0; b<(int)strlen(location.name); b++)
							for (c=0; c<8; c++, y-=p1)
								occupied|=(GetMask(x,y)&2);
						x-=p1;
						y=texty;
					}

					x=textx;
					y=texty;

					if (occupied==0)
						ok2print=1;
				}

				else
				{
					/* Position Text To The
					   Left Of The Marker */

					textx=lat+p6;
					texty=lon+p8+(label_length);

					x=textx;
					y=texty;
	
					/* Is This Position Clear Of
					   Text Or Other Markers? */

					for (a=0, occupied=0; a<16; a++)
					{
						for (b=0; b<(int)strlen(location.name); b++)
							for (c=0; c<8; c++, y-=p1)
								occupied|=(GetMask(x,y)&2);
						x-=p1;
						y=texty;
					}

					x=textx;
					y=texty;

					if (occupied==0)
						ok2print=1;
				}
			}

			/* textx and texty contain the latitude and longitude
			   coordinates that describe the placement of the text
			   on the map. */
	
			if (ok2print)
			{
				/* Draw Text */

				x=textx;
				y=texty;
				
				for (a=0; a<16; a++)
				{
					for (b=0; b<(int)strlen(location.name); b++)
					{
						byte=fontdata[16*(location.name[b])+a];

						for (c=128; c>0; c=c>>1, y-=p1)
							if (byte&c)
								OrMask(x,y,2);
					}

					x-=p1;
					y=texty;
				}
	
				/* Draw Square Marker Centered
				   On Location Specified */

				for (a=0, x=lat-p3; (x<=xmax && x>=xmin && a<7); x+=p1, a++)
					for (b=0, y=lon-p3; (LonDiff(y,ymax)<=0.0) && (LonDiff(y,ymin)>=dpp) && b<7; y+=p1, b++)
						OrMask(x,y,2);
			}
		}
	}
}

double ReadBearing(char *input)
{
	/* This function takes numeric input in the form of a character
	   string, and returns an equivalent bearing in degrees as a
	   decimal number (double).  The input may either be expressed
	   in decimal format (40.139722) or degree, minute, second
	   format (40 08 23).  This function also safely handles
	   extra spaces found either leading, trailing, or
	   embedded within the numbers expressed in the
	   input string.  Decimal seconds are permitted. */
 
	double	seconds, bearing=0.0;
	char	string[20];
	int	a, b, length, degrees, minutes;

	/* Copy "input" to "string", and ignore any extra
	   spaces that might be present in the process. */

	string[0]=0;
	length=strlen(input);

	for (a=0, b=0; a<length && a<18; a++)
	{
		if ((input[a]!=32 && input[a]!='\n') || (input[a]==32 && input[a+1]!=32 && input[a+1]!='\n' && b!=0))
		{
			string[b]=input[a];
			b++;
		}	 
	}

	string[b]=0;

	/* Count number of spaces in the clean string. */

	length=strlen(string);

	for (a=0, b=0; a<length; a++)
		if (string[a]==32)
			b++;

	if (b==0)  /* Decimal Format (40.139722) */
		sscanf(string,"%lf",&bearing);

	if (b==2)  /* Degree, Minute, Second Format (40 08 23.xx) */
	{
		sscanf(string,"%d %d %lf",&degrees, &minutes, &seconds);

		bearing=fabs((double)degrees);
		bearing+=fabs(((double)minutes)/60.0);
		bearing+=fabs(seconds/3600.0);

		if ((degrees<0) || (minutes<0) || (seconds<0.0))
			bearing=-bearing;
	}

	/* Anything else returns a 0.0 */

	if (bearing>360.0 || bearing<-360.0)
		bearing=0.0;

	return bearing;
}

struct site LoadQTH(char *filename)
{
	/* This function reads SPLAT! .qth (site location) files.
	   The latitude and longitude may be expressed either in
	   decimal degrees, or in degree, minute, second format.
	   Antenna height is assumed to be expressed in feet above
	   ground level (AGL), unless followed by the letter 'M',
	   or 'm', or by the word "meters" or "Meters", in which
	   case meters is assumed, and is handled accordingly. */

	int	x;
	char	string[50], qthfile[255];
	struct	site tempsite;
	FILE	*fd=NULL;

	x=strlen(filename);
	strncpy(qthfile, filename, 254);

	if (qthfile[x-3]!='q' || qthfile[x-2]!='t' || qthfile[x-1]!='h')
	{
		if (x>249)
			qthfile[249]=0;

		strncat(qthfile,".qth\0",5);
	}

	tempsite.lat=91.0;
	tempsite.lon=361.0;
	tempsite.alt=0.0;
	tempsite.name[0]=0;
	tempsite.filename[0]=0;

	fd=fopen(qthfile,"r");

	if (fd!=NULL)
	{
		/* Site Name */
		fgets(string,49,fd);

		/* Strip <CR> and/or <LF> from end of site name */

		for (x=0; string[x]!=13 && string[x]!=10 && string[x]!=0; tempsite.name[x]=string[x], x++);

		tempsite.name[x]=0;

		/* Site Latitude */
		fgets(string,49,fd);
		tempsite.lat=ReadBearing(string);

		/* Site Longitude */
		fgets(string,49,fd);
		tempsite.lon=ReadBearing(string);

		if (tempsite.lon<0.0)
			tempsite.lon+=360.0;

		/* Antenna Height */
		fgets(string,49,fd);
		fclose(fd);

		/* Remove <CR> and/or <LF> from antenna height string */
		for (x=0; string[x]!=13 && string[x]!=10 && string[x]!=0; x++);

		string[x]=0;

		/* Antenna height may either be in feet or meters.
		   If the letter 'M' or 'm' is discovered in
		   the string, then this is an indication that
		   the value given is expressed in meters, and
		   must be converted to feet before exiting. */

		for (x=0; string[x]!='M' && string[x]!='m' && string[x]!=0 && x<48; x++);

		if (string[x]=='M' || string[x]=='m')
		{
			string[x]=0;
			sscanf(string,"%f",&tempsite.alt);
			tempsite.alt*=3.28084;
		}

		else
		{
			string[x]=0;
			sscanf(string,"%f",&tempsite.alt);
		}

		for (x=0; x<254 && qthfile[x]!=0; x++)
			tempsite.filename[x]=qthfile[x];

		tempsite.filename[x]=0;
	}

	return tempsite;
}

void LoadPAT(char *filename)
{
	/* This function reads and processes antenna pattern (.az
	   and .el) files that correspond in name to previously
	   loaded SPLAT! .lrp files.  */

	int	a, b, w, x, y, z, last_index, next_index, span;
	char	string[255], azfile[255], elfile[255], *pointer=NULL;
	float	az, xx, elevation, amplitude, rotation, valid1, valid2,
		delta, azimuth[361], azimuth_pattern[361], el_pattern[10001],
		elevation_pattern[361][1001], slant_angle[361], tilt,
		mechanical_tilt=0.0, tilt_azimuth, tilt_increment, sum;
	FILE	*fd=NULL;
	unsigned char read_count[10001];

	for (x=0; filename[x]!='.' && filename[x]!=0 && x<250; x++)
	{
		azfile[x]=filename[x];
		elfile[x]=filename[x];
	}

	azfile[x]='.';
	azfile[x+1]='a';
	azfile[x+2]='z';
	azfile[x+3]=0;

	elfile[x]='.';
	elfile[x+1]='e';
	elfile[x+2]='l';
	elfile[x+3]=0;

	rotation=0.0;

	got_azimuth_pattern=0;
	got_elevation_pattern=0;

	/* Load .az antenna pattern file */

	fd=fopen(azfile,"r");

	if (fd!=NULL)
	{
		/* Clear azimuth pattern array */

		for (x=0; x<=360; x++)
		{
			azimuth[x]=0.0;
			read_count[x]=0;
		}


		/* Read azimuth pattern rotation
		   in degrees measured clockwise
		   from true North. */

		fgets(string,254,fd);
		pointer=strchr(string,';');

		if (pointer!=NULL)
			*pointer=0;

		sscanf(string,"%f",&rotation);


		/* Read azimuth (degrees) and corresponding
		   normalized field radiation pattern amplitude
		   (0.0 to 1.0) until EOF is reached. */

		fgets(string,254,fd);
		pointer=strchr(string,';');

		if (pointer!=NULL)
			*pointer=0;

		sscanf(string,"%f %f",&az, &amplitude);

		do
		{
			x=(int)rintf(az);

			if (x>=0 && x<=360 && fd!=NULL)
			{
				azimuth[x]+=amplitude;
				read_count[x]++;
			}

			fgets(string,254,fd);
			pointer=strchr(string,';');

			if (pointer!=NULL)
				*pointer=0;

			sscanf(string,"%f %f",&az, &amplitude);

		} while (feof(fd)==0);

		fclose(fd);


		/* Handle 0=360 degree ambiguity */

		if ((read_count[0]==0) && (read_count[360]!=0))
		{
			read_count[0]=read_count[360];
			azimuth[0]=azimuth[360];
		}

		if ((read_count[0]!=0) && (read_count[360]==0))
		{
			read_count[360]=read_count[0];
			azimuth[360]=azimuth[0];
		}

		/* Average pattern values in case more than
		    one was read for each degree of azimuth. */

		for (x=0; x<=360; x++)
		{
			if (read_count[x]>1)
				azimuth[x]/=(float)read_count[x];
		}

		/* Interpolate missing azimuths
		   to completely fill the array */

		last_index=-1;
		next_index=-1;

		for (x=0; x<=360; x++)
		{
			if (read_count[x]!=0)
			{
				if (last_index==-1)
					last_index=x;
				else
					next_index=x;
			}

			if (last_index!=-1 && next_index!=-1)
			{
				valid1=azimuth[last_index];
				valid2=azimuth[next_index];

				span=next_index-last_index;
				delta=(valid2-valid1)/(float)span;

				for (y=last_index+1; y<next_index; y++)
					azimuth[y]=azimuth[y-1]+delta;

				last_index=y;
				next_index=-1;
			}
		}

		/* Perform azimuth pattern rotation
		   and load azimuth_pattern[361] with
		   azimuth pattern data in its final form. */

		for (x=0; x<360; x++)
		{
			y=x+(int)rintf(rotation);

			if (y>=360)
				y-=360;

			azimuth_pattern[y]=azimuth[x];
		}

		azimuth_pattern[360]=azimuth_pattern[0];

		got_azimuth_pattern=255;
	}

	/* Read and process .el file */

	fd=fopen(elfile,"r");

	if (fd!=NULL)
	{
		for (x=0; x<=10000; x++)
		{
			el_pattern[x]=0.0;
			read_count[x]=0;
		}

		/* Read mechanical tilt (degrees) and
		   tilt azimuth in degrees measured
		   clockwise from true North. */  

		fgets(string,254,fd);
		pointer=strchr(string,';');

		if (pointer!=NULL)
			*pointer=0;

		sscanf(string,"%f %f",&mechanical_tilt, &tilt_azimuth);

		/* Read elevation (degrees) and corresponding
		   normalized field radiation pattern amplitude
		   (0.0 to 1.0) until EOF is reached. */

		fgets(string,254,fd);
		pointer=strchr(string,';');

		if (pointer!=NULL)
			*pointer=0;

		sscanf(string,"%f %f", &elevation, &amplitude);

		while (feof(fd)==0)
		{
			/* Read in normalized radiated field values
			   for every 0.01 degrees of elevation between
			   -10.0 and +90.0 degrees */

			x=(int)rintf(100.0*(elevation+10.0));

			if (x>=0 && x<=10000)
			{
				el_pattern[x]+=amplitude;
				read_count[x]++;
			}

			fgets(string,254,fd);
			pointer=strchr(string,';');

			if (pointer!=NULL)
				*pointer=0;

			sscanf(string,"%f %f", &elevation, &amplitude);
		}

		fclose(fd);

		/* Average the field values in case more than
		   one was read for each 0.01 degrees of elevation. */

		for (x=0; x<=10000; x++)
		{
			if (read_count[x]>1)
				el_pattern[x]/=(float)read_count[x];
		}

		/* Interpolate between missing elevations (if
		   any) to completely fill the array and provide
		   radiated field values for every 0.01 degrees of
		   elevation. */

		last_index=-1;
		next_index=-1;

		for (x=0; x<=10000; x++)
		{
			if (read_count[x]!=0)
			{
				if (last_index==-1)
					last_index=x;
				else
					next_index=x;
			}

			if (last_index!=-1 && next_index!=-1)
			{
				valid1=el_pattern[last_index];
				valid2=el_pattern[next_index];

				span=next_index-last_index;
				delta=(valid2-valid1)/(float)span;

				for (y=last_index+1; y<next_index; y++)
					el_pattern[y]=el_pattern[y-1]+delta;

				last_index=y;
				next_index=-1;
			}
		}

		/* Fill slant_angle[] array with offset angles based
		   on the antenna's mechanical beam tilt (if any)
		   and tilt direction (azimuth). */

		if (mechanical_tilt==0.0)
		{
			for (x=0; x<=360; x++)
				slant_angle[x]=0.0;
		}

		else
		{
			tilt_increment=mechanical_tilt/90.0;

			for (x=0; x<=360; x++)
			{
				xx=(float)x;
				y=(int)rintf(tilt_azimuth+xx);

				while (y>=360)
					y-=360;

				while (y<0)
					y+=360;

				if (x<=180)
					slant_angle[y]=-(tilt_increment*(90.0-xx));

				if (x>180)
					slant_angle[y]=-(tilt_increment*(xx-270.0));
			}
		}

		slant_angle[360]=slant_angle[0];   /* 360 degree wrap-around */

		for (w=0; w<=360; w++)
		{
			tilt=slant_angle[w];

			/** Convert tilt angle to
			    an array index offset **/

			y=(int)rintf(100.0*tilt);

			/* Copy shifted el_pattern[10001] field
			   values into elevation_pattern[361][1001]
			   at the corresponding azimuth, downsampling
			   (averaging) along the way in chunks of 10. */

			for (x=y, z=0; z<=1000; x+=10, z++)
			{
				for (sum=0.0, a=0; a<10; a++)
				{
					b=a+x;

					if (b>=0 && b<=10000)
						sum+=el_pattern[b];
					if (b<0)
						sum+=el_pattern[0];
					if (b>10000)
						sum+=el_pattern[10000];
				}

				elevation_pattern[w][z]=sum/10.0;
			}
		}

		got_elevation_pattern=255;
	}

	for (x=0; x<=360; x++)
	{
		for (y=0; y<=1000; y++)
		{
			if (got_elevation_pattern)
				elevation=elevation_pattern[x][y];
			else
				elevation=1.0;

			if (got_azimuth_pattern)
				az=azimuth_pattern[x];
			else
				az=1.0;

			LR.antenna_pattern[x][y]=az*elevation;
		}
	}
}

int LoadSDF_SDF(char *name)
{
	/* This function reads uncompressed SPLAT Data Files (.sdf)
	   containing digital elevation model data into memory.
	   Elevation data, maximum and minimum elevations, and
	   quadrangle limits are stored in the first available
	   dem[] structure. */

	int	x, y, data, indx, minlat, minlon, maxlat, maxlon;
	char	found, free_page=0, line[20], sdf_file[255],
		path_plus_name[512];
	FILE	*fd;

	//fprintf(stdout, "LoadSDF_SDF: ok1 \n ");
	//fprintf(stdout,"-------------------> Loading \%s\: ", name);
	 // GET SHARED MEM FOR DEM
	auto region_read = bi::mapped_region{shm, bi::read_write}; 
	void* pMem_read = region_read.get_address();
	short* arr_read = static_cast<short*>(pMem_read);
	//fprintf(stdout, "LoadSDF_SDF: ok2 \n ");


	
	for (x=0; name[x]!='.' && name[x]!=0 && x<250; x++)
		sdf_file[x]=name[x];

	sdf_file[x]=0;

	/* Parse filename for minimum latitude and longitude values */

	sscanf(sdf_file,"%d:%d:%d:%d",&minlat,&maxlat,&minlon,&maxlon);

	sdf_file[x]='.';
	sdf_file[x+1]='s';
	sdf_file[x+2]='d';
	sdf_file[x+3]='f';
	sdf_file[x+4]=0;

	/* Is it already in memory? */

	for (indx=0, found=0; indx<MAXPAGES && found==0; indx++)
	{
		if (minlat==dem[indx].min_north && minlon==dem[indx].min_west && maxlat==dem[indx].max_north && maxlon==dem[indx].max_west)
			found=1;
	}

	/* Is room available to load it? */

	if (found==0)
	{	
		for (indx=0, free_page=0; indx<MAXPAGES && free_page==0; indx++)
			if (dem[indx].max_north==-90)
				free_page=1;
	}

	indx--;

	if (free_page && found==0 && indx>=0 && indx<MAXPAGES)
	{
		/* Search for SDF file in current working directory first */

		strncpy(path_plus_name,sdf_file,255);

		fd=fopen(path_plus_name,"rb");

		fprintf(stdout,"-------------------> sdf_path \%s\: ", sdf_path);

		if (fd==NULL)
		{
			/* Next, try loading SDF file from path specified
			   in $HOME/.splat_path file or by -d argument */

			strncpy(path_plus_name,sdf_path,255);
			strncat(path_plus_name,sdf_file,254);

			fd=fopen(path_plus_name,"rb");
		}

		if (fd!=NULL)
		{
		  //fprintf(stdout,"Loading \"%s\" into page %d...",path_plus_name,indx+1);
		  //	fflush(stdout);

			fgets(line,19,fd);
			sscanf(line,"%d",&dem[indx].max_west);

			fgets(line,19,fd);
			sscanf(line,"%d",&dem[indx].min_north);

			fgets(line,19,fd);
			sscanf(line,"%d",&dem[indx].min_west);

			fgets(line,19,fd);
			sscanf(line,"%d",&dem[indx].max_north);

			for (x=0; x<ippd; x++)
				for (y=0; y<ippd; y++)
				{
					fgets(line,19,fd);
					data=atoi(line);

					arr_read[indx*IPPD*IPPD+x*IPPD+y] = data; // parallelizable code
  
					dem[indx].signal[x][y]=0;
					dem[indx].mask[x][y]=0;

					if (data>dem[indx].max_el){
					  dem[indx].max_el=data; 
					  
					}
					

					if (data<dem[indx].min_el){
					  dem[indx].min_el=data; 
					  
					}
					
				}

			fclose(fd);

			if (dem[indx].min_el<min_elevation)
				min_elevation=dem[indx].min_el;

			if (dem[indx].max_el>max_elevation)
				max_elevation=dem[indx].max_el;

			if (max_north==-90)
				max_north=dem[indx].max_north;

			else if (dem[indx].max_north>max_north)
					max_north=dem[indx].max_north;

			if (min_north==90)
				min_north=dem[indx].min_north;

			else if (dem[indx].min_north<min_north)
					min_north=dem[indx].min_north;

			if (max_west==-1)
				max_west=dem[indx].max_west;

			else
			{
				if (abs(dem[indx].max_west-max_west)<180)
				{
 					if (dem[indx].max_west>max_west)
						max_west=dem[indx].max_west;
				}

				else
				{
 					if (dem[indx].max_west<max_west)
						max_west=dem[indx].max_west;
				}
			}

			if (min_west==360)
				min_west=dem[indx].min_west;

			else
			{
				if (fabs(dem[indx].min_west-min_west)<180.0)
				{
 					if (dem[indx].min_west<min_west)
						min_west=dem[indx].min_west;
				}

				else
				{
 					if (dem[indx].min_west>min_west)
						min_west=dem[indx].min_west;
				}
			}

			//fprintf(stdout," Done!\n");
			//fflush(stdout);

			return 1;
		}

		else
			return -1;
	}

	else
		return 0;
}

char *BZfgets(BZFILE *bzfd, unsigned length)
{
	/* This function returns at most one less than 'length' number
	   of characters from a bz2 compressed file whose file descriptor
	   is pointed to by *bzfd.  In operation, a buffer is filled with
	   uncompressed data (size = BZBUFFER), which is then parsed
	   and doled out as NULL terminated character strings every time
	   this function is invoked.  A NULL string indicates an EOF
	   or error condition. */

	static int x, y, nBuf;
	static char buffer[BZBUFFER+1], output[BZBUFFER+1];
	char done=0;

	if (opened!=1 && bzerror==BZ_OK)
	{
		/* First time through.  Initialize everything! */

		x=0;
		y=0;
		nBuf=0;
		opened=1;
		output[0]=0;
	}

	do
	{
		if (x==nBuf && bzerror!=BZ_STREAM_END && bzerror==BZ_OK && opened)
		{
			/* Uncompress data into a static buffer */

			nBuf=BZ2_bzRead(&bzerror, bzfd, buffer, BZBUFFER);
			buffer[nBuf]=0;
			x=0;
		}

		/* Build a string from buffer contents */

		output[y]=buffer[x];

		if (output[y]=='\n' || output[y]==0 || y==(int)length-1)
		{
			output[y+1]=0;
			done=1;
			y=0;
		}

		else
			y++;
		x++;

	} while (done==0);

	if (output[0]==0)
		opened=0;

	return (output);
}


char LoadSDF(char *name)
{
	/* This function loads the requested SDF file from the filesystem.
	   It first tries to invoke the LoadSDF_SDF() function to load an
	   uncompressed SDF file (since uncompressed files load slightly
	   faster).  If that attempt fails, then it tries to load a
	   compressed SDF file by invoking the LoadSDF_BZ() function.
	   If that fails, then we can assume that no elevation data
	   exists for the region requested, and that the region
	   requested must be entirely over water. */

  int	x, y, indx, minlat, minlon, maxlat, maxlon;
  char	found, free_page=0;
  int	return_value=-1;


  // GET SHARED MEM FOR DEM 
  auto region_read = bi::mapped_region{shm, bi::read_write}; // this has to be here, and not globally declared..if not there is a segementation fault
  void* pMem_read = region_read.get_address();
  short* arr_read = static_cast<short*>(pMem_read);
  
  
  /* Try to load an uncompressed SDF first. */
  
  return_value=LoadSDF_SDF(name);
  fprintf(stdout, "LoadSDF, name = %s, ret_val = %d \n", name, return_value);
  
  
  
  /* If neither format can be found, then assume the area is water. */
  if (return_value==0 || return_value==-1)
    {
      fprintf(stdout, "LoadSDF_SDF failed...assuming water level 0masl\n");
      
      /* Parse SDF name for minimum latitude and longitude values */
      
      sscanf(name,"%d:%d:%d:%d",&minlat,&maxlat,&minlon,&maxlon);
      
      /* Is it already in memory? */
      
      for (indx=0, found=0; indx<MAXPAGES && found==0; indx++) 
	{
	  if (minlat==dem[indx].min_north && minlon==dem[indx].min_west && maxlat==dem[indx].max_north && maxlon==dem[indx].max_west) 
	    found=1;
	}
      
      /* Is room available to load it? */
      
      if (found==0)
	{	
	  for (indx=0, free_page=0; indx<MAXPAGES && free_page==0; indx++)
	    if (dem[indx].max_north==-90) 
	      free_page=1;
	}
      
      indx--;
      
      if (free_page && found==0 && indx>=0 && indx<MAXPAGES)
	{
	  
	  fprintf(stdout,"Region  \"%s\" assumed as sea-level into page %d...",name,indx+1);
	  fflush(stdout);
	  
	  dem[indx].max_west=maxlon; 
	  dem[indx].min_north=minlat; 
	  dem[indx].min_west=minlon; 
	  dem[indx].max_north=maxlat; 
	  
	  
	  
	  /* Fill DEM with sea-level topography */
	  
	  for (x=0; x<ippd; x++)
	    for (y=0; y<ippd; y++)
	      {
		dem[indx].data[x][y]=0; 
		dem[indx].signal[x][y]=0;
		dem[indx].mask[x][y]=0;
		
		if (dem[indx].min_el>0){
		  dem[indx].min_el=0; 
		  
		}
		
	      }
	  
	  if (dem[indx].min_el<min_elevation) 
	    min_elevation=dem[indx].min_el;
	  
	  if (dem[indx].max_el>max_elevation)
	    max_elevation=dem[indx].max_el;
	  
	  if (max_north==-90)
	    max_north=dem[indx].max_north;
	  
	  else if (dem[indx].max_north>max_north)
	    max_north=dem[indx].max_north;
	  
	  if (min_north==90)
	    min_north=dem[indx].min_north;
	  
	  else if (dem[indx].min_north<min_north)
	    min_north=dem[indx].min_north;
	  
	  if (max_west==-1)
	    max_west=dem[indx].max_west;
	  
	  else
	    {
	      if (abs(dem[indx].max_west-max_west)<180)
		{
		  if (dem[indx].max_west>max_west)
		    max_west=dem[indx].max_west;
		}
	      
	      else
		{
		  if (dem[indx].max_west<max_west)
		    max_west=dem[indx].max_west;
		}
	    }
	  
	  if (min_west==360)
	    min_west=dem[indx].min_west;
	  
	  else
	    {
	      if (abs(dem[indx].min_west-min_west)<180)
		{
		  if (dem[indx].min_west<min_west)
		    min_west=dem[indx].min_west;
		}
	      
	      else
		{
		  if (dem[indx].min_west>min_west)
		    min_west=dem[indx].min_west;
		}
	    }
	  
	  return_value=1;
	}
    }

  if (nof_loaded_pages >= MAXPAGES){ // this is a big error..
    fprintf(stdout , "@@@@@@@@@@@@@@@@@@@@@@@@@@ loaded pages exceeds MAXPAGES= %d; exiting!!!! \n ", MAXPAGES);
    exit (EXIT_FAILURE);
  }


  if (return_value == 1){
    nof_loaded_pages = nof_loaded_pages + 1;
    fprintf(stdout , "returning from LoadSDF, loaded pages = %d \n ", nof_loaded_pages);
  }
  return return_value;
}

void LoadCities(char *filename)
{
	/* This function reads SPLAT! city/site files, and plots
	   the locations and names of the cities and site locations
	   read on topographic maps generated by SPLAT! */

	int	x, y, z;
	char	input[80], str[3][80];
	struct	site city_site;
	FILE	*fd=NULL;

	fd=fopen(filename,"r");

	if (fd!=NULL)
	{
		fgets(input,78,fd);

		fprintf(stdout,"\nReading \"%s\"... ",filename);
		fflush(stdout);

		while (fd!=NULL && feof(fd)==0)
		{
			/* Parse line for name, latitude, and longitude */

			for (x=0, y=0, z=0; x<78 && input[x]!=0 && z<3; x++)
			{
				if (input[x]!=',' && y<78)
				{
					str[z][y]=input[x];
					y++;
				}

				else
				{
					str[z][y]=0;
					z++;
					y=0;
				}
			}

			strncpy(city_site.name,str[0],49);
			city_site.lat=ReadBearing(str[1]);
			city_site.lon=ReadBearing(str[2]);
			city_site.alt=0.0;

			if (city_site.lon<0.0)
				city_site.lon+=360.0;

			PlaceMarker(city_site);

			fgets(input,78,fd);
		}

		fclose(fd);
		
	}

	else
		fprintf(stderr,"\n*** ERROR: \"%s\": not found!",filename);
}

void LoadUDT(char *filename)
{
	/* This function reads a file containing User-Defined Terrain
	   features for their addition to the digital elevation model
	   data used by SPLAT!.  Elevations in the UDT file are evaluated
	   and then copied into a temporary file under /tmp.  Then the
	   contents of the temp file are scanned, and if found to be unique,
	   are added to the ground elevations described by the digital
	   elevation data already loaded into memory. */

	int	i, x, y, z, ypix, xpix, tempxpix, tempypix, fd=0;
	char	input[80], str[3][80], tempname[15], *pointer=NULL;
	double	latitude, longitude, height, tempheight;
	FILE	*fd1=NULL, *fd2=NULL;

	strcpy(tempname,"/tmp/XXXXXX\0");

	fd1=fopen(filename,"r");

	if (fd1!=NULL)
	{
		fd=mkstemp(tempname);
		fd2=fopen(tempname,"w");

		fgets(input,78,fd1);

		pointer=strchr(input,';');

		if (pointer!=NULL)
			*pointer=0;

		fprintf(stdout,"\nReading \"%s\"... ",filename);
		fflush(stdout);

		while (feof(fd1)==0)
		{
			/* Parse line for latitude, longitude, height */

			for (x=0, y=0, z=0; x<78 && input[x]!=0 && z<3; x++)
			{
				if (input[x]!=',' && y<78)
				{
					str[z][y]=input[x];
					y++;
				}

				else
				{
					str[z][y]=0;
					z++;
					y=0;
				}
			}

			latitude=ReadBearing(str[0]);
			longitude=ReadBearing(str[1]);

			if (longitude<0.0)
				longitude+=360.0;

			/* Remove <CR> and/or <LF> from antenna height string */

			for (i=0; str[2][i]!=13 && str[2][i]!=10 && str[2][i]!=0; i++);

			str[2][i]=0;

			/* The terrain feature may be expressed in either
			   feet or meters.  If the letter 'M' or 'm' is
			   discovered in the string, then this is an
			   indication that the value given is expressed
			   in meters.  Otherwise the height is interpreted
			   as being expressed in feet.  */

			for (i=0; str[2][i]!='M' && str[2][i]!='m' && str[2][i]!=0 && i<48; i++);

			if (str[2][i]=='M' || str[2][i]=='m')
			{
				str[2][i]=0;
				height=rint(atof(str[2]));
			}

			else
			{
				str[2][i]=0;
				height=rint(METERS_PER_FOOT*atof(str[2]));
			}

			if (height>0.0)
				fprintf(fd2,"%d, %d, %f\n",(int)rint(latitude/dpp), (int)rint(longitude/dpp), height);

			fgets(input,78,fd1);

			pointer=strchr(input,';');

			if (pointer!=NULL)
				*pointer=0;
		}

		fclose(fd1);
		fclose(fd2);
		close(fd);

		fd1=fopen(tempname,"r");
		fd2=fopen(tempname,"r");

		y=0;

		fscanf(fd1,"%d, %d, %lf", &xpix, &ypix, &height);

		do
		{
			x=0;
			z=0;

			fscanf(fd2,"%d, %d, %lf", &tempxpix, &tempypix, &tempheight);

			do
			{
				if (x>y && xpix==tempxpix && ypix==tempypix)
				{
						z=1;  /* Dupe! */

						if (tempheight>height)
							height=tempheight;
				}

				else
				{
					fscanf(fd2,"%d, %d, %lf", &tempxpix, &tempypix, &tempheight);
					x++;
				}

			} while (feof(fd2)==0 && z==0);

			if (z==0)  /* No duplicate found */
				AddElevation(xpix*dpp, ypix*dpp, height);

			fscanf(fd1,"%d, %d, %lf", &xpix, &ypix, &height);
			y++;

			rewind(fd2);

		} while (feof(fd1)==0);

		fclose(fd1);
		fclose(fd2);
		unlink(tempname);
	}

	else
		fprintf(stderr,"\n*** ERROR: \"%s\": not found!",filename);

	fprintf(stdout,"\n");
}

void LoadBoundaries(char *filename)
{
	/* This function reads Cartographic Boundary Files available from
	   the U.S. Census Bureau, and plots the data contained in those
	   files on the PPM Map generated by SPLAT!.  Such files contain
	   the coordinates that describe the boundaries of cities,
	   counties, and states. */

	int	x;
	double	lat0, lon0, lat1, lon1;
	char	string[80];
	struct	site source, destination;
	FILE	*fd=NULL;

	fd=fopen(filename,"r");

	if (fd!=NULL)
	{
		fgets(string,78,fd);

		fprintf(stdout,"\nReading \"%s\"... ",filename);
		fflush(stdout);

		do
		{
			fgets(string,78,fd);
			sscanf(string,"%lf %lf", &lon0, &lat0);
			fgets(string,78,fd);

			do
			{
				sscanf(string,"%lf %lf", &lon1, &lat1);

				source.lat=lat0;
				source.lon=(lon0>0.0 ? 360.0-lon0 : -lon0);
				destination.lat=lat1;
				destination.lon=(lon1>0.0 ? 360.0-lon1 : -lon1);

				ReadPath(source,destination);

				for (x=0; x<path.length; x++)
					OrMask(path.lat[x],path.lon[x],4);

				lat0=lat1;
				lon0=lon1;

				fgets(string,78,fd);

			} while (strncmp(string,"END",3)!=0 && feof(fd)==0);

			fgets(string,78,fd);

		} while (strncmp(string,"END",3)!=0 && feof(fd)==0);

		fclose(fd);

		//fprintf(stdout,"Done!");
		//fflush(stdout);
	}

	else
		fprintf(stderr,"\n*** ERROR: \"%s\": not found!",filename);
}

char ReadLRParm(struct site txsite, char forced_read)
{
	/* This function reads ITM parameter data for the transmitter
	   site.  The file name is the same as the txsite, except the
	   filename extension is .lrp.  If the needed file is not found,
	   then the file "splat.lrp" is read from the current working
	   directory.  Failure to load this file under a forced_read
	   condition will result in the default parameters hard coded
	   into this function to be used and written to "splat.lrp". */

	double	din;
	char	filename[255], string[80], *pointer=NULL, return_value=0;
	int	iin, ok=0, x;
	FILE	*fd=NULL, *outfile=NULL;

	/* Default parameters */

	LR.eps_dielect=0.0;
	LR.sgm_conductivity=0.0;
	LR.eno_ns_surfref=0.0;
	LR.frq_mhz=0.0;
	LR.radio_climate=0;
	LR.pol=0;
	LR.conf=0.0;
	LR.rel=0.0;
	LR.erp=0.0;

	/* Generate .lrp filename from txsite filename. */

	for (x=0; txsite.filename[x]!='.' && txsite.filename[x]!=0 && x<250; x++)
		filename[x]=txsite.filename[x];

	filename[x]='.';
	filename[x+1]='l';
	filename[x+2]='r';
	filename[x+3]='p';
	filename[x+4]=0;

	fd=fopen(filename,"r");

	if (fd==NULL)
	{
		/* Load default "splat.lrp" file */

		strncpy(filename,"splat.lrp\0",10);
		fd=fopen(filename,"r");
	}

	if (fd!=NULL)
	{
		fgets(string,80,fd);

		pointer=strchr(string,';');

		if (pointer!=NULL)
			*pointer=0;

		ok=sscanf(string,"%lf", &din);

		if (ok)
		{
			LR.eps_dielect=din;

			fgets(string,80,fd);

			pointer=strchr(string,';');

			if (pointer!=NULL)
				*pointer=0;

			ok=sscanf(string,"%lf", &din);
		}

		if (ok)
		{
			LR.sgm_conductivity=din;

			fgets(string,80,fd);

			pointer=strchr(string,';');

			if (pointer!=NULL)
				*pointer=0;

			ok=sscanf(string,"%lf", &din);
		}

		if (ok)
		{
			LR.eno_ns_surfref=din;

			fgets(string,80,fd);

			pointer=strchr(string,';');

			if (pointer!=NULL)
				*pointer=0;

			ok=sscanf(string,"%lf", &din);
		}

		if (ok)
		{
			LR.frq_mhz=din;

			fgets(string,80,fd);

			pointer=strchr(string,';');

			if (pointer!=NULL)
				*pointer=0;

			ok=sscanf(string,"%d", &iin);
		}

		if (ok)
		{
			LR.radio_climate=iin;

			fgets(string,80,fd);

			pointer=strchr(string,';');

			if (pointer!=NULL)
				*pointer=0;

			ok=sscanf(string,"%d", &iin);
		}

		if (ok)
		{
			LR.pol=iin;

			fgets(string,80,fd);

			pointer=strchr(string,';');

			if (pointer!=NULL)
				*pointer=0;

			ok=sscanf(string,"%lf", &din);
		}

		if (ok)
		{
			LR.conf=din;

			fgets(string,80,fd);

			pointer=strchr(string,';');

			if (pointer!=NULL)
				*pointer=0;

			ok=sscanf(string,"%lf", &din);
		}

		if (ok)
		{
			LR.rel=din;
			din=0.0;
			return_value=1;

			if (fgets(string,80,fd)!=NULL)
			{
				pointer=strchr(string,';');

				if (pointer!=NULL)
					*pointer=0;

				if (sscanf(string,"%lf", &din))
					LR.erp=din;

				/* ERP in SPLAT! is referenced to 1 Watt
				   into a dipole (0 dBd).  If ERP is
				   expressed in dBm (referenced to a
				   0 dBi radiator), convert dBm in EIRP
				   to ERP.  */

				if ((strstr(string, "dBm")!=NULL) || (strstr(string,"dbm")!=NULL))
					LR.erp=(pow(10.0,(LR.erp-32.14)/10.0));
			}
		}

		fclose(fd);

		if (forced_erp!=-1.0)
			LR.erp=forced_erp;

		if (forced_freq>=20.0 && forced_freq<=20000.0)
			LR.frq_mhz=forced_freq;

		if (ok)
			LoadPAT(filename);
	} 

	if (fd==NULL && forced_read)
	{
		/* Assign some default parameters
		   for use in this run. */

		LR.eps_dielect=15.0;
		LR.sgm_conductivity=0.005;
		LR.eno_ns_surfref=301.0;
		LR.frq_mhz=300.0;
		LR.radio_climate=5;
		LR.pol=0;
		LR.conf=0.50;
		LR.rel=0.50;
		LR.erp=0.0;

		/* Write them to a "splat.lrp" file. */

		outfile=fopen("splat.lrp","w");

		fprintf(outfile,"%.3f\t; Earth Dielectric Constant (Relative permittivity)\n",LR.eps_dielect);
		fprintf(outfile,"%.3f\t; Earth Conductivity (Siemens per meter)\n", LR.sgm_conductivity);
		fprintf(outfile,"%.3f\t; Atmospheric Bending Constant (N-Units)\n",LR.eno_ns_surfref);
		fprintf(outfile,"%.3f\t; Frequency in MHz (20 MHz to 20 GHz)\n", LR.frq_mhz);
		fprintf(outfile,"%d\t; Radio Climate\n",LR.radio_climate);
		fprintf(outfile,"%d\t; Polarization (0 = Horizontal, 1 = Vertical)\n", LR.pol);
		fprintf(outfile,"%.2f\t; Fraction of Situations\n",LR.conf);
		fprintf(outfile,"%.2f\t; Fraction of Time\n",LR.rel);
		fprintf(outfile,"%.2f\t; Transmitter Effective Radiated Power in Watts or dBm (optional)\n",LR.erp);
		fprintf(outfile,"\nPlease consult SPLAT! documentation for the meaning and use of this data.\n");

		fclose(outfile);

		return_value=1;

		fprintf(stderr,"\n\n%c*** There were problems reading your \"%s\" file! ***\nA \"splat.lrp\" file was written to your directory with default data.\n",7,filename);
	}

	else if (forced_read==0)
			return_value=0;

	if (forced_read && (fd==NULL || ok==0))
	{
		LR.eps_dielect=15.0;
		LR.sgm_conductivity=0.005;
		LR.eno_ns_surfref=301.0;
		LR.frq_mhz=300.0;
		LR.radio_climate=5;
		LR.pol=0;
		LR.conf=0.50;
		LR.rel=0.50;
		LR.erp=0.0;

		fprintf(stderr,"Default parameters have been assumed for this analysis.\n");

		return_value=1;
	}

	return (return_value);
}

void PlotPath(struct site source, struct site destination, char mask_value)
{
	/* This function analyzes the path between the source and
	   destination locations.  It determines which points along
	   the path have line-of-sight visibility to the source.
	   Points along with path having line-of-sight visibility
	   to the source at an AGL altitude equal to that of the
	   destination location are stored by setting bit 1 in the
	   mask[][] array, which are displayed in green when PPM
	   maps are later generated by SPLAT!. */

	char block;
	int x, y;
	register double cos_xmtr_angle, cos_test_angle, test_alt;
	double distance, rx_alt, tx_alt;

	ReadPath(source,destination);

	for (y=0; y<path.length; y++)
	{
		/* Test this point only if it hasn't been already
		   tested and found to be free of obstructions. */

		if ((GetMask(path.lat[y],path.lon[y])&mask_value)==0)
		{
			distance=5280.0*path.distance[y];
			tx_alt=earthradius+source.alt+path.elevation[0];
			rx_alt=earthradius+destination.alt+path.elevation[y];

			/* Calculate the cosine of the elevation of the
			   transmitter as seen at the temp rx point. */

			cos_xmtr_angle=((rx_alt*rx_alt)+(distance*distance)-(tx_alt*tx_alt))/(2.0*rx_alt*distance);

			for (x=y, block=0; x>=0 && block==0; x--)
			{
				distance=5280.0*(path.distance[y]-path.distance[x]);
				test_alt=earthradius+(path.elevation[x]==0.0?path.elevation[x]:path.elevation[x]+clutter);

				cos_test_angle=((rx_alt*rx_alt)+(distance*distance)-(test_alt*test_alt))/(2.0*rx_alt*distance);

				/* Compare these two angles to determine if
				   an obstruction exists.  Since we're comparing
				   the cosines of these angles rather than
				   the angles themselves, the following "if"
				   statement is reversed from what it would
				   be if the actual angles were compared. */

				if (cos_xmtr_angle>=cos_test_angle)
					block=1;
			}

			if (block==0)
				OrMask(path.lat[y],path.lon[y],mask_value);
		}
	}
}

void PlotLRPath(struct site source, struct site destination, unsigned char mask_value, FILE *fd)
{
	/* This function plots the RF path loss between source and
	   destination points based on the ITWOM propagation model,
	   taking into account antenna pattern data, if available. */

	int	x, y, ifs, ofs, errnum;
	char	block=0, strmode[100];
	double	loss, azimuth, pattern=0.0, xmtr_alt,
		dest_alt, xmtr_alt2, dest_alt2, cos_rcvr_angle,
		cos_test_angle=0.0, test_alt, elevation=0.0,
		distance=0.0, four_thirds_earth, rxp, dBm,
		field_strength=0.0;
	struct	site temp;

	ReadPath(source,destination);

	four_thirds_earth=FOUR_THIRDS*EARTHRADIUS;

	/* Copy elevations plus clutter along path into the elev[] array. */

	for (x=1; x<path.length-1; x++)
		elev[x+2]=(path.elevation[x]==0.0?path.elevation[x]*METERS_PER_FOOT:(clutter+path.elevation[x])*METERS_PER_FOOT);

	/* Copy ending points without clutter */

	elev[2]=path.elevation[0]*METERS_PER_FOOT;
	elev[path.length+1]=path.elevation[path.length-1]*METERS_PER_FOOT;

	/* Since the only energy the propagation model considers
	   reaching the destination is based on what is scattered
	   or deflected from the first obstruction along the path,
	   we first need to find the location and elevation angle
	   of that first obstruction (if it exists).  This is done
	   using a 4/3rds Earth radius to match the radius used by
	   the irregular terrain propagation model.  This information
	   is required for properly integrating the antenna's elevation
	   pattern into the calculation for overall path loss. */

	for (y=2; (y<(path.length-1) && path.distance[y]<=max_range); y++)
	{
		/* Process this point only if it
		   has not already been processed. */

		if ((GetMask(path.lat[y],path.lon[y])&248)!=(mask_value<<3))
		{
			distance=5280.0*path.distance[y];
			xmtr_alt=four_thirds_earth+source.alt+path.elevation[0];
			dest_alt=four_thirds_earth+destination.alt+path.elevation[y];
			dest_alt2=dest_alt*dest_alt;
			xmtr_alt2=xmtr_alt*xmtr_alt;

			/* Calculate the cosine of the elevation of
			   the receiver as seen by the transmitter. */

			cos_rcvr_angle=((xmtr_alt2)+(distance*distance)-(dest_alt2))/(2.0*xmtr_alt*distance);

			if (cos_rcvr_angle>1.0)
				cos_rcvr_angle=1.0;

			if (cos_rcvr_angle<-1.0)
				cos_rcvr_angle=-1.0;

			if (got_elevation_pattern || fd!=NULL)
			{
				/* Determine the elevation angle to the first obstruction
				   along the path IF elevation pattern data is available
				   or an output (.ano) file has been designated. */

				for (x=2, block=0; (x<y && block==0); x++)
				{
					distance=5280.0*path.distance[x];

					test_alt=four_thirds_earth+(path.elevation[x]==0.0?path.elevation[x]:path.elevation[x]+clutter);

					/* Calculate the cosine of the elevation
					   angle of the terrain (test point)
					   as seen by the transmitter. */

					cos_test_angle=((xmtr_alt2)+(distance*distance)-(test_alt*test_alt))/(2.0*xmtr_alt*distance);

					if (cos_test_angle>1.0)
						cos_test_angle=1.0;

					if (cos_test_angle<-1.0)
						cos_test_angle=-1.0;

					/* Compare these two angles to determine if
					   an obstruction exists.  Since we're comparing
					   the cosines of these angles rather than
					   the angles themselves, the sense of the
					   following "if" statement is reversed from
				  	   what it would be if the angles themselves
					   were compared. */

					if (cos_rcvr_angle>=cos_test_angle)
						block=1;
				}

				if (block)
					elevation=((acos(cos_test_angle))/DEG2RAD)-90.0;
				else
					elevation=((acos(cos_rcvr_angle))/DEG2RAD)-90.0;
			}

			/* Determine attenuation for each point along
			   the path using ITWOM's point_to_point mode
			   starting at y=2 (number_of_points = 1), the
			   shortest distance terrain can play a role in
			   path loss. */
 
			elev[0]=y-1;  /* (number of points - 1) */

			/* Distance between elevation samples */

			elev[1]=METERS_PER_MILE*(path.distance[y]-path.distance[y-1]);

			if (olditm)
				point_to_point_ITM(elev,source.alt*METERS_PER_FOOT, 
  		 		destination.alt*METERS_PER_FOOT, LR.eps_dielect,
				LR.sgm_conductivity, LR.eno_ns_surfref, LR.frq_mhz,
				LR.radio_climate, LR.pol, LR.conf, LR.rel, loss,
				strmode, errnum);

			else
				point_to_point(elev,source.alt*METERS_PER_FOOT, 
  	 			destination.alt*METERS_PER_FOOT, LR.eps_dielect,
				LR.sgm_conductivity, LR.eno_ns_surfref, LR.frq_mhz,
				LR.radio_climate, LR.pol, LR.conf, LR.rel, loss,
				strmode, errnum);

			temp.lat=path.lat[y];
			temp.lon=path.lon[y];

			azimuth=(Azimuth(source,temp));

			if (fd!=NULL)
				fprintf(fd,"%.7f, %.7f, %.3f, %.3f, ",path.lat[y], path.lon[y], azimuth, elevation);

			/* If ERP==0, write path loss to alphanumeric
			   output file.  Otherwise, write field strength
			   or received power level (below), as appropriate. */

			if (fd!=NULL && LR.erp==0.0)
				fprintf(fd,"%.2f",loss);

			/* Integrate the antenna's radiation
			   pattern into the overall path loss. */

			x=(int)rint(10.0*(10.0-elevation));

			if (x>=0 && x<=1000)
			{
				azimuth=rint(azimuth);

				pattern=(double)LR.antenna_pattern[(int)azimuth][x];

				if (pattern!=0.0)
				{
					pattern=20.0*log10(pattern);
					loss-=pattern;
				}
			}

			if (LR.erp!=0.0)
			{
				if (dbm)
				{
					/* dBm is based on EIRP (ERP + 2.14) */

					rxp=LR.erp/(pow(10.0,(loss-2.14)/10.0));

					dBm=10.0*(log10(rxp*1000.0));

					if (fd!=NULL)
						fprintf(fd,"%.3f",dBm);

					/* Scale roughly between 0 and 255 */

					ifs=200+(int)rint(dBm);

					if (ifs<0)
						ifs=0;

					if (ifs>255)
						ifs=255;

					ofs=GetSignal(path.lat[y],path.lon[y]);

					if (ofs>ifs)
						ifs=ofs;

					PutSignal(path.lat[y],path.lon[y],(unsigned char)ifs);
				}

				else
				{
					field_strength=(139.4+(20.0*log10(LR.frq_mhz))-loss)+(10.0*log10(LR.erp/1000.0));

					ifs=100+(int)rint(field_strength);

					if (ifs<0)
						ifs=0;

					if (ifs>255)
						ifs=255;

					ofs=GetSignal(path.lat[y],path.lon[y]);

					if (ofs>ifs)
						ifs=ofs;

					PutSignal(path.lat[y],path.lon[y],(unsigned char)ifs);
	
					if (fd!=NULL)
						fprintf(fd,"%.3f",field_strength);
				}
			}

			else
			{
				if (loss>255)
					ifs=255;
				else
					ifs=(int)rint(loss);

				ofs=GetSignal(path.lat[y],path.lon[y]);

				if (ofs<ifs && ofs!=0)
					ifs=ofs;

				PutSignal(path.lat[y],path.lon[y],(unsigned char)ifs);
			}

			if (fd!=NULL)
			{
				if (block)
					fprintf(fd," *");

				fprintf(fd,"\n");
			}

			/* Mark this point as having been analyzed */

			PutMask(path.lat[y],path.lon[y],(GetMask(path.lat[y],path.lon[y])&7)+(mask_value<<3));
		}
	}
}

void PlotLOSMap(struct site source, double altitude)
{
	/* This function performs a 360 degree sweep around the
	   transmitter site (source location), and plots the
	   line-of-sight coverage of the transmitter on the SPLAT!
	   generated topographic map based on a receiver located
	   at the specified altitude (in feet AGL).  Results
	   are stored in memory, and written out in the form
	   of a topographic map when the WritePPM() function
	   is later invoked. */

	int y, z, count;
	struct site edge;
	unsigned char symbol[4], x;
	double lat, lon, minwest, maxnorth, th;
	static unsigned char mask_value=1;

	symbol[0]='.';
	symbol[1]='o';
	symbol[2]='O';
	symbol[3]='o';

	count=0;	

	fprintf(stdout,"\nComputing line-of-sight coverage of \"%s\" with an RX antenna\nat %.2f %s AGL",source.name,metric?altitude*METERS_PER_FOOT:altitude,metric?"meters":"feet");

	if (clutter>0.0)
		fprintf(stdout," and %.2f %s of ground clutter",metric?clutter*METERS_PER_FOOT:clutter,metric?"meters":"feet");

	fprintf(stdout,"...\n\n 0%c to  25%c ",37,37);
	fflush(stdout);

	/* th=pixels/degree divided by 64 loops per
	   progress indicator symbol (.oOo) printed. */
	
	th=ppd/64.0;

	z=(int)(th*ReduceAngle(max_west-min_west));

	minwest=dpp+(double)min_west;
	maxnorth=(double)max_north-dpp;

	for (lon=minwest, x=0, y=0; (LonDiff(lon,(double)max_west)<=0.0); y++, lon=minwest+(dpp*(double)y))
	{
		if (lon>=360.0)
			lon-=360.0;

		edge.lat=max_north;
		edge.lon=lon;
		edge.alt=altitude;

		PlotPath(source,edge,mask_value);
		count++;

		if (count==z) 
		{
			fprintf(stdout,"%c",symbol[x]);
			fflush(stdout);
			count=0;

			if (x==3)
				x=0;
			else
				x++;
		}
	}

	count=0;
	fprintf(stdout,"\n25%c to  50%c ",37,37);
	fflush(stdout);
	
	z=(int)(th*(double)(max_north-min_north));

	for (lat=maxnorth, x=0, y=0; lat>=(double)min_north; y++, lat=maxnorth-(dpp*(double)y))
	{
		edge.lat=lat;
		edge.lon=min_west;
		edge.alt=altitude;

		PlotPath(source,edge,mask_value);
		count++;

		if (count==z) 
		{
			fprintf(stdout,"%c",symbol[x]);
			fflush(stdout);
			count=0;

			if (x==3)
				x=0;
			else
				x++;
		}
	}

	count=0;
	fprintf(stdout,"\n50%c to  75%c ",37,37);
	fflush(stdout);

	z=(int)(th*ReduceAngle(max_west-min_west));

	for (lon=minwest, x=0, y=0; (LonDiff(lon,(double)max_west)<=0.0); y++, lon=minwest+(dpp*(double)y))
	{
		if (lon>=360.0)
			lon-=360.0;

		edge.lat=min_north;
		edge.lon=lon;
		edge.alt=altitude;

		PlotPath(source,edge,mask_value);
		count++;

		if (count==z)
		{
			fprintf(stdout,"%c",symbol[x]);
			fflush(stdout);
			count=0;

			if (x==3)
				x=0;
			else
				x++;
		}
	}

	count=0;
	fprintf(stdout,"\n75%c to 100%c ",37,37);
	fflush(stdout);
	
	z=(int)(th*(double)(max_north-min_north));

	for (lat=(double)min_north, x=0, y=0; lat<(double)max_north; y++, lat=(double)min_north+(dpp*(double)y))
	{
		edge.lat=lat;
		edge.lon=max_west;
		edge.alt=altitude;

		PlotPath(source,edge,mask_value);
		count++;

		if (count==z)
		{
			fprintf(stdout,"%c",symbol[x]);
			fflush(stdout);
			count=0;

			if (x==3)
				x=0;
			else
				x++;
		}
	}


	/* Assign next mask value */

	switch (mask_value)
	{
		case 1:
			mask_value=8;
			break;

		case 8:
			mask_value=16;
			break;

		case 16:
			mask_value=32;
	}
}

void PlotLRMap(struct site source, double altitude, char *plo_filename)
{
	/* This function performs a 360 degree sweep around the
	   transmitter site (source location), and plots the
	   Irregular Terrain Model attenuation on the SPLAT!
	   generated topographic map based on a receiver located
	   at the specified altitude (in feet AGL).  Results
	   are stored in memory, and written out in the form
	   of a topographic map when the WritePPMLR() or
	   WritePPMSS() functions are later invoked. */

	int y, z, count;
	struct site edge;
	double lat, lon, minwest, maxnorth, th;
	unsigned char x, symbol[4];
	static unsigned char mask_value=1;
	FILE *fd=NULL;

	minwest=dpp+(double)min_west;
	maxnorth=(double)max_north-dpp;

	symbol[0]='.';
	symbol[1]='o';
	symbol[2]='O';
	symbol[3]='o';

	count=0;

	if (olditm)
		fprintf(stdout,"\nComputing ITM ");
	else
		fprintf(stdout,"\nComputing ITWOM ");

	if (LR.erp==0.0)
		fprintf(stdout,"path loss");
	else
	{
		if (dbm)
			fprintf(stdout,"signal power level");
		else
			fprintf(stdout,"field strength");
	}
 
	fprintf(stdout," contours of \"%s\"\nout to a radius of %.2f %s with an RX antenna at %.2f %s AGL",source.name,metric?max_range*KM_PER_MILE:max_range,metric?"kilometers":"miles",metric?altitude*METERS_PER_FOOT:altitude,metric?"meters":"feet");

	if (clutter>0.0)
		fprintf(stdout,"\nand %.2f %s of ground clutter",metric?clutter*METERS_PER_FOOT:clutter,metric?"meters":"feet");

	fprintf(stdout,"...\n\n 0%c to  25%c ",37,37);
	fflush(stdout);

	if (plo_filename[0]!=0)
		fd=fopen(plo_filename,"wb");

	if (fd!=NULL)
	{
		/* Write header information to output file */

		fprintf(fd,"%d, %d\t; max_west, min_west\n%d, %d\t; max_north, min_north\n",max_west, min_west, max_north, min_north);
	}

	/* th=pixels/degree divided by 64 loops per
	   progress indicator symbol (.oOo) printed. */
	
	th=ppd/64.0;

	z=(int)(th*ReduceAngle(max_west-min_west));

	for (lon=minwest, x=0, y=0; (LonDiff(lon,(double)max_west)<=0.0); y++, lon=minwest+(dpp*(double)y))
	{
		if (lon>=360.0)
			lon-=360.0;

		edge.lat=max_north;
		edge.lon=lon;
		edge.alt=altitude;

		PlotLRPath(source,edge,mask_value,fd);
		count++;

		if (count==z) 
		{
			fprintf(stdout,"%c",symbol[x]);
			fflush(stdout);
			count=0;

			if (x==3)
				x=0;
			else
				x++;
		}
	}

	count=0;
	fprintf(stdout,"\n25%c to  50%c ",37,37);
	fflush(stdout);
	
	z=(int)(th*(double)(max_north-min_north));

	for (lat=maxnorth, x=0, y=0; lat>=(double)min_north; y++, lat=maxnorth-(dpp*(double)y))
	{
		edge.lat=lat;
		edge.lon=min_west;
		edge.alt=altitude;

		PlotLRPath(source,edge,mask_value,fd);
		count++;

		if (count==z) 
		{
			fprintf(stdout,"%c",symbol[x]);
			fflush(stdout);
			count=0;

			if (x==3)
				x=0;
			else
				x++;
		}
	}

	count=0;
	fprintf(stdout,"\n50%c to  75%c ",37,37);
	fflush(stdout);

	z=(int)(th*ReduceAngle(max_west-min_west));

	for (lon=minwest, x=0, y=0; (LonDiff(lon,(double)max_west)<=0.0); y++, lon=minwest+(dpp*(double)y))
	{
		if (lon>=360.0)
			lon-=360.0;

		edge.lat=min_north;
		edge.lon=lon;
		edge.alt=altitude;

		PlotLRPath(source,edge,mask_value,fd);
		count++;

		if (count==z)
		{
			fprintf(stdout,"%c",symbol[x]);
			fflush(stdout);
			count=0;

			if (x==3)
				x=0;
			else
				x++;
		}
	}

	count=0;
	fprintf(stdout,"\n75%c to 100%c ",37,37);
	fflush(stdout);
	
	z=(int)(th*(double)(max_north-min_north));

	for (lat=(double)min_north, x=0, y=0; lat<(double)max_north; y++, lat=(double)min_north+(dpp*(double)y))
	{
		edge.lat=lat;
		edge.lon=max_west;
		edge.alt=altitude;

		PlotLRPath(source,edge,mask_value,fd);
		count++;

		if (count==z)
		{
			fprintf(stdout,"%c",symbol[x]);
			fflush(stdout);
			count=0;

			if (x==3)
				x=0;
			else
				x++;
		}
	}

	if (fd!=NULL)
		fclose(fd);


	if (mask_value<30)
		mask_value++;
}

void LoadSignalColors(struct site xmtr)
{
	int x, y, ok, val[4];
	char filename[255], string[80], *pointer=NULL;
	FILE *fd=NULL;

	for (x=0; xmtr.filename[x]!='.' && xmtr.filename[x]!=0 && x<250; x++)
		filename[x]=xmtr.filename[x];

	filename[x]='.';
	filename[x+1]='s';
	filename[x+2]='c';
	filename[x+3]='f';
	filename[x+4]=0;

	/* Default values */

	region.level[0]=128;
	region.color[0][0]=255;
	region.color[0][1]=0;
	region.color[0][2]=0;

	region.level[1]=118;
	region.color[1][0]=255;
	region.color[1][1]=165;
	region.color[1][2]=0;

	region.level[2]=108;
	region.color[2][0]=255;
	region.color[2][1]=206;
	region.color[2][2]=0;

	region.level[3]=98;
	region.color[3][0]=255;
	region.color[3][1]=255;
	region.color[3][2]=0;

	region.level[4]=88;
	region.color[4][0]=184;
	region.color[4][1]=255;
	region.color[4][2]=0;

	region.level[5]=78;
	region.color[5][0]=0;
	region.color[5][1]=255;
	region.color[5][2]=0;

	region.level[6]=68;
	region.color[6][0]=0;
	region.color[6][1]=208;
	region.color[6][2]=0;

	region.level[7]=58;
	region.color[7][0]=0;
	region.color[7][1]=196;
	region.color[7][2]=196;

	region.level[8]=48;
	region.color[8][0]=0;
	region.color[8][1]=148;
	region.color[8][2]=255;

	region.level[9]=38;
	region.color[9][0]=80;
	region.color[9][1]=80;
	region.color[9][2]=255;

	region.level[10]=28;
	region.color[10][0]=0;
	region.color[10][1]=38;
	region.color[10][2]=255;

	region.level[11]=18;
	region.color[11][0]=142;
	region.color[11][1]=63;
	region.color[11][2]=255;

	region.level[12]=8;
	region.color[12][0]=140;
	region.color[12][1]=0;
	region.color[12][2]=128;

	region.levels=13;

	fd=fopen("splat.scf","r");

	if (fd==NULL)
		fd=fopen(filename,"r");

	if (fd==NULL)
	{
		fd=fopen(filename,"w");

		fprintf(fd,"; SPLAT! Auto-generated Signal Color Definition (\"%s\") File\n",filename);
		fprintf(fd,";\n; Format for the parameters held in this file is as follows:\n;\n");
		fprintf(fd,";    dBuV/m: red, green, blue\n;\n");
		fprintf(fd,"; ...where \"dBuV/m\" is the signal strength (in dBuV/m) and\n");
		fprintf(fd,"; \"red\", \"green\", and \"blue\" are the corresponding RGB color\n");
		fprintf(fd,"; definitions ranging from 0 to 255 for the region specified.\n");
		fprintf(fd,";\n; The following parameters may be edited and/or expanded\n");
		fprintf(fd,"; for future runs of SPLAT!  A total of 32 contour regions\n");
		fprintf(fd,"; may be defined in this file.\n;\n;\n");

		for (x=0; x<region.levels; x++)
			fprintf(fd,"%3d: %3d, %3d, %3d\n",region.level[x], region.color[x][0], region.color[x][1], region.color[x][2]);

		fclose(fd);
	}

	else
	{
		x=0;
		fgets(string,80,fd);

		while (x<32 && feof(fd)==0)
		{
			pointer=strchr(string,';');

			if (pointer!=NULL)
				*pointer=0;

			ok=sscanf(string,"%d: %d, %d, %d", &val[0], &val[1], &val[2], &val[3]);

			if (ok==4)
			{
				for (y=0; y<4; y++)
				{
					if (val[y]>255)
						val[y]=255;

					if (val[y]<0)
						val[y]=0;
				}
	
				region.level[x]=val[0];
				region.color[x][0]=val[1];
				region.color[x][1]=val[2];
				region.color[x][2]=val[3];
				x++;
			}

			fgets(string,80,fd);
		}

		fclose(fd);
		region.levels=x;
	}
}

void LoadLossColors(struct site xmtr)
{
	int x, y, ok, val[4];
	char filename[255], string[80], *pointer=NULL;
	FILE *fd=NULL;

	for (x=0; xmtr.filename[x]!='.' && xmtr.filename[x]!=0 && x<250; x++)
		filename[x]=xmtr.filename[x];

	filename[x]='.';
	filename[x+1]='l';
	filename[x+2]='c';
	filename[x+3]='f';
	filename[x+4]=0;

	/* Default values */

	region.level[0]=80;
	region.color[0][0]=255;
	region.color[0][1]=0;
	region.color[0][2]=0;

	region.level[1]=90;
	region.color[1][0]=255;
	region.color[1][1]=128;
	region.color[1][2]=0;

	region.level[2]=100;
	region.color[2][0]=255;
	region.color[2][1]=165;
	region.color[2][2]=0;

	region.level[3]=110;
	region.color[3][0]=255;
	region.color[3][1]=206;
	region.color[3][2]=0;

	region.level[4]=120;
	region.color[4][0]=255;
	region.color[4][1]=255;
	region.color[4][2]=0;

	region.level[5]=130;
	region.color[5][0]=184;
	region.color[5][1]=255;
	region.color[5][2]=0;

	region.level[6]=140;
	region.color[6][0]=0;
	region.color[6][1]=255;
	region.color[6][2]=0;

	region.level[7]=150;
	region.color[7][0]=0;
	region.color[7][1]=208;
	region.color[7][2]=0;

	region.level[8]=160;
	region.color[8][0]=0;
	region.color[8][1]=196;
	region.color[8][2]=196;

	region.level[9]=170;
	region.color[9][0]=0;
	region.color[9][1]=148;
	region.color[9][2]=255;

	region.level[10]=180;
	region.color[10][0]=80;
	region.color[10][1]=80;
	region.color[10][2]=255;

	region.level[11]=190;
	region.color[11][0]=0;
	region.color[11][1]=38;
	region.color[11][2]=255;

	region.level[12]=200;
	region.color[12][0]=142;
	region.color[12][1]=63;
	region.color[12][2]=255;

	region.level[13]=210;
	region.color[13][0]=196;
	region.color[13][1]=54;
	region.color[13][2]=255;

	region.level[14]=220;
	region.color[14][0]=255;
	region.color[14][1]=0;
	region.color[14][2]=255;

	region.level[15]=230;
	region.color[15][0]=255;
	region.color[15][1]=194;
	region.color[15][2]=204;

	region.levels=16;

	fd=fopen("splat.lcf","r");

	if (fd==NULL)
		fd=fopen(filename,"r");

	if (fd==NULL)
	{
		fd=fopen(filename,"w");

		fprintf(fd,"; SPLAT! Auto-generated Path-Loss Color Definition (\"%s\") File\n",filename);
		fprintf(fd,";\n; Format for the parameters held in this file is as follows:\n;\n");
		fprintf(fd,";    dB: red, green, blue\n;\n");
		fprintf(fd,"; ...where \"dB\" is the path loss (in dB) and\n");
		fprintf(fd,"; \"red\", \"green\", and \"blue\" are the corresponding RGB color\n");
		fprintf(fd,"; definitions ranging from 0 to 255 for the region specified.\n");
		fprintf(fd,";\n; The following parameters may be edited and/or expanded\n");
		fprintf(fd,"; for future runs of SPLAT!  A total of 32 contour regions\n");
		fprintf(fd,"; may be defined in this file.\n;\n;\n");

		for (x=0; x<region.levels; x++)
			fprintf(fd,"%3d: %3d, %3d, %3d\n",region.level[x], region.color[x][0], region.color[x][1], region.color[x][2]);

		fclose(fd);
	}

	else
	{
		x=0;
		fgets(string,80,fd);

		while (x<32 && feof(fd)==0)
		{
			pointer=strchr(string,';');

			if (pointer!=NULL)
				*pointer=0;

			ok=sscanf(string,"%d: %d, %d, %d", &val[0], &val[1], &val[2], &val[3]);

			if (ok==4)
			{
				for (y=0; y<4; y++)
				{
					if (val[y]>255)
						val[y]=255;

					if (val[y]<0)
						val[y]=0;
				}
	
				region.level[x]=val[0];
				region.color[x][0]=val[1];
				region.color[x][1]=val[2];
				region.color[x][2]=val[3];
				x++;
			}

			fgets(string,80,fd);
		}

		fclose(fd);
		region.levels=x;
	}
}

void LoadDBMColors(struct site xmtr)
{
	int x, y, ok, val[4];
	char filename[255], string[80], *pointer=NULL;
	FILE *fd=NULL;

	for (x=0; xmtr.filename[x]!='.' && xmtr.filename[x]!=0 && x<250; x++)
		filename[x]=xmtr.filename[x];

	filename[x]='.';
	filename[x+1]='d';
	filename[x+2]='c';
	filename[x+3]='f';
	filename[x+4]=0;

	/* Default values */

	region.level[0]=0;
	region.color[0][0]=255;
	region.color[0][1]=0;
	region.color[0][2]=0;

	region.level[1]=-10;
	region.color[1][0]=255;
	region.color[1][1]=128;
	region.color[1][2]=0;

	region.level[2]=-20;
	region.color[2][0]=255;
	region.color[2][1]=165;
	region.color[2][2]=0;

	region.level[3]=-30;
	region.color[3][0]=255;
	region.color[3][1]=206;
	region.color[3][2]=0;

	region.level[4]=-40;
	region.color[4][0]=255;
	region.color[4][1]=255;
	region.color[4][2]=0;

	region.level[5]=-50;
	region.color[5][0]=184;
	region.color[5][1]=255;
	region.color[5][2]=0;

	region.level[6]=-60;
	region.color[6][0]=0;
	region.color[6][1]=255;
	region.color[6][2]=0;

	region.level[7]=-70;
	region.color[7][0]=0;
	region.color[7][1]=208;
	region.color[7][2]=0;

	region.level[8]=-80;
	region.color[8][0]=0;
	region.color[8][1]=196;
	region.color[8][2]=196;

	region.level[9]=-90;
	region.color[9][0]=0;
	region.color[9][1]=148;
	region.color[9][2]=255;

	region.level[10]=-100;
	region.color[10][0]=80;
	region.color[10][1]=80;
	region.color[10][2]=255;

	region.level[11]=-110;
	region.color[11][0]=0;
	region.color[11][1]=38;
	region.color[11][2]=255;

	region.level[12]=-120;
	region.color[12][0]=142;
	region.color[12][1]=63;
	region.color[12][2]=255;

	region.level[13]=-130;
	region.color[13][0]=196;
	region.color[13][1]=54;
	region.color[13][2]=255;

	region.level[14]=-140;
	region.color[14][0]=255;
	region.color[14][1]=0;
	region.color[14][2]=255;

	region.level[15]=-150;
	region.color[15][0]=255;
	region.color[15][1]=194;
	region.color[15][2]=204;

	region.levels=16;

	fd=fopen("splat.dcf","r");

	if (fd==NULL)
		fd=fopen(filename,"r");

	if (fd==NULL)
	{
		fd=fopen(filename,"w");

		fprintf(fd,"; SPLAT! Auto-generated DBM Signal Level Color Definition (\"%s\") File\n",filename);
		fprintf(fd,";\n; Format for the parameters held in this file is as follows:\n;\n");
		fprintf(fd,";    dBm: red, green, blue\n;\n");
		fprintf(fd,"; ...where \"dBm\" is the received signal power level between +40 dBm\n");
		fprintf(fd,"; and -200 dBm, and \"red\", \"green\", and \"blue\" are the corresponding\n");
		fprintf(fd,"; RGB color definitions ranging from 0 to 255 for the region specified.\n");
		fprintf(fd,";\n; The following parameters may be edited and/or expanded\n");
		fprintf(fd,"; for future runs of SPLAT!  A total of 32 contour regions\n");
		fprintf(fd,"; may be defined in this file.\n;\n;\n");

		for (x=0; x<region.levels; x++)
			fprintf(fd,"%+4d: %3d, %3d, %3d\n",region.level[x], region.color[x][0], region.color[x][1], region.color[x][2]);

		fclose(fd);
	}

	else
	{
		x=0;
		fgets(string,80,fd);

		while (x<32 && feof(fd)==0)
		{
			pointer=strchr(string,';');

			if (pointer!=NULL)
				*pointer=0;

			ok=sscanf(string,"%d: %d, %d, %d", &val[0], &val[1], &val[2], &val[3]);

			if (ok==4)
			{
				if (val[0]<-200)
					val[0]=-200;

				if (val[0]>+40)
					val[0]=+40;

				region.level[x]=val[0];

				for (y=1; y<4; y++)
				{
					if (val[y]>255)
						val[y]=255;

					if (val[y]<0)
						val[y]=0;
				}
	
				region.color[x][0]=val[1];
				region.color[x][1]=val[2];
				region.color[x][2]=val[3];
				x++;
			}

			fgets(string,80,fd);
		}

		fclose(fd);
		region.levels=x;
	}
}



void GraphTerrain(struct site source, struct site destination, char *name)
{
	/* This function invokes gnuplot to generate an appropriate
	   output file indicating the terrain profile between the source
	   and destination locations when the -p command line option
	   is used.  "basename" is the name assigned to the output
	   file generated by gnuplot.  The filename extension is used
	   to set gnuplot's terminal setting and output file type.
	   If no extension is found, .png is assumed.  */

	int	x, y, z;
	char	basename[255], term[30], ext[15];
	double	minheight=100000.0, maxheight=-100000.0;
	FILE	*fd=NULL, *fd1=NULL;

	ReadPath(destination,source);

	fd=fopen("profile.gp","wb");

	if (clutter>0.0)
		fd1=fopen("clutter.gp","wb");

	for (x=0; x<path.length; x++)
	{
		if ((path.elevation[x]+clutter)>maxheight)
			maxheight=path.elevation[x]+clutter;

		if (path.elevation[x]<minheight)
			minheight=path.elevation[x];

		if (metric)
		{
			fprintf(fd,"%f\t%f\n",KM_PER_MILE*path.distance[x],METERS_PER_FOOT*path.elevation[x]);

			if (fd1!=NULL && x>0 && x<path.length-2)
				fprintf(fd1,"%f\t%f\n",KM_PER_MILE*path.distance[x],METERS_PER_FOOT*(path.elevation[x]==0.0?path.elevation[x]:(path.elevation[x]+clutter)));
		}

		else
		{
			fprintf(fd,"%f\t%f\n",path.distance[x],path.elevation[x]);

			if (fd1!=NULL && x>0 && x<path.length-2)
				fprintf(fd1,"%f\t%f\n",path.distance[x],(path.elevation[x]==0.0?path.elevation[x]:(path.elevation[x]+clutter)));
		}
	}

	fclose(fd);

	if (fd1!=NULL)
		fclose(fd1);

	if (name[0]=='.')
	{
		/* Default filename and output file type */

		strncpy(basename,"profile\0",8);
		strncpy(term,"png\0",4);
		strncpy(ext,"png\0",4);
	}

	else
	{
		/* Extract extension and terminal type from "name" */

		ext[0]=0;
		y=strlen(name);
		strncpy(basename,name,254);

		for (x=y-1; x>0 && name[x]!='.'; x--);

		if (x>0)  /* Extension found */
		{
			for (z=x+1; z<=y && (z-(x+1))<10; z++)
			{
				ext[z-(x+1)]=tolower(name[z]);
				term[z-(x+1)]=name[z];
			}

			ext[z-(x+1)]=0;  /* Ensure an ending 0 */
			term[z-(x+1)]=0;
			basename[x]=0;
		}

		if (ext[0]==0)	/* No extension -- Default is png */
		{
			strncpy(term,"png\0",4);
			strncpy(ext,"png\0",4);
		}
	}

	/* Either .ps or .postscript may be used
	   as an extension for postscript output. */

	if (strncmp(term,"postscript",10)==0)
		strncpy(ext,"ps\0",3);

	else if (strncmp(ext,"ps",2)==0)
			strncpy(term,"postscript enhanced color\0",26);

	if (maxheight<1.0)
	{
		maxheight=1.0;	/* Avoid a gnuplot y-range error */ 
		minheight=-1.0;	/* over a completely sea-level path */
	}

	else
		minheight-=(0.01*maxheight);

	fd=fopen("splat.gp","w");
	fprintf(fd,"set grid\n");
	fprintf(fd,"set yrange [%2.3f to %2.3f]\n", metric?minheight*METERS_PER_FOOT:minheight, metric?maxheight*METERS_PER_FOOT:maxheight);
	fprintf(fd,"set encoding iso_8859_1\n");
	fprintf(fd,"set term %s\n",term);
	fprintf(fd,"set title \"%s Terrain Profile Between %s and %s (%.2f%c Azimuth)\"\n",splat_name,destination.name, source.name, Azimuth(destination,source),176);

	if (metric)
	{
		fprintf(fd,"set xlabel \"Distance Between %s and %s (%.2f kilometers)\"\n",destination.name,source.name,KM_PER_MILE*Distance(source,destination));
		fprintf(fd,"set ylabel \"Ground Elevation Above Sea Level (meters)\"\n");
	}

	else
	{
		fprintf(fd,"set xlabel \"Distance Between %s and %s (%.2f miles)\"\n",destination.name,source.name,Distance(source,destination));
		fprintf(fd,"set ylabel \"Ground Elevation Above Sea Level (feet)\"\n");
	}

	fprintf(fd,"set output \"%s.%s\"\n",basename,ext);

	if (clutter>0.0)
	{
		if (metric)
			fprintf(fd,"plot \"profile.gp\" title \"Terrain Profile\" with lines, \"clutter.gp\" title \"Clutter Profile (%.2f meters)\" with lines\n",clutter*METERS_PER_FOOT);
		else
			fprintf(fd,"plot \"profile.gp\" title \"Terrain Profile\" with lines, \"clutter.gp\" title \"Clutter Profile (%.2f feet)\" with lines\n",clutter);
	}

	else
		fprintf(fd,"plot \"profile.gp\" title \"\" with lines\n");

	fclose(fd);
			
	x=system("gnuplot splat.gp");

	if (x!=-1)
	{
		if (gpsav==0)
		{	
			unlink("splat.gp");
			unlink("profile.gp");
		}

		fprintf(stdout,"Terrain plot written to: \"%s.%s\"\n",basename,ext);
		fflush(stdout);
	}

	else
		fprintf(stderr,"\n*** ERROR: Error occurred invoking gnuplot!\n");
}

void GraphElevation(struct site source, struct site destination, char *name)
{
	/* This function invokes gnuplot to generate an appropriate
	   output file indicating the terrain elevation profile between
	   the source and destination locations when the -e command line
	   option is used.  "basename" is the name assigned to the output
	   file generated by gnuplot.  The filename extension is used
	   to set gnuplot's terminal setting and output file type.
	   If no extension is found, .png is assumed.  */

	int	x, y, z;
	char	basename[255], term[30], ext[15];
	double	angle, clutter_angle=0.0, refangle, maxangle=-90.0,
	       	minangle=90.0, distance;
	struct	site remote, remote2;
	FILE	*fd=NULL, *fd1=NULL, *fd2=NULL;

	ReadPath(destination,source);  /* destination=RX, source=TX */
	refangle=ElevationAngle(destination,source);
	distance=Distance(source,destination);

	fd=fopen("profile.gp","wb");

	if (clutter>0.0)
		fd1=fopen("clutter.gp","wb");

	fd2=fopen("reference.gp","wb");

	for (x=1; x<path.length-1; x++)
	{
		remote.lat=path.lat[x];
		remote.lon=path.lon[x];
		remote.alt=0.0;
		angle=ElevationAngle(destination,remote);

		if (clutter>0.0)
		{
			remote2.lat=path.lat[x];
			remote2.lon=path.lon[x];

			if (path.elevation[x]!=0.0)
				remote2.alt=clutter;
			else
				remote2.alt=0.0;

			clutter_angle=ElevationAngle(destination,remote2);
		}

		if (metric)
		{
			fprintf(fd,"%f\t%f\n",KM_PER_MILE*path.distance[x],angle);

			if (fd1!=NULL)
				fprintf(fd1,"%f\t%f\n",KM_PER_MILE*path.distance[x],clutter_angle);

			fprintf(fd2,"%f\t%f\n",KM_PER_MILE*path.distance[x],refangle);
		}

		else
		{
			fprintf(fd,"%f\t%f\n",path.distance[x],angle);

			if (fd1!=NULL)
				fprintf(fd1,"%f\t%f\n",path.distance[x],clutter_angle);

			fprintf(fd2,"%f\t%f\n",path.distance[x],refangle);
		}

		if (angle>maxangle)
			maxangle=angle;

		if (clutter_angle>maxangle)
			maxangle=clutter_angle;

		if (angle<minangle)
			minangle=angle;
	}

	if (metric)
	{
		fprintf(fd,"%f\t%f\n",KM_PER_MILE*path.distance[path.length-1],refangle);
		fprintf(fd2,"%f\t%f\n",KM_PER_MILE*path.distance[path.length-1],refangle);
	}

	else
	{
		fprintf(fd,"%f\t%f\n",path.distance[path.length-1],refangle);
		fprintf(fd2,"%f\t%f\n",path.distance[path.length-1],refangle);
	}

	fclose(fd);

	if (fd1!=NULL)
		fclose(fd1);

	fclose(fd2);

	if (name[0]=='.')
	{
		/* Default filename and output file type */

		strncpy(basename,"profile\0",8);
		strncpy(term,"png\0",4);
		strncpy(ext,"png\0",4);
	}

	else
	{
		/* Extract extension and terminal type from "name" */

		ext[0]=0;
		y=strlen(name);
		strncpy(basename,name,254);

		for (x=y-1; x>0 && name[x]!='.'; x--);

		if (x>0)  /* Extension found */
		{
			for (z=x+1; z<=y && (z-(x+1))<10; z++)
			{
				ext[z-(x+1)]=tolower(name[z]);
				term[z-(x+1)]=name[z];
			}

			ext[z-(x+1)]=0;  /* Ensure an ending 0 */
			term[z-(x+1)]=0;
			basename[x]=0;
		}

		if (ext[0]==0)	/* No extension -- Default is png */
		{
			strncpy(term,"png\0",4);
			strncpy(ext,"png\0",4);
		}
	}

	/* Either .ps or .postscript may be used
	   as an extension for postscript output. */

	if (strncmp(term,"postscript",10)==0)
		strncpy(ext,"ps\0",3);

	else if (strncmp(ext,"ps",2)==0)
			strncpy(term,"postscript enhanced color\0",26);

	fd=fopen("splat.gp","w");

	fprintf(fd,"set grid\n");

	if (distance>2.0)
		fprintf(fd,"set yrange [%2.3f to %2.3f]\n", (-fabs(refangle)-0.25), maxangle+0.25);
	else
		fprintf(fd,"set yrange [%2.3f to %2.3f]\n", minangle, refangle+(-minangle/8.0));

	fprintf(fd,"set encoding iso_8859_1\n");
	fprintf(fd,"set term %s\n",term);
	fprintf(fd,"set title \"%s Elevation Profile Between %s and %s (%.2f%c azimuth)\"\n",splat_name,destination.name,source.name,Azimuth(destination,source),176);

	if (metric)
		fprintf(fd,"set xlabel \"Distance Between %s and %s (%.2f kilometers)\"\n",destination.name,source.name,KM_PER_MILE*distance);
	else
		fprintf(fd,"set xlabel \"Distance Between %s and %s (%.2f miles)\"\n",destination.name,source.name,distance);


	fprintf(fd,"set ylabel \"Elevation Angle Along LOS Path Between\\n%s and %s (degrees)\"\n",destination.name,source.name);
	fprintf(fd,"set output \"%s.%s\"\n",basename,ext);

	if (clutter>0.0)
	{
		if (metric)
			fprintf(fd,"plot \"profile.gp\" title \"Real Earth Profile\" with lines, \"clutter.gp\" title \"Clutter Profile (%.2f meters)\" with lines, \"reference.gp\" title \"Line of Sight Path (%.2f%c elevation)\" with lines\n",clutter*METERS_PER_FOOT,refangle,176);
		else
			fprintf(fd,"plot \"profile.gp\" title \"Real Earth Profile\" with lines, \"clutter.gp\" title \"Clutter Profile (%.2f feet)\" with lines, \"reference.gp\" title \"Line of Sight Path (%.2f%c elevation)\" with lines\n",clutter,refangle,176);
	}

	else
		fprintf(fd,"plot \"profile.gp\" title \"Real Earth Profile\" with lines, \"reference.gp\" title \"Line of Sight Path (%.2f%c elevation)\" with lines\n",refangle,176);

	fclose(fd);
			
	x=system("gnuplot splat.gp");

	if (x!=-1)
	{
		if (gpsav==0)
		{
			unlink("splat.gp");
			unlink("profile.gp");
			unlink("reference.gp");

			if (clutter>0.0)
				unlink("clutter.gp");
		}	

		fprintf(stdout,"Elevation plot written to: \"%s.%s\"\n",basename,ext);
		fflush(stdout);
	}

	else
		fprintf(stderr,"\n*** ERROR: Error occurred invoking gnuplot!\n");
}

void GraphHeight(struct site source, struct site destination, char *name, unsigned char fresnel_plot, unsigned char normalized)
{
	/* This function invokes gnuplot to generate an appropriate
	   output file indicating the terrain height profile between
	   the source and destination locations referenced to the
	   line-of-sight path between the receive and transmit sites
	   when the -h or -H command line option is used.  "basename"
	   is the name assigned to the output file generated by gnuplot.
	   The filename extension is used to set gnuplot's terminal
	   setting and output file type.  If no extension is found,
	   .png is assumed.  */

	int	x, y, z;
	char	basename[255], term[30], ext[15];
	double	a, b, c, height=0.0, refangle, cangle, maxheight=-100000.0,
		minheight=100000.0, lambda=0.0, f_zone=0.0, fpt6_zone=0.0,
		nm=0.0, nb=0.0, ed=0.0, es=0.0, r=0.0, d=0.0, d1=0.0,
		terrain, azimuth, distance, dheight=0.0, minterrain=100000.0,
		minearth=100000.0, miny, maxy, min2y, max2y;
	struct	site remote;
	FILE	*fd=NULL, *fd1=NULL, *fd2=NULL, *fd3=NULL, *fd4=NULL, *fd5=NULL;

	ReadPath(destination,source);  /* destination=RX, source=TX */
	azimuth=Azimuth(destination,source);
	distance=Distance(destination,source);
	refangle=ElevationAngle(destination,source);
	b=GetElevation(destination)+destination.alt+earthradius;

	/* Wavelength and path distance (great circle) in feet. */

	if (fresnel_plot)
	{
		lambda=9.8425e8/(LR.frq_mhz*1e6);
		d=5280.0*path.distance[path.length-1];
	}

	if (normalized)
	{
		ed=GetElevation(destination);
		es=GetElevation(source);
		nb=-destination.alt-ed;
		nm=(-source.alt-es-nb)/(path.distance[path.length-1]);
	}

	fd=fopen("profile.gp","wb");

	if (clutter>0.0)
		fd1=fopen("clutter.gp","wb");

	fd2=fopen("reference.gp","wb");
	fd5=fopen("curvature.gp", "wb");

	if ((LR.frq_mhz>=20.0) && (LR.frq_mhz<=20000.0) && fresnel_plot)
	{
		fd3=fopen("fresnel.gp", "wb");
		fd4=fopen("fresnel_pt_6.gp", "wb");
	}

	for (x=0; x<path.length-1; x++)
	{
		remote.lat=path.lat[x];
		remote.lon=path.lon[x];
		remote.alt=0.0;

		terrain=GetElevation(remote);

		if (x==0)
			terrain+=destination.alt;  /* RX antenna spike */

		a=terrain+earthradius;
 		cangle=5280.0*Distance(destination,remote)/earthradius;
		c=b*sin(refangle*DEG2RAD+HALFPI)/sin(HALFPI-refangle*DEG2RAD-cangle);

		height=a-c;

		/* Per Fink and Christiansen, Electronics
		 * Engineers' Handbook, 1989:
		 *
		 *   H = sqrt(lamba * d1 * (d - d1)/d)
		 *
		 * where H is the distance from the LOS
		 * path to the first Fresnel zone boundary.
		 */

		if ((LR.frq_mhz>=20.0) && (LR.frq_mhz<=20000.0) && fresnel_plot)
		{
			d1=5280.0*path.distance[x];
			f_zone=-1.0*sqrt(lambda*d1*(d-d1)/d);
			fpt6_zone=f_zone*fzone_clearance;
		}

		if (normalized)
		{
			r=-(nm*path.distance[x])-nb;
			height+=r;

			if ((LR.frq_mhz>=20.0) && (LR.frq_mhz<=20000.0) && fresnel_plot)
			{
				f_zone+=r;
				fpt6_zone+=r;
			}
		}

		else
			r=0.0;

		if (metric)
		{
			fprintf(fd,"%f\t%f\n",KM_PER_MILE*path.distance[x],METERS_PER_FOOT*height);

			if (fd1!=NULL && x>0 && x<path.length-2)
				fprintf(fd1,"%f\t%f\n",KM_PER_MILE*path.distance[x],METERS_PER_FOOT*(terrain==0.0?height:(height+clutter)));

			fprintf(fd2,"%f\t%f\n",KM_PER_MILE*path.distance[x],METERS_PER_FOOT*r);
			fprintf(fd5,"%f\t%f\n",KM_PER_MILE*path.distance[x],METERS_PER_FOOT*(height-terrain));
		}

		else
		{
			fprintf(fd,"%f\t%f\n",path.distance[x],height);

			if (fd1!=NULL && x>0 && x<path.length-2)
				fprintf(fd1,"%f\t%f\n",path.distance[x],(terrain==0.0?height:(height+clutter)));

			fprintf(fd2,"%f\t%f\n",path.distance[x],r);
			fprintf(fd5,"%f\t%f\n",path.distance[x],height-terrain);
		}

		if ((LR.frq_mhz>=20.0) && (LR.frq_mhz<=20000.0) && fresnel_plot)
		{
			if (metric)
			{
				fprintf(fd3,"%f\t%f\n",KM_PER_MILE*path.distance[x],METERS_PER_FOOT*f_zone);
				fprintf(fd4,"%f\t%f\n",KM_PER_MILE*path.distance[x],METERS_PER_FOOT*fpt6_zone);
			}

			else
			{
				fprintf(fd3,"%f\t%f\n",path.distance[x],f_zone);
				fprintf(fd4,"%f\t%f\n",path.distance[x],fpt6_zone);
			}

			if (f_zone<minheight)
				minheight=f_zone;
		}

		if ((height+clutter)>maxheight)
			maxheight=height+clutter;

		if (height<minheight)
			minheight=height;

		if (r>maxheight)
			maxheight=r;

		if (terrain<minterrain)
			minterrain=terrain;

		if ((height-terrain)<minearth)
			minearth=height-terrain;
	}

	if (normalized)
		r=-(nm*path.distance[path.length-1])-nb;
	else
		r=0.0;

	if (metric)
	{
		fprintf(fd,"%f\t%f\n",KM_PER_MILE*path.distance[path.length-1],METERS_PER_FOOT*r);
		fprintf(fd2,"%f\t%f\n",KM_PER_MILE*path.distance[path.length-1],METERS_PER_FOOT*r);
	}

	else
	{
		fprintf(fd,"%f\t%f\n",path.distance[path.length-1],r);
		fprintf(fd2,"%f\t%f\n",path.distance[path.length-1],r);
	}

	if ((LR.frq_mhz>=20.0) && (LR.frq_mhz<=20000.0) && fresnel_plot)
	{
		if (metric)
		{
			fprintf(fd3,"%f\t%f\n",KM_PER_MILE*path.distance[path.length-1],METERS_PER_FOOT*r);
			fprintf(fd4,"%f\t%f\n",KM_PER_MILE*path.distance[path.length-1],METERS_PER_FOOT*r);
		}

		else
		{
			fprintf(fd3,"%f\t%f\n",path.distance[path.length-1],r);
			fprintf(fd4,"%f\t%f\n",path.distance[path.length-1],r);
		}
	}
	
	if (r>maxheight)
		maxheight=r;

	if (r<minheight)
		minheight=r;

	fclose(fd);

	if (fd1!=NULL)
		fclose(fd1);

	fclose(fd2);
	fclose(fd5);

	if ((LR.frq_mhz>=20.0) && (LR.frq_mhz<=20000.0) && fresnel_plot)
	{
		fclose(fd3);
		fclose(fd4);
	}

	if (name[0]=='.')
	{
		/* Default filename and output file type */

		strncpy(basename,"profile\0",8);
		strncpy(term,"png\0",4);
		strncpy(ext,"png\0",4);
	}

	else
	{
		/* Extract extension and terminal type from "name" */

		ext[0]=0;
		y=strlen(name);
		strncpy(basename,name,254);

		for (x=y-1; x>0 && name[x]!='.'; x--);

		if (x>0)  /* Extension found */
		{
			for (z=x+1; z<=y && (z-(x+1))<10; z++)
			{
				ext[z-(x+1)]=tolower(name[z]);
				term[z-(x+1)]=name[z];
			}

			ext[z-(x+1)]=0;  /* Ensure an ending 0 */
			term[z-(x+1)]=0;
			basename[x]=0;
		}

		if (ext[0]==0)	/* No extension -- Default is png */
		{
			strncpy(term,"png\0",4);
			strncpy(ext,"png\0",4);
		}
	}

	/* Either .ps or .postscript may be used
	   as an extension for postscript output. */

	if (strncmp(term,"postscript",10)==0)
		strncpy(ext,"ps\0",3);

	else if (strncmp(ext,"ps",2)==0)
			strncpy(term,"postscript enhanced color\0",26);

	fd=fopen("splat.gp","w");

	dheight=maxheight-minheight;
	miny=minheight-0.15*dheight;
	maxy=maxheight+0.05*dheight;

	if (maxy<20.0)
		maxy=20.0;

	dheight=maxheight-minheight;
	min2y=miny-minterrain+0.05*dheight;

	if (minearth<min2y)
	{
		miny-=min2y-minearth+0.05*dheight;
		min2y=minearth-0.05*dheight;
	}

	max2y=min2y+maxy-miny;
 
	fprintf(fd,"set grid\n");
	fprintf(fd,"set yrange [%2.3f to %2.3f]\n", metric?miny*METERS_PER_FOOT:miny, metric?maxy*METERS_PER_FOOT:maxy);
	fprintf(fd,"set y2range [%2.3f to %2.3f]\n", metric?min2y*METERS_PER_FOOT:min2y, metric?max2y*METERS_PER_FOOT:max2y);
	fprintf(fd,"set xrange [-0.5 to %2.3f]\n",metric?KM_PER_MILE*rint(distance+0.5):rint(distance+0.5));
	fprintf(fd,"set encoding iso_8859_1\n");
	fprintf(fd,"set term %s\n",term);

	if ((LR.frq_mhz>=20.0) && (LR.frq_mhz<=20000.0) && fresnel_plot)
		fprintf(fd,"set title \"%s Path Profile Between %s and %s (%.2f%c azimuth)\\nWith First Fresnel Zone\"\n",splat_name, destination.name, source.name, azimuth,176);

	else
		fprintf(fd,"set title \"%s Height Profile Between %s and %s (%.2f%c azimuth)\"\n",splat_name, destination.name, source.name, azimuth,176);

	if (metric)
		fprintf(fd,"set xlabel \"Distance Between %s and %s (%.2f kilometers)\"\n",destination.name,source.name,KM_PER_MILE*Distance(source,destination));
	else
		fprintf(fd,"set xlabel \"Distance Between %s and %s (%.2f miles)\"\n",destination.name,source.name,Distance(source,destination));

	if (normalized)
	{
		if (metric)
			fprintf(fd,"set ylabel \"Normalized Height Referenced To LOS Path Between\\n%s and %s (meters)\"\n",destination.name,source.name);

		else
			fprintf(fd,"set ylabel \"Normalized Height Referenced To LOS Path Between\\n%s and %s (feet)\"\n",destination.name,source.name);

	}

	else
	{
		if (metric)
			fprintf(fd,"set ylabel \"Height Referenced To LOS Path Between\\n%s and %s (meters)\"\n",destination.name,source.name);

		else
			fprintf(fd,"set ylabel \"Height Referenced To LOS Path Between\\n%s and %s (feet)\"\n",destination.name,source.name);
	}

	fprintf(fd,"set output \"%s.%s\"\n",basename,ext);

	if ((LR.frq_mhz>=20.0) && (LR.frq_mhz<=20000.0) && fresnel_plot)
	{
		if (clutter>0.0)
		{
			if (metric)
				fprintf(fd,"plot \"profile.gp\" title \"Point-to-Point Profile\" with lines, \"clutter.gp\" title \"Ground Clutter (%.2f meters)\" with lines, \"reference.gp\" title \"Line of Sight Path\" with lines, \"curvature.gp\" axes x1y2 title \"Earth's Curvature Contour\" with lines, \"fresnel.gp\" axes x1y1 title \"First Fresnel Zone (%.3f MHz)\" with lines, \"fresnel_pt_6.gp\" title \"%.0f%% of First Fresnel Zone\" with lines\n",clutter*METERS_PER_FOOT,LR.frq_mhz,fzone_clearance*100.0);
			else
				fprintf(fd,"plot \"profile.gp\" title \"Point-to-Point Profile\" with lines, \"clutter.gp\" title \"Ground Clutter (%.2f feet)\" with lines, \"reference.gp\" title \"Line of Sight Path\" with lines, \"curvature.gp\" axes x1y2 title \"Earth's Curvature Contour\" with lines, \"fresnel.gp\" axes x1y1 title \"First Fresnel Zone (%.3f MHz)\" with lines, \"fresnel_pt_6.gp\" title \"%.0f%% of First Fresnel Zone\" with lines\n",clutter,LR.frq_mhz,fzone_clearance*100.0);
		}

		else
			fprintf(fd,"plot \"profile.gp\" title \"Point-to-Point Profile\" with lines, \"reference.gp\" title \"Line of Sight Path\" with lines, \"curvature.gp\" axes x1y2 title \"Earth's Curvature Contour\" with lines, \"fresnel.gp\" axes x1y1 title \"First Fresnel Zone (%.3f MHz)\" with lines, \"fresnel_pt_6.gp\" title \"%.0f%% of First Fresnel Zone\" with lines\n",LR.frq_mhz,fzone_clearance*100.0);
	}

	else
	{
		if (clutter>0.0)
		{
			if (metric)
				fprintf(fd,"plot \"profile.gp\" title \"Point-to-Point Profile\" with lines, \"clutter.gp\" title \"Ground Clutter (%.2f meters)\" with lines, \"reference.gp\" title \"Line Of Sight Path\" with lines, \"curvature.gp\" axes x1y2 title \"Earth's Curvature Contour\" with lines\n",clutter*METERS_PER_FOOT);
			else
				fprintf(fd,"plot \"profile.gp\" title \"Point-to-Point Profile\" with lines, \"clutter.gp\" title \"Ground Clutter (%.2f feet)\" with lines, \"reference.gp\" title \"Line Of Sight Path\" with lines, \"curvature.gp\" axes x1y2 title \"Earth's Curvature Contour\" with lines\n",clutter);
		}

		else
			fprintf(fd,"plot \"profile.gp\" title \"Point-to-Point Profile\" with lines, \"reference.gp\" title \"Line Of Sight Path\" with lines, \"curvature.gp\" axes x1y2 title \"Earth's Curvature Contour\" with lines\n");

	}

	fclose(fd);

	x=system("gnuplot splat.gp");

	if (x!=-1)
	{
		if (gpsav==0)
		{
			unlink("splat.gp");
			unlink("profile.gp");
			unlink("reference.gp");
			unlink("curvature.gp");

			if (fd1!=NULL)
				unlink("clutter.gp");

			if ((LR.frq_mhz>=20.0) && (LR.frq_mhz<=20000.0) && fresnel_plot)
			{
				unlink("fresnel.gp");
				unlink("fresnel_pt_6.gp");
			}
		}

		fprintf(stdout,"\nHeight plot written to: \"%s.%s\"",basename,ext);
		fflush(stdout);
	}

	else
		fprintf(stderr,"\n*** ERROR: Error occurred invoking gnuplot!\n");
}

void ObstructionAnalysis(struct site xmtr, struct site rcvr, double f, FILE *outfile)
{
	/* Perform an obstruction analysis along the
	   path between receiver and transmitter. */

	int	x;
	struct	site site_x;
	double	h_r, h_t, h_x, h_r_orig, cos_tx_angle, cos_test_angle,
		cos_tx_angle_f1, cos_tx_angle_fpt6, d_tx, d_x,
		h_r_f1, h_r_fpt6, h_f, h_los, lambda=0.0;
	char	string[255], string_fpt6[255], string_f1[255];

	ReadPath(xmtr,rcvr);
	h_r=GetElevation(rcvr)+rcvr.alt+earthradius;
	h_r_f1=h_r;
	h_r_fpt6=h_r;
	h_r_orig=h_r;
	h_t=GetElevation(xmtr)+xmtr.alt+earthradius;
	d_tx=5280.0*Distance(rcvr,xmtr);
	cos_tx_angle=((h_r*h_r)+(d_tx*d_tx)-(h_t*h_t))/(2.0*h_r*d_tx);
	cos_tx_angle_f1=cos_tx_angle;
	cos_tx_angle_fpt6=cos_tx_angle;

	if (f)
		lambda=9.8425e8/(f*1e6);

	if (clutter>0.0)
	{
		fprintf(outfile,"Terrain has been raised by");

		if (metric)
			fprintf(outfile," %.2f meters",METERS_PER_FOOT*clutter);
		else
			fprintf(outfile," %.2f feet",clutter);

		fprintf(outfile," to account for ground clutter.\n\n");
	}

	/* At each point along the path calculate the cosine
	   of a sort of "inverse elevation angle" at the receiver.
	   From the antenna, 0 deg. looks at the ground, and 90 deg.
	   is parallel to the ground.

	   Start at the receiver.  If this is the lowest antenna,
	   then terrain obstructions will be nearest to it.  (Plus,
	   that's the way SPLAT!'s original los() did it.)

	   Calculate cosines only.  That's sufficient to compare
	   angles and it saves the extra computational burden of
	   acos().  However, note the inverted comparison: if
	   acos(A) > acos(B), then B > A. */

	for (x=path.length-1; x>0; x--)
	{
		site_x.lat=path.lat[x];
		site_x.lon=path.lon[x];
		site_x.alt=0.0;

		h_x=GetElevation(site_x)+earthradius+clutter;
		d_x=5280.0*Distance(rcvr,site_x);

		/* Deal with the LOS path first. */

		cos_test_angle=((h_r*h_r)+(d_x*d_x)-(h_x*h_x))/(2.0*h_r*d_x);

		if (cos_tx_angle>cos_test_angle)
		{
			if (h_r==h_r_orig)
				fprintf(outfile,"Between %s and %s, %s detected obstructions at:\n\n",rcvr.name,xmtr.name,splat_name);

			if (site_x.lat>=0.0)
			{
				if (metric)
					fprintf(outfile,"   %8.4f N,%9.4f W, %5.2f kilometers, %6.2f meters AMSL\n",site_x.lat, site_x.lon, KM_PER_MILE*(d_x/5280.0), METERS_PER_FOOT*(h_x-earthradius));
				else
					fprintf(outfile,"   %8.4f N,%9.4f W, %5.2f miles, %6.2f feet AMSL\n",site_x.lat, site_x.lon, d_x/5280.0, h_x-earthradius);
			}

			else
			{
				if (metric)
					fprintf(outfile,"   %8.4f S,%9.4f W, %5.2f kilometers, %6.2f meters AMSL\n",-site_x.lat, site_x.lon, KM_PER_MILE*(d_x/5280.0), METERS_PER_FOOT*(h_x-earthradius));
				else

					fprintf(outfile,"   %8.4f S,%9.4f W, %5.2f miles, %6.2f feet AMSL\n",-site_x.lat, site_x.lon, d_x/5280.0, h_x-earthradius);
			}
		}

		while (cos_tx_angle>cos_test_angle)
		{
			h_r+=1;
			cos_test_angle=((h_r*h_r)+(d_x*d_x)-(h_x*h_x))/(2.0*h_r*d_x);
			cos_tx_angle=((h_r*h_r)+(d_tx*d_tx)-(h_t*h_t))/(2.0*h_r*d_tx);
		}

		if (f)
		{
			/* Now clear the first Fresnel zone... */

			cos_tx_angle_f1=((h_r_f1*h_r_f1)+(d_tx*d_tx)-(h_t*h_t))/(2.0*h_r_f1*d_tx);
			h_los=sqrt(h_r_f1*h_r_f1+d_x*d_x-2*h_r_f1*d_x*cos_tx_angle_f1);
			h_f=h_los-sqrt(lambda*d_x*(d_tx-d_x)/d_tx);

			while (h_f<h_x)
			{
				h_r_f1+=1;
				cos_tx_angle_f1=((h_r_f1*h_r_f1)+(d_tx*d_tx)-(h_t*h_t))/(2.0*h_r_f1*d_tx);
				h_los=sqrt(h_r_f1*h_r_f1+d_x*d_x-2*h_r_f1*d_x*cos_tx_angle_f1);
				h_f=h_los-sqrt(lambda*d_x*(d_tx-d_x)/d_tx);
			}

			/* and clear the 60% F1 zone. */

			cos_tx_angle_fpt6=((h_r_fpt6*h_r_fpt6)+(d_tx*d_tx)-(h_t*h_t))/(2.0*h_r_fpt6*d_tx);
			h_los=sqrt(h_r_fpt6*h_r_fpt6+d_x*d_x-2*h_r_fpt6*d_x*cos_tx_angle_fpt6);
			h_f=h_los-fzone_clearance*sqrt(lambda*d_x*(d_tx-d_x)/d_tx);

			while (h_f<h_x)
			{
				h_r_fpt6+=1;
				cos_tx_angle_fpt6=((h_r_fpt6*h_r_fpt6)+(d_tx*d_tx)-(h_t*h_t))/(2.0*h_r_fpt6*d_tx);
				h_los=sqrt(h_r_fpt6*h_r_fpt6+d_x*d_x-2*h_r_fpt6*d_x*cos_tx_angle_fpt6);
				h_f=h_los-fzone_clearance*sqrt(lambda*d_x*(d_tx-d_x)/d_tx);
			}
		}
	}
	fprintf(stdout,"ObstructionAnalysis h_r 0 %f, h_r_orig = %f \n", h_r, h_r_orig);
	if (h_r>h_r_orig)
	{
		if (metric)
			snprintf(string,150,"\nAntenna at %s must be raised to at least %.2f meters AGL\nto clear all obstructions detected by %s.\n",rcvr.name, METERS_PER_FOOT*(h_r-GetElevation(rcvr)-earthradius),splat_name);
		else
			snprintf(string,150,"\nAntenna at %s must be raised to at least %.2f feet AGL\nto clear all obstructions detected by %s.\n",rcvr.name, h_r-GetElevation(rcvr)-earthradius,splat_name);
	}

	else
		snprintf(string,150,"\nNo obstructions to LOS path due to terrain were detected by %s\n",splat_name);

	if (f)
	{
		if (h_r_fpt6>h_r_orig)
		{
			if (metric)
				snprintf(string_fpt6,150,"\nAntenna at %s must be raised to at least %.2f meters AGL\nto clear %.0f%c of the first Fresnel zone.\n",rcvr.name, METERS_PER_FOOT*(h_r_fpt6-GetElevation(rcvr)-earthradius),fzone_clearance*100.0,37);

			else
				snprintf(string_fpt6,150,"\nAntenna at %s must be raised to at least %.2f feet AGL\nto clear %.0f%c of the first Fresnel zone.\n",rcvr.name, h_r_fpt6-GetElevation(rcvr)-earthradius,fzone_clearance*100.0,37);
		}

		else
			snprintf(string_fpt6,150,"\n%.0f%c of the first Fresnel zone is clear.\n",fzone_clearance*100.0,37);
	
		if (h_r_f1>h_r_orig)
		{
			if (metric)
				snprintf(string_f1,150,"\nAntenna at %s must be raised to at least %.2f meters AGL\nto clear the first Fresnel zone.\n",rcvr.name, METERS_PER_FOOT*(h_r_f1-GetElevation(rcvr)-earthradius));

			else			
				snprintf(string_f1,150,"\nAntenna at %s must be raised to at least %.2f feet AGL\nto clear the first Fresnel zone.\n",rcvr.name, h_r_f1-GetElevation(rcvr)-earthradius);

		}

		else
    		    snprintf(string_f1,150,"\nThe first Fresnel zone is clear.\n");
	}

	fprintf(outfile,"%s",string);

	if (f)
	{
		fprintf(outfile,"%s",string_f1);
		fprintf(outfile,"%s",string_fpt6);
	}
}


const char* ObstructionAnalysisBurst(struct site xmtr, struct site rcvr, double f)
{

        FILE	*outfile=fopen("burst.txt","w");
	/* Perform an obstruction analysis along the
	   path between receiver and transmitter. */

	int	x;
	struct	site site_x;
	double	h_r, h_t, h_x, h_r_orig, cos_tx_angle, cos_test_angle,
		cos_tx_angle_f1, cos_tx_angle_fpt6, d_tx, d_x,
		h_r_f1, h_r_fpt6, h_f, h_los, lambda=0.0;
	char	string[255], string_fpt6[255], string_f1[255];

	ReadPath(xmtr,rcvr);
	h_r=GetElevation(rcvr)+rcvr.alt+earthradius;
	
	h_r_f1=h_r;
	h_r_fpt6=h_r;
	h_r_orig=h_r;
	h_t=GetElevation(xmtr)+xmtr.alt+earthradius;
	d_tx=5280.0*Distance(rcvr,xmtr);
	cos_tx_angle=((h_r*h_r)+(d_tx*d_tx)-(h_t*h_t))/(2.0*h_r*d_tx);
	cos_tx_angle_f1=cos_tx_angle;
	cos_tx_angle_fpt6=cos_tx_angle;

	if (f)
		lambda=9.8425e8/(f*1e6);

	if (clutter>0.0)
	{
		fprintf(outfile,"Terrain has been raised by");

		if (metric)
			fprintf(outfile," %.2f meters",METERS_PER_FOOT*clutter);
		else
			fprintf(outfile," %.2f feet",clutter);

		fprintf(outfile," to account for ground clutter.\n\n");
	}

	/* At each point along the path calculate the cosine
	   of a sort of "inverse elevation angle" at the receiver.
	   From the antenna, 0 deg. looks at the ground, and 90 deg.
	   is parallel to the ground.

	   Start at the receiver.  If this is the lowest antenna,
	   then terrain obstructions will be nearest to it.  (Plus,
	   that's the way SPLAT!'s original los() did it.)

	   Calculate cosines only.  That's sufficient to compare
	   angles and it saves the extra computational burden of
	   acos().  However, note the inverted comparison: if
	   acos(A) > acos(B), then B > A. */

	for (x=path.length-1; x>0; x--)
	{
		site_x.lat=path.lat[x];
		site_x.lon=path.lon[x];
		site_x.alt=0.0;

		h_x=GetElevation(site_x)+earthradius+clutter;
		d_x=5280.0*Distance(rcvr,site_x);

		/* Deal with the LOS path first. */

		cos_test_angle=((h_r*h_r)+(d_x*d_x)-(h_x*h_x))/(2.0*h_r*d_x);

		if (cos_tx_angle>cos_test_angle)
		{
			if (h_r==h_r_orig)
				fprintf(outfile,"Between %s and %s, %s detected obstructions at:\n\n",rcvr.name,xmtr.name,splat_name);

			if (site_x.lat>=0.0)
			{
				if (metric)
					fprintf(outfile,"   %8.4f N,%9.4f W, %5.2f kilometers, %6.2f meters AMSL\n",site_x.lat, site_x.lon, KM_PER_MILE*(d_x/5280.0), METERS_PER_FOOT*(h_x-earthradius));
				else
					fprintf(outfile,"   %8.4f N,%9.4f W, %5.2f miles, %6.2f feet AMSL\n",site_x.lat, site_x.lon, d_x/5280.0, h_x-earthradius);
			}

			else
			{
				if (metric)
					fprintf(outfile,"   %8.4f S,%9.4f W, %5.2f kilometers, %6.2f meters AMSL\n",-site_x.lat, site_x.lon, KM_PER_MILE*(d_x/5280.0), METERS_PER_FOOT*(h_x-earthradius));
				else

					fprintf(outfile,"   %8.4f S,%9.4f W, %5.2f miles, %6.2f feet AMSL\n",-site_x.lat, site_x.lon, d_x/5280.0, h_x-earthradius);
			}
		}

		while (cos_tx_angle>cos_test_angle)
		{
			h_r+=1;
			cos_test_angle=((h_r*h_r)+(d_x*d_x)-(h_x*h_x))/(2.0*h_r*d_x);
			cos_tx_angle=((h_r*h_r)+(d_tx*d_tx)-(h_t*h_t))/(2.0*h_r*d_tx);
		}

		if (f)
		{
			/* Now clear the first Fresnel zone... */

			cos_tx_angle_f1=((h_r_f1*h_r_f1)+(d_tx*d_tx)-(h_t*h_t))/(2.0*h_r_f1*d_tx);
			h_los=sqrt(h_r_f1*h_r_f1+d_x*d_x-2*h_r_f1*d_x*cos_tx_angle_f1);
			h_f=h_los-sqrt(lambda*d_x*(d_tx-d_x)/d_tx);

			while (h_f<h_x)
			{
				h_r_f1+=1;
				cos_tx_angle_f1=((h_r_f1*h_r_f1)+(d_tx*d_tx)-(h_t*h_t))/(2.0*h_r_f1*d_tx);
				h_los=sqrt(h_r_f1*h_r_f1+d_x*d_x-2*h_r_f1*d_x*cos_tx_angle_f1);
				h_f=h_los-sqrt(lambda*d_x*(d_tx-d_x)/d_tx);
			}

			/* and clear the 60% F1 zone. */

			cos_tx_angle_fpt6=((h_r_fpt6*h_r_fpt6)+(d_tx*d_tx)-(h_t*h_t))/(2.0*h_r_fpt6*d_tx);
			h_los=sqrt(h_r_fpt6*h_r_fpt6+d_x*d_x-2*h_r_fpt6*d_x*cos_tx_angle_fpt6);
			h_f=h_los-fzone_clearance*sqrt(lambda*d_x*(d_tx-d_x)/d_tx);

			while (h_f<h_x)
			{
				h_r_fpt6+=1;
				cos_tx_angle_fpt6=((h_r_fpt6*h_r_fpt6)+(d_tx*d_tx)-(h_t*h_t))/(2.0*h_r_fpt6*d_tx);
				h_los=sqrt(h_r_fpt6*h_r_fpt6+d_x*d_x-2*h_r_fpt6*d_x*cos_tx_angle_fpt6);
				h_f=h_los-fzone_clearance*sqrt(lambda*d_x*(d_tx-d_x)/d_tx);
			}
		}
	}
	fprintf(stdout,"ObstructionAnalysisBurst h_r 0 %f, h_r_orig = %f \n", h_r, h_r_orig);
	if (h_r>h_r_orig)
	{
		if (metric)
			snprintf(string,150,"\nAntenna at %s must be raised to at least %.2f meters AGL\nto clear all obstructions detected by %s.\n",rcvr.name, METERS_PER_FOOT*(h_r-GetElevation(rcvr)-earthradius),splat_name);
		else
			snprintf(string,150,"\nAntenna at %s must be raised to at least %.2f feet AGL\nto clear all obstructions detected by %s.\n",rcvr.name, h_r-GetElevation(rcvr)-earthradius,splat_name);
	}

	else
		snprintf(string,150,"\nNo obstructions to LOS path due to terrain were detected by %s\n",splat_name);

	if (f)
	{
		if (h_r_fpt6>h_r_orig)
		{
			if (metric)
				snprintf(string_fpt6,150,"\nAntenna at %s must be raised to at least %.2f meters AGL\nto clear %.0f%c of the first Fresnel zone.\n",rcvr.name, METERS_PER_FOOT*(h_r_fpt6-GetElevation(rcvr)-earthradius),fzone_clearance*100.0,37);

			else
				snprintf(string_fpt6,150,"\nAntenna at %s must be raised to at least %.2f feet AGL\nto clear %.0f%c of the first Fresnel zone.\n",rcvr.name, h_r_fpt6-GetElevation(rcvr)-earthradius,fzone_clearance*100.0,37);
		}

		else
			snprintf(string_fpt6,150,"\n%.0f%c of the first Fresnel zone is clear.\n",fzone_clearance*100.0,37);
	
		if (h_r_f1>h_r_orig)
		{
			if (metric)
				snprintf(string_f1,150,"\nAntenna at %s must be raised to at least %.2f meters AGL\nto clear the first Fresnel zone.\n",rcvr.name, METERS_PER_FOOT*(h_r_f1-GetElevation(rcvr)-earthradius));

			else			
				snprintf(string_f1,150,"\nAntenna at %s must be raised to at least %.2f feet AGL\nto clear the first Fresnel zone.\n",rcvr.name, h_r_f1-GetElevation(rcvr)-earthradius);

		}

		else
    		    snprintf(string_f1,150,"\nThe first Fresnel zone is clear.\n");
	}

	fprintf(outfile,"%s",string);

	if (f)
	{
		fprintf(outfile,"%s",string_f1);
		fprintf(outfile,"%s",string_fpt6);
	}


  
  
  return "done";
}

void PathReport(struct site source, struct site destination, char *name, char graph_it)
{
	/* This function writes a SPLAT! Path Report (name.txt) to
	   the filesystem.  If (graph_it == 1), then gnuplot is invoked
	   to generate an appropriate output file indicating the ITM
	   model loss between the source and destination locations.
    	   "filename" is the name assigned to the output file generated
	   by gnuplot.  The filename extension is used to set gnuplot's
	   terminal setting and output file type.  If no extension is
	   found, .png is assumed. */

	int	x, y, z, errnum;
	char	basename[255], term[30], ext[15], strmode[100],
		report_name[80], block=0, propstring[20];
	double	maxloss=-100000.0, minloss=100000.0, loss, haavt,
		angle1, angle2, azimuth, pattern=1.0, patterndB=0.0,
		total_loss=0.0, cos_xmtr_angle, cos_test_angle=0.0,
		source_alt, test_alt, dest_alt, source_alt2, dest_alt2,
		distance, elevation, four_thirds_earth, field_strength,
		free_space_loss=0.0, eirp=0.0, voltage, rxp, dBm,
		power_density;
	FILE	*fd=NULL, *fd2=NULL;

	sprintf(report_name,"%s-to-%s.txt",source.name,destination.name);

	four_thirds_earth=FOUR_THIRDS*EARTHRADIUS;

	for (x=0; report_name[x]!=0; x++)
		if (report_name[x]==32 || report_name[x]==17 || report_name[x]==92 || report_name[x]==42 || report_name[x]==47)
			report_name[x]='_';	

	fd2=fopen(report_name,"w");

	fprintf(fd2,"\n\t\t--==[ %s v%s Path Analysis ]==--\n\n",splat_name,splat_version);
	fprintf(fd2,"%s\n\n",dashes);
	fprintf(fd2,"Transmitter site: %s\n",source.name);

	if (source.lat>=0.0)
	{
		fprintf(fd2,"Site location: %.4f North / %.4f West",source.lat, source.lon);
		fprintf(fd2, " (%s N / ", dec2dms(source.lat));
	}

	else
	{

		fprintf(fd2,"Site location: %.4f South / %.4f West",-source.lat, source.lon);
		fprintf(fd2, " (%s S / ", dec2dms(source.lat));
	}
	
	fprintf(fd2, "%s W)\n", dec2dms(source.lon));

	if (metric)
	{
		fprintf(fd2,"Ground elevation: %.2f meters AMSL\n",METERS_PER_FOOT*GetElevation(source));
		fprintf(fd2,"Antenna height: %.2f meters AGL / %.2f meters AMSL\n",METERS_PER_FOOT*source.alt,METERS_PER_FOOT*(source.alt+GetElevation(source)));
	}

	else
	{
		fprintf(fd2,"Ground elevation: %.2f feet AMSL\n",GetElevation(source));
		fprintf(fd2,"Antenna height: %.2f feet AGL / %.2f feet AMSL\n",source.alt, source.alt+GetElevation(source));
	}

	haavt=haat(source);

	if (haavt>-4999.0)
	{
		if (metric)
			fprintf(fd2,"Antenna height above average terrain: %.2f meters\n",METERS_PER_FOOT*haavt);
		else
			fprintf(fd2,"Antenna height above average terrain: %.2f feet\n",haavt);
	}

	azimuth=Azimuth(source,destination);
	angle1=ElevationAngle(source,destination);
	angle2=ElevationAngleTwo(source,destination,earthradius);

	if (got_azimuth_pattern || got_elevation_pattern)
	{
		x=(int)rint(10.0*(10.0-angle2));

		if (x>=0 && x<=1000)
			pattern=(double)LR.antenna_pattern[(int)rint(azimuth)][x];

		patterndB=20.0*log10(pattern);
	}

	if (metric)
		fprintf(fd2,"Distance to %s: %.2f kilometers\n",destination.name,KM_PER_MILE*Distance(source,destination));

	else
		fprintf(fd2,"Distance to %s: %.2f miles\n",destination.name,Distance(source,destination));

	fprintf(fd2,"Azimuth to %s: %.2f degrees\n",destination.name,azimuth);

	if (angle1>=0.0)
		fprintf(fd2,"Elevation angle to %s: %+.4f degrees\n",destination.name,angle1);

	else
		fprintf(fd2,"Depression angle to %s: %+.4f degrees\n",destination.name,angle1);

	if ((angle2-angle1)>0.0001)
	{
		if (angle2<0.0)
			fprintf(fd2,"Depression");
		else
			fprintf(fd2,"Elevation");

		fprintf(fd2," angle to the first obstruction: %+.4f degrees\n",angle2);
	}

	fprintf(fd2,"\n%s\n\n",dashes);

	/* Receiver */

	fprintf(fd2,"Receiver site: %s\n",destination.name);

	if (destination.lat>=0.0)
	{
		fprintf(fd2,"Site location: %.4f North / %.4f West",destination.lat, destination.lon);
		fprintf(fd2, " (%s N / ", dec2dms(destination.lat));
	}

	else
	{
		fprintf(fd2,"Site location: %.4f South / %.4f West",-destination.lat, destination.lon);
		fprintf(fd2, " (%s S / ", dec2dms(destination.lat));
	}

	fprintf(fd2, "%s W)\n", dec2dms(destination.lon));

	if (metric)
	{
		fprintf(fd2,"Ground elevation: %.2f meters AMSL\n",METERS_PER_FOOT*GetElevation(destination));
		fprintf(fd2,"Antenna height: %.2f meters AGL / %.2f meters AMSL\n",METERS_PER_FOOT*destination.alt, METERS_PER_FOOT*(destination.alt+GetElevation(destination)));
	}

	else
	{
		fprintf(fd2,"Ground elevation: %.2f feet AMSL\n",GetElevation(destination));
		fprintf(fd2,"Antenna height: %.2f feet AGL / %.2f feet AMSL\n",destination.alt, destination.alt+GetElevation(destination));
	}

	haavt=haat(destination);

	if (haavt>-4999.0)
	{
		if (metric)
			fprintf(fd2,"Antenna height above average terrain: %.2f meters\n",METERS_PER_FOOT*haavt);
		else
			fprintf(fd2,"Antenna height above average terrain: %.2f feet\n",haavt);
	}

	if (metric)
		fprintf(fd2,"Distance to %s: %.2f kilometers\n",source.name,KM_PER_MILE*Distance(source,destination));

	else
		fprintf(fd2,"Distance to %s: %.2f miles\n",source.name,Distance(source,destination));

	azimuth=Azimuth(destination,source);

	angle1=ElevationAngle(destination,source);
	angle2=ElevationAngleTwo(destination,source,earthradius);

	fprintf(fd2,"Azimuth to %s: %.2f degrees\n",source.name,azimuth);

	if (angle1>=0.0)
		fprintf(fd2,"Elevation angle to %s: %+.4f degrees\n",source.name,angle1);

	else
		fprintf(fd2,"Depression angle to %s: %+.4f degrees\n",source.name,angle1);

	if ((angle2-angle1)>0.0001)
	{
		if (angle2<0.0)
			fprintf(fd2,"Depression");
		else
			fprintf(fd2,"Elevation");

		fprintf(fd2," angle to the first obstruction: %+.4f degrees\n",angle2);
	}

	fprintf(fd2,"\n%s\n\n",dashes);

	if (LR.frq_mhz>0.0)
	{
		if (olditm)
			fprintf(fd2,"Longley-Rice Parameters Used In This Analysis:\n\n");
		else
			fprintf(fd2,"ITWOM Version %.1f Parameters Used In This Analysis:\n\n",ITWOMVersion());

		fprintf(fd2,"Earth's Dielectric Constant: %.3lf\n",LR.eps_dielect);
		fprintf(fd2,"Earth's Conductivity: %.3lf Siemens/meter\n",LR.sgm_conductivity);
		fprintf(fd2,"Atmospheric Bending Constant (N-units): %.3lf ppm\n",LR.eno_ns_surfref);
		fprintf(fd2,"Frequency: %.3lf MHz\n",LR.frq_mhz);
		fprintf(fd2,"Radio Climate: %d (",LR.radio_climate);

		switch (LR.radio_climate)
		{
			case 1:
			fprintf(fd2,"Equatorial");
			break;

			case 2:
			fprintf(fd2,"Continental Subtropical");
			break;

			case 3:
			fprintf(fd2,"Maritime Subtropical");
			break;

			case 4:
			fprintf(fd2,"Desert");
			break;

			case 5:
			fprintf(fd2,"Continental Temperate");
			break;

			case 6:
			fprintf(fd2,"Martitime Temperate, Over Land");
			break;

			case 7:
			fprintf(fd2,"Maritime Temperate, Over Sea");
			break;

			default:
			fprintf(fd2,"Unknown");
		}

		fprintf(fd2,")\nPolarization: %d (",LR.pol);

		if (LR.pol==0)
			fprintf(fd2,"Horizontal");

		if (LR.pol==1)
			fprintf(fd2,"Vertical");

		fprintf(fd2,")\nFraction of Situations: %.1lf%c\n",LR.conf*100.0,37);
		fprintf(fd2,"Fraction of Time: %.1lf%c\n",LR.rel*100.0,37);

		if (LR.erp!=0.0)
		{
			fprintf(fd2,"Transmitter ERP: ");

			if (LR.erp<1.0)
				fprintf(fd2,"%.1lf milliwatts",1000.0*LR.erp);

			if (LR.erp>=1.0 && LR.erp<10.0)
				fprintf(fd2,"%.1lf Watts",LR.erp);

			if (LR.erp>=10.0 && LR.erp<10.0e3)
				fprintf(fd2,"%.0lf Watts",LR.erp);

			if (LR.erp>=10.0e3)
				fprintf(fd2,"%.3lf kilowatts",LR.erp/1.0e3);

			dBm=10.0*(log10(LR.erp*1000.0));
			fprintf(fd2," (%+.2f dBm)\n",dBm);

			/* EIRP = ERP + 2.14 dB */

			fprintf(fd2,"Transmitter EIRP: ");

			eirp=LR.erp*1.636816521;

			if (eirp<1.0)
				fprintf(fd2,"%.1lf milliwatts",1000.0*eirp);

			if (eirp>=1.0 && eirp<10.0)
				fprintf(fd2,"%.1lf Watts",eirp);

			if (eirp>=10.0 && eirp<10.0e3)
				fprintf(fd2,"%.0lf Watts",eirp);

			if (eirp>=10.0e3)
				fprintf(fd2,"%.3lf kilowatts",eirp/1.0e3);

			dBm=10.0*(log10(eirp*1000.0));
			fprintf(fd2," (%+.2f dBm)\n",dBm);
		}

		fprintf(fd2,"\n%s\n\n",dashes);

		fprintf(fd2,"Summary For The Link Between %s and %s:\n\n",source.name, destination.name);

		if (patterndB!=0.0)
			fprintf(fd2,"%s antenna pattern towards %s: %.3f (%.2f dB)\n", source.name, destination.name, pattern, patterndB);

		ReadPath(source, destination);  /* source=TX, destination=RX */

		/* Copy elevations plus clutter along
		   path into the elev[] array. */

		for (x=1; x<path.length-1; x++)
			elev[x+2]=METERS_PER_FOOT*(path.elevation[x]==0.0?path.elevation[x]:(clutter+path.elevation[x]));

		/* Copy ending points without clutter */

		elev[2]=path.elevation[0]*METERS_PER_FOOT;
		elev[path.length+1]=path.elevation[path.length-1]*METERS_PER_FOOT;

		fd=fopen("profile.gp","w");

		azimuth=rint(Azimuth(source,destination));

		for (y=2; y<(path.length-1); y++)  /* path.length-1 avoids LR error */
		{
			distance=5280.0*path.distance[y];
			source_alt=four_thirds_earth+source.alt+path.elevation[0];
			dest_alt=four_thirds_earth+destination.alt+path.elevation[y];
			dest_alt2=dest_alt*dest_alt;
			source_alt2=source_alt*source_alt;

			/* Calculate the cosine of the elevation of
			   the receiver as seen by the transmitter. */

			cos_xmtr_angle=((source_alt2)+(distance*distance)-(dest_alt2))/(2.0*source_alt*distance);

			if (got_elevation_pattern)
			{
				/* If an antenna elevation pattern is available, the
				   following code determines the elevation angle to
			   	   the first obstruction along the path. */

				for (x=2, block=0; x<y && block==0; x++)
				{
					distance=5280.0*(path.distance[y]-path.distance[x]);
					test_alt=four_thirds_earth+path.elevation[x];

					/* Calculate the cosine of the elevation
					   angle of the terrain (test point)
					   as seen by the transmitter. */

					cos_test_angle=((source_alt2)+(distance*distance)-(test_alt*test_alt))/(2.0*source_alt*distance);

					/* Compare these two angles to determine if
					   an obstruction exists.  Since we're comparing
					   the cosines of these angles rather than
					   the angles themselves, the sense of the
					   following "if" statement is reversed from
				   	   what it would be if the angles themselves
				   	   were compared. */

					if (cos_xmtr_angle>=cos_test_angle)
						block=1;
				}

				/* At this point, we have the elevation angle
				   to the first obstruction (if it exists). */
			}

			/* Determine path loss for each point along
			   the path using ITWOM's point_to_point mode
		  	   starting at x=2 (number_of_points = 1), the
		  	   shortest distance terrain can play a role in
		  	   path loss. */

			elev[0]=y-1;	/* (number of points - 1) */

			/* Distance between elevation samples */

			elev[1]=METERS_PER_MILE*(path.distance[y]-path.distance[y-1]);

			if (olditm)
				point_to_point_ITM(elev,source.alt*METERS_PER_FOOT, 
  		 		destination.alt*METERS_PER_FOOT, LR.eps_dielect,
				LR.sgm_conductivity, LR.eno_ns_surfref, LR.frq_mhz,
				LR.radio_climate, LR.pol, LR.conf, LR.rel, loss,
				strmode, errnum);
			else
				point_to_point(elev,source.alt*METERS_PER_FOOT, 
  		 		destination.alt*METERS_PER_FOOT, LR.eps_dielect,
				LR.sgm_conductivity, LR.eno_ns_surfref, LR.frq_mhz,
				LR.radio_climate, LR.pol, LR.conf, LR.rel, loss,
				strmode, errnum);

			if (block)
				elevation=((acos(cos_test_angle))/DEG2RAD)-90.0;
			else
				elevation=((acos(cos_xmtr_angle))/DEG2RAD)-90.0;

			/* Integrate the antenna's radiation
			   pattern into the overall path loss. */

			x=(int)rint(10.0*(10.0-elevation));

			if (x>=0 && x<=1000)
			{
				pattern=(double)LR.antenna_pattern[(int)azimuth][x];

				if (pattern!=0.0)
					patterndB=20.0*log10(pattern);
			}

			else
				patterndB=0.0;

			total_loss=loss-patterndB;

			if (metric)
				fprintf(fd,"%f\t%f\n",KM_PER_MILE*path.distance[y],total_loss);

			else
				fprintf(fd,"%f\t%f\n",path.distance[y],total_loss);

			if (total_loss>maxloss)
				maxloss=total_loss;

			if (total_loss<minloss)
				minloss=total_loss;
		}

		fclose(fd);

		distance=Distance(source,destination);


		if (distance!=0.0)
		{
			free_space_loss=36.6+(20.0*log10(LR.frq_mhz))+(20.0*log10(distance));

			fprintf(fd2,"Free space path loss: %.2f dB\n",free_space_loss);
		}

		if (olditm)
			fprintf(fd2,"Longley-Rice path loss: %.2f dB\n",loss);
		else
			fprintf(fd2,"ITWOM Version %.1f path loss: %.2f dB\n",ITWOMVersion(),loss);

		if (free_space_loss!=0.0)
			fprintf(fd2,"Attenuation due to terrain shielding: %.2f dB\n",loss-free_space_loss);

		if (patterndB!=0.0)
			fprintf(fd2,"Total path loss including %s antenna pattern: %.2f dB\n",source.name,total_loss);

		if (LR.erp!=0.0)
		{
			field_strength=(139.4+(20.0*log10(LR.frq_mhz))-total_loss)+(10.0*log10(LR.erp/1000.0));

			/* dBm is referenced to EIRP */

			rxp=eirp/(pow(10.0,(total_loss/10.0)));
			dBm=10.0*(log10(rxp*1000.0));
			power_density=(eirp/(pow(10.0,(total_loss-free_space_loss)/10.0)));
			/* divide by 4*PI*distance_in_meters squared */
			power_density/=(4.0*PI*distance*distance*2589988.11);

			fprintf(fd2,"Field strength at %s: %.2f dBuV/meter\n", destination.name,field_strength);
			fprintf(fd2,"Signal power level at %s: %+.2f dBm\n",destination.name,dBm);
			fprintf(fd2,"Signal power density at %s: %+.2f dBW per square meter\n",destination.name,10.0*log10(power_density));
			voltage=1.0e6*sqrt(50.0*(eirp/(pow(10.0,(total_loss-2.14)/10.0))));
			fprintf(fd2,"Voltage across a 50 ohm dipole at %s: %.2f uV (%.2f dBuV)\n",destination.name,voltage,20.0*log10(voltage));

			voltage=1.0e6*sqrt(75.0*(eirp/(pow(10.0,(total_loss-2.14)/10.0))));
			fprintf(fd2,"Voltage across a 75 ohm dipole at %s: %.2f uV (%.2f dBuV)\n",destination.name,voltage,20.0*log10(voltage));
		}

		fprintf(fd2,"Mode of propagation: ");
		
		if (olditm)
		{
			fprintf(fd2,"%s\n",strmode);
			fprintf(fd2,"Longley-Rice model error number: %d",errnum);
		}

		else
		{
			if (strcmp(strmode,"L-o-S")==0)
				fprintf(fd2,"Line of Sight\n");

			if (strncmp(strmode,"1_Hrzn",6)==0)
				fprintf(fd2,"Single Horizon ");

			if (strncmp(strmode,"2_Hrzn",6)==0)
				fprintf(fd2,"Double Horizon ");

			y=strlen(strmode);

			if (y>19)
				y=19;

			for (x=6; x<y; x++)
				propstring[x-6]=strmode[x];

			propstring[x]=0;

			if (strncmp(propstring,"_Diff",5)==0)
				fprintf(fd2,"Diffraction Dominant\n");

			if (strncmp(propstring,"_Tropo",6)==0)
				fprintf(fd2,"Troposcatter Dominant\n");

			if (strncmp(propstring,"_Peak",5)==0)
				fprintf(fd2,"RX at Peak Terrain Along Path\n");

			fprintf(fd2,"ITWOM error number: %d",errnum);
		}

		switch (errnum)
		{
			case 0:
				fprintf(fd2," (No error)\n");
				break;

			case 1:
				fprintf(fd2,"\n  Warning: Some parameters are nearly out of range.\n");
				fprintf(fd2,"  Results should be used with caution.\n");
				break;

			case 2:
				fprintf(fd2,"\n  Note: Default parameters have been substituted for impossible ones.\n");
				break;

			case 3:
				fprintf(fd2,"\n  Warning: A combination of parameters is out of range.\n");
				fprintf(fd2,"  Results are probably invalid.\n");
				break;

			default:
				fprintf(fd2,"\n  Warning: Some parameters are out of range.\n");
				fprintf(fd2,"  Results are probably invalid.\n");
		}

		fprintf(fd2,"\n%s\n\n",dashes);
	}

	fprintf(stdout,"\nPath Loss Report written to: \"%s\"\n",report_name);
	fflush(stdout);

	ObstructionAnalysis(source, destination, LR.frq_mhz, fd2);
	fclose(fd2);

	/* Skip plotting the graph if ONLY a path-loss report is needed. */

	if (graph_it)
	{
		if (name[0]=='.')
		{
			/* Default filename and output file type */
			strncpy(basename,"profile\0",8);
			strncpy(term,"png\0",4);
			strncpy(ext,"png\0",4);
		}
		else
		{
			/* Extract extension and terminal type from "name" */
			ext[0]=0;
			y=strlen(name);
			strncpy(basename,name,254);

			for (x=y-1; x>0 && name[x]!='.'; x--);

			if (x>0)  /* Extension found */
			{
				for (z=x+1; z<=y && (z-(x+1))<10; z++)
				{
					ext[z-(x+1)]=tolower(name[z]);
					term[z-(x+1)]=name[z];
				}

				ext[z-(x+1)]=0;  /* Ensure an ending 0 */
				term[z-(x+1)]=0;
				basename[x]=0;
			}
		}

		if (ext[0]==0)	/* No extension -- Default is png */
		{
			strncpy(term,"png\0",4);
			strncpy(ext,"png\0",4);
		}

		/* Either .ps or .postscript may be used
		   as an extension for postscript output. */

		if (strncmp(term,"postscript",10)==0)
			strncpy(ext,"ps\0",3);

		else if (strncmp(ext,"ps",2)==0)
				strncpy(term,"postscript enhanced color\0",26);

		fd=fopen("splat.gp","w");

		fprintf(fd,"set grid\n");
		fprintf(fd,"set yrange [%2.3f to %2.3f]\n", minloss, maxloss);
		fprintf(fd,"set encoding iso_8859_1\n");
		fprintf(fd,"set term %s\n",term);
		fprintf(fd,"set title \"%s Loss Profile Along Path Between %s and %s (%.2f%c azimuth)\"\n",splat_name, destination.name, source.name, Azimuth(destination,source),176);

		if (metric)
			fprintf(fd,"set xlabel \"Distance Between %s and %s (%.2f kilometers)\"\n",destination.name,source.name,KM_PER_MILE*Distance(destination,source));
		else
			fprintf(fd,"set xlabel \"Distance Between %s and %s (%.2f miles)\"\n",destination.name,source.name,Distance(destination,source));

		if (got_azimuth_pattern || got_elevation_pattern)
			fprintf(fd,"set ylabel \"Total Path Loss (including TX antenna pattern) (dB)");
		else
		{
			if (olditm)
				fprintf(fd,"set ylabel \"Longley-Rice Path Loss (dB)");
			else
				fprintf(fd,"set ylabel \"ITWOM Version %.1f Path Loss (dB)",ITWOMVersion());
		}

		fprintf(fd,"\"\nset output \"%s.%s\"\n",basename,ext);
		fprintf(fd,"plot \"profile.gp\" title \"Path Loss\" with lines\n");

		fclose(fd);
			
		x=system("gnuplot splat.gp");

		if (x!=-1)
		{
			if (gpsav==0)
			{
				unlink("splat.gp");
				unlink("profile.gp");
				unlink("reference.gp");
			}	

			fprintf(stdout,"Path loss plot written to: \"%s.%s\"\n",basename,ext);
			fflush(stdout);
		}

		else
			fprintf(stderr,"\n*** ERROR: Error occurred invoking gnuplot!\n");
	}

	if (x!=-1 && gpsav==0)
		unlink("profile.gp");
}

void SiteReport(struct site xmtr)
{
	char	report_name[80];
	double	terrain;
	int	x, azi;
	FILE	*fd;

	sprintf(report_name,"%s-site_report.txt",xmtr.name);

	for (x=0; report_name[x]!=0; x++)
		if (report_name[x]==32 || report_name[x]==17 || report_name[x]==92 || report_name[x]==42 || report_name[x]==47)
			report_name[x]='_';	

	fd=fopen(report_name,"w");

	fprintf(fd,"\n\t--==[ %s v%s Site Analysis Report For: %s ]==--\n\n",splat_name, splat_version, xmtr.name);

	fprintf(fd,"%s\n\n",dashes);

	if (xmtr.lat>=0.0)
	{
		fprintf(fd,"Site location: %.4f North / %.4f West",xmtr.lat, xmtr.lon);
		fprintf(fd, " (%s N / ",dec2dms(xmtr.lat));
	}

	else
	{
		fprintf(fd,"Site location: %.4f South / %.4f West",-xmtr.lat, xmtr.lon);
		fprintf(fd, " (%s S / ",dec2dms(xmtr.lat));
	}

	fprintf(fd, "%s W)\n",dec2dms(xmtr.lon));

	if (metric)
	{
		fprintf(fd,"Ground elevation: %.2f meters AMSL\n",METERS_PER_FOOT*GetElevation(xmtr));
		fprintf(fd,"Antenna height: %.2f meters AGL / %.2f meters AMSL\n",METERS_PER_FOOT*xmtr.alt, METERS_PER_FOOT*(xmtr.alt+GetElevation(xmtr)));
	}

	else
	{
		fprintf(fd,"Ground elevation: %.2f feet AMSL\n",GetElevation(xmtr));
		fprintf(fd,"Antenna height: %.2f feet AGL / %.2f feet AMSL\n",xmtr.alt, xmtr.alt+GetElevation(xmtr));
	}

	terrain=haat(xmtr);

	if (terrain>-4999.0)
	{
		if (metric)
			fprintf(fd,"Antenna height above average terrain: %.2f meters\n\n",METERS_PER_FOOT*terrain);
		else
			fprintf(fd,"Antenna height above average terrain: %.2f feet\n\n",terrain);

		/* Display the average terrain between 2 and 10 miles
		   from the transmitter site at azimuths of 0, 45, 90,
		   135, 180, 225, 270, and 315 degrees. */

		for (azi=0; azi<=315; azi+=45)
		{
			fprintf(fd,"Average terrain at %3d degrees azimuth: ",azi);
			terrain=AverageTerrain(xmtr,(double)azi,2.0,10.0);

			if (terrain>-4999.0)
			{
				if (metric)
					fprintf(fd,"%.2f meters AMSL\n",METERS_PER_FOOT*terrain);
				else
					fprintf(fd,"%.2f feet AMSL\n",terrain);
			}

			else
				fprintf(fd,"No terrain\n");
		}
	}

	fprintf(fd,"\n%s\n\n",dashes);
	fclose(fd);
	fprintf(stdout,"\nSite analysis report written to: \"%s\"\n",report_name);
}

void LoadTopoData(int max_lon, int min_lon, int max_lat, int min_lat)
{
	/* This function loads the SDF files required
	   to cover the limits of the region specified. */ 

	int x, y, width, ymin, ymax;
	width=ReduceAngle(max_lon-min_lon);

	if ((max_lon-min_lon)<=180.0)
	{
		for (y=0; y<=width; y++)
			for (x=min_lat; x<=max_lat; x++)
			{
				ymin=(int)(min_lon+(double)y);

				while (ymin<0)
					ymin+=360;

				while (ymin>=360)
					ymin-=360;

				ymax=ymin+1;

				while (ymax<0)
					ymax+=360;

				while (ymax>=360)
					ymax-=360;

				if (ippd==3600)
					snprintf(string,19,"%d:%d:%d:%d-hd",x, x+1, ymin, ymax);
				else
					snprintf(string,16,"%d:%d:%d:%d",x, x+1, ymin, ymax);
				LoadSDF(string);
			}
	}

	else
	{
		for (y=0; y<=width; y++)
			for (x=min_lat; x<=max_lat; x++)
			{
				ymin=max_lon+y;

				while (ymin<0)
					ymin+=360;

				while (ymin>=360)
					ymin-=360;
					
				ymax=ymin+1;

				while (ymax<0)
					ymax+=360;

				while (ymax>=360)
					ymax-=360;

				if (ippd==3600)
					snprintf(string,19,"%d:%d:%d:%d-hd",x, x+1, ymin, ymax);
				else
					snprintf(string,16,"%d:%d:%d:%d",x, x+1, ymin, ymax);
				LoadSDF(string);
			}
	}
}

int LoadANO(char *filename)
{
	/* This function reads a SPLAT! alphanumeric output 
	   file (-ani option) for analysis and/or map generation. */

	int	error=0, max_west, min_west, max_north, min_north;
	char	string[80], *pointer=NULL;
	double	latitude=0.0, longitude=0.0, azimuth=0.0, elevation=0.0,
		ano=0.0;
	FILE	*fd;

	fd=fopen(filename,"r");

	if (fd!=NULL)
	{
		fgets(string,78,fd);
		pointer=strchr(string,';');

		if (pointer!=NULL)
			*pointer=0;

		sscanf(string,"%d, %d",&max_west, &min_west);

		fgets(string,78,fd);
		pointer=strchr(string,';');

		if (pointer!=NULL)
			*pointer=0;

		sscanf(string,"%d, %d",&max_north, &min_north);

		fgets(string,78,fd);
		pointer=strchr(string,';');

		if (pointer!=NULL)
			*pointer=0;

		LoadTopoData(max_west-1, min_west, max_north-1, min_north);

		fprintf(stdout,"\nReading \"%s\"... ",filename);
		fflush(stdout);

		fgets(string,78,fd);
		sscanf(string,"%lf, %lf, %lf, %lf, %lf",&latitude, &longitude, &azimuth, &elevation, &ano);

		while (feof(fd)==0)
		{
			if (LR.erp==0.0)
			{
				/* Path loss */

				if (contour_threshold==0 || (fabs(ano)<=(double)contour_threshold))
				{
					ano=fabs(ano);

					if (ano>255.0)
						ano=255.0;

					PutSignal(latitude,longitude,((unsigned char)round(ano)));
				}
			}

			if (LR.erp!=0.0 && dbm!=0)
			{
				/* signal power level in dBm */

				if (contour_threshold==0 || (ano>=(double)contour_threshold))
				{
					ano=200.0+rint(ano);

					if (ano<0.0)
						ano=0.0;

					if (ano>255.0)
						ano=255.0;

					PutSignal(latitude,longitude,((unsigned char)round(ano)));
				}
			}

			if (LR.erp!=0.0 && dbm==0)
			{
				/* field strength dBuV/m */

				if (contour_threshold==0 || (ano>=(double)contour_threshold))
				{
					ano=100.0+rint(ano);

					if (ano<0.0)
						ano=0.0;

					if (ano>255.0)
						ano=255.0;

					PutSignal(latitude,longitude,((unsigned char)round(ano)));
				}
			}

			fgets(string,78,fd);
			sscanf(string,"%lf, %lf, %lf, %lf, %lf",&latitude, &longitude, &azimuth, &elevation, &ano);
		}

		fclose(fd);

	}

	else
		error=1;

	return error;
}

void WriteKML(struct site source, struct site destination)
{
	int	x, y;
	char	block, report_name[80];
	double	distance, rx_alt, tx_alt, cos_xmtr_angle,
		azimuth, cos_test_angle, test_alt;
	FILE	*fd=NULL;

	ReadPath(source,destination);

	sprintf(report_name,"%s-to-%s.kml",source.name,destination.name);

	for (x=0; report_name[x]!=0; x++)
		if (report_name[x]==32 || report_name[x]==17 || report_name[x]==92 || report_name[x]==42 || report_name[x]==47)
			report_name[x]='_';	

	fd=fopen(report_name,"w");

	fprintf(fd,"<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n");
	fprintf(fd,"<kml xmlns=\"http://earth.google.com/kml/2.0\">\n");
	fprintf(fd,"<!-- Generated by %s Version %s -->\n",splat_name, splat_version);
	fprintf(fd,"<Folder>\n");
	fprintf(fd,"<name>SPLAT! Path</name>\n");
	fprintf(fd,"<open>1</open>\n");
	fprintf(fd,"<description>Path Between %s and %s</description>\n",source.name,destination.name);

	fprintf(fd,"<Placemark>\n");
	fprintf(fd,"    <name>%s</name>\n",source.name);
	fprintf(fd,"    <description>\n");
	fprintf(fd,"       Transmit Site\n");

	if (source.lat>=0.0)
		fprintf(fd,"       <BR>%s North</BR>\n",dec2dms(source.lat));
	else
		fprintf(fd,"       <BR>%s South</BR>\n",dec2dms(source.lat));

	fprintf(fd,"       <BR>%s West</BR>\n",dec2dms(source.lon));

	azimuth=Azimuth(source,destination);
	distance=Distance(source,destination);

	if (metric)
		fprintf(fd,"       <BR>%.2f km",distance*KM_PER_MILE);
	else
		fprintf(fd,"       <BR>%.2f miles",distance);

	fprintf(fd," to %s</BR>\n       <BR>toward an azimuth of %.2f%c</BR>\n",destination.name,azimuth,176);

	fprintf(fd,"    </description>\n");
	fprintf(fd,"    <visibility>1</visibility>\n");
	fprintf(fd,"    <Style>\n");
	fprintf(fd,"      <IconStyle>\n");
	fprintf(fd,"        <Icon>\n");
	fprintf(fd,"          <href>root://icons/palette-5.png</href>\n");
	fprintf(fd,"          <x>224</x>\n");
	fprintf(fd,"          <y>224</y>\n");
	fprintf(fd,"          <w>32</w>\n");
	fprintf(fd,"          <h>32</h>\n");
	fprintf(fd,"        </Icon>\n");
	fprintf(fd,"      </IconStyle>\n");
	fprintf(fd,"    </Style>\n");
	fprintf(fd,"    <Point>\n");
	fprintf(fd,"      <extrude>1</extrude>\n");
	fprintf(fd,"      <altitudeMode>relativeToGround</altitudeMode>\n");
	fprintf(fd,"      <coordinates>%f,%f,30</coordinates>\n",(source.lon<180.0?-source.lon:360.0-source.lon),source.lat);
	fprintf(fd,"    </Point>\n");
	fprintf(fd,"</Placemark>\n");

	fprintf(fd,"<Placemark>\n");
	fprintf(fd,"    <name>%s</name>\n",destination.name);
	fprintf(fd,"    <description>\n");
	fprintf(fd,"       Receive Site\n");

	if (destination.lat>=0.0)
		fprintf(fd,"       <BR>%s North</BR>\n",dec2dms(destination.lat));
	else
		fprintf(fd,"       <BR>%s South</BR>\n",dec2dms(destination.lat));

	fprintf(fd,"       <BR>%s West</BR>\n",dec2dms(destination.lon));

	if (metric)
		fprintf(fd,"       <BR>%.2f km",distance*KM_PER_MILE);
	else
		fprintf(fd,"       <BR>%.2f miles",distance);

	fprintf(fd," to %s</BR>\n       <BR>toward an azimuth of %.2f%c</BR>\n",source.name,Azimuth(destination,source),176);

	fprintf(fd,"    </description>\n");
	fprintf(fd,"    <visibility>1</visibility>\n");
	fprintf(fd,"    <Style>\n");
	fprintf(fd,"      <IconStyle>\n");
	fprintf(fd,"        <Icon>\n");
	fprintf(fd,"          <href>root://icons/palette-5.png</href>\n");
	fprintf(fd,"          <x>224</x>\n");
	fprintf(fd,"          <y>224</y>\n");
	fprintf(fd,"          <w>32</w>\n");
	fprintf(fd,"          <h>32</h>\n");
	fprintf(fd,"        </Icon>\n");
	fprintf(fd,"      </IconStyle>\n");
	fprintf(fd,"    </Style>\n");
	fprintf(fd,"    <Point>\n");
	fprintf(fd,"      <extrude>1</extrude>\n");
	fprintf(fd,"      <altitudeMode>relativeToGround</altitudeMode>\n");
	fprintf(fd,"      <coordinates>%f,%f,30</coordinates>\n",(destination.lon<180.0?-destination.lon:360.0-destination.lon),destination.lat);
	fprintf(fd,"    </Point>\n");
	fprintf(fd,"</Placemark>\n");

	fprintf(fd,"<Placemark>\n");
	fprintf(fd,"<name>Point-to-Point Path</name>\n");
	fprintf(fd,"  <visibility>1</visibility>\n");
	fprintf(fd,"  <open>0</open>\n");
	fprintf(fd,"  <Style>\n");
	fprintf(fd,"    <LineStyle>\n");
	fprintf(fd,"      <color>7fffffff</color>\n");
	fprintf(fd,"    </LineStyle>\n");
	fprintf(fd,"    <PolyStyle>\n");
	fprintf(fd,"       <color>7fffffff</color>\n");
	fprintf(fd,"    </PolyStyle>\n");
	fprintf(fd,"  </Style>\n");
	fprintf(fd,"  <LineString>\n");
	fprintf(fd,"    <extrude>1</extrude>\n");
	fprintf(fd,"    <tessellate>1</tessellate>\n");
	fprintf(fd,"    <altitudeMode>relativeToGround</altitudeMode>\n");
	fprintf(fd,"    <coordinates>\n");

	for (x=0; x<path.length; x++)
		fprintf(fd,"      %f,%f,5\n",(path.lon[x]<180.0?-path.lon[x]:360.0-path.lon[x]),path.lat[x]);

	fprintf(fd,"    </coordinates>\n");
	fprintf(fd,"   </LineString>\n");
	fprintf(fd,"</Placemark>\n");

	fprintf(fd,"<Placemark>\n");
	fprintf(fd,"<name>Line-of-Sight Path</name>\n");
	fprintf(fd,"  <visibility>1</visibility>\n");
	fprintf(fd,"  <open>0</open>\n");
	fprintf(fd,"  <Style>\n");
	fprintf(fd,"    <LineStyle>\n");
	fprintf(fd,"      <color>ff00ff00</color>\n");
	fprintf(fd,"    </LineStyle>\n");
	fprintf(fd,"    <PolyStyle>\n");
	fprintf(fd,"       <color>7f00ff00</color>\n");
	fprintf(fd,"    </PolyStyle>\n");
	fprintf(fd,"  </Style>\n");
	fprintf(fd,"  <LineString>\n");
	fprintf(fd,"    <extrude>1</extrude>\n");
	fprintf(fd,"    <tessellate>1</tessellate>\n");
	fprintf(fd,"    <altitudeMode>relativeToGround</altitudeMode>\n");
	fprintf(fd,"    <coordinates>\n");

	/* Walk across the "path", indentifying obstructions along the way */

	for (y=0; y<path.length; y++)
	{
		distance=5280.0*path.distance[y];
		tx_alt=earthradius+source.alt+path.elevation[0];
		rx_alt=earthradius+destination.alt+path.elevation[y];

		/* Calculate the cosine of the elevation of the
		   transmitter as seen at the temp rx point. */

		cos_xmtr_angle=((rx_alt*rx_alt)+(distance*distance)-(tx_alt*tx_alt))/(2.0*rx_alt*distance);

		for (x=y, block=0; x>=0 && block==0; x--)
		{
			distance=5280.0*(path.distance[y]-path.distance[x]);
			test_alt=earthradius+path.elevation[x];

			cos_test_angle=((rx_alt*rx_alt)+(distance*distance)-(test_alt*test_alt))/(2.0*rx_alt*distance);

			/* Compare these two angles to determine if
			   an obstruction exists.  Since we're comparing
			   the cosines of these angles rather than
			   the angles themselves, the following "if"
			   statement is reversed from what it would
			   be if the actual angles were compared. */

			if (cos_xmtr_angle>=cos_test_angle)
				block=1;
		}

		if (block)
			fprintf(fd,"      %f,%f,-30\n",(path.lon[y]<180.0?-path.lon[y]:360.0-path.lon[y]),path.lat[y]);
		else
			fprintf(fd,"      %f,%f,5\n",(path.lon[y]<180.0?-path.lon[y]:360.0-path.lon[y]),path.lat[y]);
	}

	fprintf(fd,"    </coordinates>\n");
	fprintf(fd,"  </LineString>\n");
	fprintf(fd,"</Placemark>\n");

	fprintf(fd,"    <LookAt>\n");
	fprintf(fd,"      <longitude>%f</longitude>\n",(source.lon<180.0?-source.lon:360.0-source.lon));
	fprintf(fd,"      <latitude>%f</latitude>\n",source.lat);
	fprintf(fd,"      <range>300.0</range>\n");
	fprintf(fd,"      <tilt>45.0</tilt>\n");
	fprintf(fd,"      <heading>%f</heading>\n",azimuth);
	fprintf(fd,"    </LookAt>\n");

	fprintf(fd,"</Folder>\n");
	fprintf(fd,"</kml>\n");

	fclose(fd);

	fprintf(stdout, "\nKML file written to: \"%s\"",report_name);

	fflush(stdout);
}



//(units are here always feet)
ObstructionAnalysisReturn ObstructionAnalysisBURST(struct site xmtr, struct site rcvr, double f)
{

	/* Perform an obstruction analysis along the
	   path between receiver and transmitter. */

  int los = 1; // this will be set to 0 if not los
  int first_fresnel_zone_clear = 1; // this will be set to 0 if first fresnel zone not clear
  int	x;
  struct	site site_x;
  double	h_r, h_t, h_x, h_r_orig, cos_tx_angle, cos_test_angle,
    cos_tx_angle_f1, cos_tx_angle_fpt6, d_tx, d_x,
    h_r_f1, h_r_fpt6, h_f, h_los, lambda=0.0;
  char	string[255], string_fpt6[255], string_f1[255];


  
  ReadPath(xmtr,rcvr);
    h_r=GetElevation(rcvr)+rcvr.alt+earthradius;
    
  h_r_f1=h_r;
  h_r_fpt6=h_r;
  h_r_orig=h_r;
  
    h_t=GetElevation(xmtr)+xmtr.alt+earthradius;
    
  d_tx=5280.0*Distance(rcvr,xmtr);
  cos_tx_angle=((h_r*h_r)+(d_tx*d_tx)-(h_t*h_t))/(2.0*h_r*d_tx);
  cos_tx_angle_f1=cos_tx_angle;
  cos_tx_angle_fpt6=cos_tx_angle;
  if (f)
    lambda=9.8425e8/(f*1e6);
  
  	
  
  /* At each point along the path calculate the cosine
     of a sort of "inverse elevation angle" at the receiver.
     From the antenna, 0 deg. looks at the ground, and 90 deg.
     is parallel to the ground.
     
     Start at the receiver.  If this is the lowest antenna,
     then terrain obstructions will be nearest to it.  (Plus,
     that's the way SPLAT!'s original los() did it.)
     
     Calculate cosines only.  That's sufficient to compare
     angles and it saves the extra computational burden of
     acos().  However, note the inverted comparison: if
     acos(A) > acos(B), then B > A. */
  //fprintf(stdout,"ObstructionAnalysisBURST debug 4, path.length: %d \n", path.length);
  double site_x_elev;
  for (x=path.length-1; x>0; x--)
    {
      site_x.lat=path.lat[x];
      site_x.lon=path.lon[x];
      site_x.alt=0.0;



      h_x=GetElevation(site_x)+earthradius+clutter;
      d_x=5280.0*Distance(rcvr,site_x);
      //added this to avoid nan in computation of cos_test_angle further down
      if (d_x == 0.0)
	    d_x = 0.0000000001;
      
      
      /* Deal with the LOS path first. */
      
      cos_test_angle=((h_r*h_r)+(d_x*d_x)-(h_x*h_x))/(2.0*h_r*d_x);
      

      
      while (cos_tx_angle>cos_test_angle)
	{
	  
	  h_r+=1;
	  cos_test_angle=((h_r*h_r)+(d_x*d_x)-(h_x*h_x))/(2.0*h_r*d_x);
	  cos_tx_angle=((h_r*h_r)+(d_tx*d_tx)-(h_t*h_t))/(2.0*h_r*d_tx);
	}
      
      if (f)
	{
	  /* Now clear the first Fresnel zone... */
	  
	  cos_tx_angle_f1=((h_r_f1*h_r_f1)+(d_tx*d_tx)-(h_t*h_t))/(2.0*h_r_f1*d_tx);
	  h_los=sqrt(h_r_f1*h_r_f1+d_x*d_x-2*h_r_f1*d_x*cos_tx_angle_f1);
	  h_f=h_los-sqrt(lambda*d_x*(d_tx-d_x)/d_tx);
	  
	  while (h_f<h_x)
	    {
	      h_r_f1+=1;
	      cos_tx_angle_f1=((h_r_f1*h_r_f1)+(d_tx*d_tx)-(h_t*h_t))/(2.0*h_r_f1*d_tx);
	      h_los=sqrt(h_r_f1*h_r_f1+d_x*d_x-2*h_r_f1*d_x*cos_tx_angle_f1);
	      h_f=h_los-sqrt(lambda*d_x*(d_tx-d_x)/d_tx);
	    }

	  /* and clear the 60% F1 zone. */
	  
	  cos_tx_angle_fpt6=((h_r_fpt6*h_r_fpt6)+(d_tx*d_tx)-(h_t*h_t))/(2.0*h_r_fpt6*d_tx);
	  h_los=sqrt(h_r_fpt6*h_r_fpt6+d_x*d_x-2*h_r_fpt6*d_x*cos_tx_angle_fpt6);
	  h_f=h_los-fzone_clearance*sqrt(lambda*d_x*(d_tx-d_x)/d_tx);
	  
	  while (h_f<h_x)
	    {
	      h_r_fpt6+=1;
	      cos_tx_angle_fpt6=((h_r_fpt6*h_r_fpt6)+(d_tx*d_tx)-(h_t*h_t))/(2.0*h_r_fpt6*d_tx);
	      h_los=sqrt(h_r_fpt6*h_r_fpt6+d_x*d_x-2*h_r_fpt6*d_x*cos_tx_angle_fpt6);
	      h_f=h_los-fzone_clearance*sqrt(lambda*d_x*(d_tx-d_x)/d_tx);
	    }
	}
    }
  
  
  if (h_r>h_r_orig)
    {
      
      los = 0;
      
    }
  
  else
    
	if (h_r_fpt6>h_r_orig)
	  {
	    first_fresnel_zone_clear = 0;
	    
	  }
	
	
	else{
	  
	}
	
	if (h_r_f1>h_r_orig)
	  {
	    first_fresnel_zone_clear = 0;
	    
	    if (metric){
	      
	    }
	    
	    else{
	      
	    }
	    
	  }
	
	else{
	  
	}
     
  
  if (f)
    {
      
    }
  
  ObstructionAnalysisReturn asys;
  asys.los = los;
  asys.first_fresnel_zone_clear = first_fresnel_zone_clear;
  asys.surface_distance = KM_PER_MILE*Distance(xmtr, rcvr) * 1000.0; //[m] this is the great circle distance in km
  asys.point_to_point_distance = Distance_including_ELevation(xmtr, rcvr); // [m]
  return asys;

}


Pt2PtReturn PathReportBURST(struct site source, struct site destination)
{


	/* This function returns los and the ITM
	   model loss between the source and destination locations.
    	  */


  float elev_source = GetElevation(source);
  float	elev_dest = GetElevation(destination);


  int	x, y, z, errnum;
  char	basename[255], term[30], ext[15], strmode[100],
	report_name[80], block=0, propstring[20];
  double	maxloss=-100000.0, minloss=100000.0, loss, haavt,
    angle1, angle2, azimuth, pattern=1.0, patterndB=0.0,
    total_loss=0.0, cos_xmtr_angle, cos_test_angle=0.0,
    source_alt, test_alt, dest_alt, source_alt2, dest_alt2,
    distance, elevation, four_thirds_earth, field_strength,
    free_space_loss=0.0, eirp=0.0, voltage, rxp, dBm,
    power_density;
  

  four_thirds_earth=FOUR_THIRDS*EARTHRADIUS;
  
  for (x=0; report_name[x]!=0; x++)
    if (report_name[x]==32 || report_name[x]==17 || report_name[x]==92 || report_name[x]==42 || report_name[x]==47)
      report_name[x]='_';

  
  haavt=haat(source);
  
  azimuth=Azimuth(source,destination);
  angle1=ElevationAngle(source,destination);

  angle2= ElevationAngleTwo(source,destination,earthradius);

  
  if (got_azimuth_pattern || got_elevation_pattern)
    {
      x=(int)rint(10.0*(10.0-angle2));
      
      if (x>=0 && x<=1000)
	pattern=(double)LR.antenna_pattern[(int)rint(azimuth)][x];
      
      patterndB=20.0*log10(pattern);
    }
  


  
  haavt=haat(destination);

  azimuth=Azimuth(destination,source);

  angle1=ElevationAngle(destination,source);

  angle2=ElevationAngleTwo(destination,source,earthradius);


  
  if (LR.frq_mhz>0.0)
    {
      
     
      if (LR.erp!=0.0)
	{
	  
	  dBm=10.0*(log10(LR.erp*1000.0));
	  eirp=LR.erp*1.636816521;
	  
	  dBm=10.0*(log10(eirp*1000.0));
	}
      
      ReadPath(source, destination);  /* source=TX, destination=RX */
      /* Copy elevations plus clutter along
	 path into the elev[] array. */
      
      for (x=1; x<path.length-1; x++)
	elev[x+2]=METERS_PER_FOOT*(path.elevation[x]==0.0?path.elevation[x]:(clutter+path.elevation[x]));
      
      /* Copy ending points without clutter */
      
      elev[2]=path.elevation[0]*METERS_PER_FOOT;
      elev[path.length+1]=path.elevation[path.length-1]*METERS_PER_FOOT;
      
      
      azimuth=rint(Azimuth(source,destination));
      

      for (y=2; y<(path.length-1); y++)  /* path.length-1 avoids LR error */
	{
	  distance=5280.0*path.distance[y];
	  
	    source_alt=four_thirds_earth+source.alt+path.elevation[0];
	    dest_alt=four_thirds_earth+destination.alt+path.elevation[y];
	    
	  dest_alt2=dest_alt*dest_alt;
	  source_alt2=source_alt*source_alt;
	  
	  /* Calculate the cosine of the elevation of
	     the receiver as seen by the transmitter. */
	  
	  cos_xmtr_angle=((source_alt2)+(distance*distance)-(dest_alt2))/(2.0*source_alt*distance);

	  if (got_elevation_pattern)
	    {
	      /* If an antenna elevation pattern is available, the
		 following code determines the elevation angle to
		 the first obstruction along the path. */
	      
	      for (x=2, block=0; x<y && block==0; x++)
		{
		  distance=5280.0*(path.distance[y]-path.distance[x]);
		  test_alt=four_thirds_earth+path.elevation[x];

		  /* Calculate the cosine of the elevation
		     angle of the terrain (test point)
		     as seen by the transmitter. */
		  
		  cos_test_angle=((source_alt2)+(distance*distance)-(test_alt*test_alt))/(2.0*source_alt*distance);
		  
		  /* Compare these two angles to determine if
		     an obstruction exists.  Since we're comparing
		     the cosines of these angles rather than
		     the angles themselves, the sense of the
		     following "if" statement is reversed from
		     what it would be if the angles themselves
		     were compared. */
		  
		  if (cos_xmtr_angle>=cos_test_angle)
		    block=1;
		}
	      
	      /* At this point, we have the elevation angle
		 to the first obstruction (if it exists). */
	    }
	  
	  /* Determine path loss for each point along
	     the path using ITWOM's point_to_point mode
	     starting at x=2 (number_of_points = 1), the
	     shortest distance terrain can play a role in
	     path loss. */
	  
	  elev[0]=y-1;	/* (number of points - 1) */

			/* Distance between elevation samples */
	  
	  elev[1]=METERS_PER_MILE*(path.distance[y]-path.distance[y-1]);
	  
	  if (olditm == 1){
	    
	    point_to_point_ITM(elev,source.alt*METERS_PER_FOOT,
			       destination.alt*METERS_PER_FOOT, LR.eps_dielect,
			       LR.sgm_conductivity, LR.eno_ns_surfref, LR.frq_mhz,
			       LR.radio_climate, LR.pol, LR.conf, LR.rel, loss,
			       strmode, errnum);
	  }
	  else{
	    
	    point_to_point(elev,source.alt*METERS_PER_FOOT,
			   destination.alt*METERS_PER_FOOT, LR.eps_dielect,
			   LR.sgm_conductivity, LR.eno_ns_surfref, LR.frq_mhz,
			   LR.radio_climate, LR.pol, LR.conf, LR.rel, loss,
			   strmode, errnum);
	  }

	  if (block){
	    elevation=((acos(cos_test_angle))/DEG2RAD)-90.0;
	  }
	  else{
	    elevation=((acos(cos_xmtr_angle))/DEG2RAD)-90.0;
	  }
	  /* Integrate the antenna's radiation
	     pattern into the overall path loss. */
	  
	  x=(int)rint(10.0*(10.0-elevation));

	  if (x>=0 && x<=1000)
	    {
	      pattern=(double)LR.antenna_pattern[(int)azimuth][x];
	      
	      if (pattern!=0.0)
		patterndB=20.0*log10(pattern);
	    }
	  
	  else
	    patterndB=0.0;
	  
	  total_loss=loss-patterndB;
	  
	  
	  if (total_loss>maxloss)
	    maxloss=total_loss;
	  
	  if (total_loss<minloss)
	    minloss=total_loss;
	}


      distance=Distance(source,destination);
      float free_space_loss_distance = (Distance_including_ELevation(source,destination) / 1000.0)/KM_PER_MILE; // we use the 3D distance for free_space_loss [mile]	
		
      
      if (distance!=0.0)
	{

	  float free_space_loss_original =36.6+(20.0*log10(LR.frq_mhz))+(20.0*log10(distance));
	  free_space_loss=36.6+(20.0*log10(LR.frq_mhz))+(20.0*log10(free_space_loss_distance));
	  
	}
      else{
	
      }
      
     
      if (LR.erp!=0.0)
	{
	  field_strength=(139.4+(20.0*log10(LR.frq_mhz))-total_loss)+(10.0*log10(LR.erp/1000.0));
	  
	  /* dBm is referenced to EIRP */
	  
	  rxp=eirp/(pow(10.0,(total_loss/10.0)));
	  dBm=10.0*(log10(rxp*1000.0));
	  power_density=(eirp/(pow(10.0,(total_loss-free_space_loss)/10.0)));
	  /* divide by 4*PI*distance_in_meters squared */
	  power_density/=(4.0*PI*distance*distance*2589988.11);
	  
	  voltage=1.0e6*sqrt(50.0*(eirp/(pow(10.0,(total_loss-2.14)/10.0))));
	  
	  voltage=1.0e6*sqrt(75.0*(eirp/(pow(10.0,(total_loss-2.14)/10.0))));
	  
	}
      
      
      if (olditm)
	{
	  
	}
      
      else
	{
	  
	  y=strlen(strmode);
	  
	  if (y>19)
	    y=19;

	  for (x=6; x<y; x++)
	    propstring[x-6]=strmode[x];
	  
	  propstring[x]=0;
	  
	}
      
    }
  
  

  ObstructionAnalysisReturn obstRet = ObstructionAnalysisBURST(source, destination, LR.frq_mhz);

  
  // compute Range from source to destination according to "Earth Curvature and Atmospheric Refraction Effects on Radar Signal Propagation" A:Doerry 2013, Sandia Report
  
  Pt2PtReturn retval;
  retval.los = obstRet.los;
  retval.first_fresnel_zone_clear = obstRet.first_fresnel_zone_clear;
  retval.propagation_path_loss = loss;
  retval.free_space_loss = free_space_loss;
  retval.surface_distance = obstRet.surface_distance;//KM_PER_MILE*distance * 1000.0;
  retval.point_to_point_distance = obstRet.point_to_point_distance;//radar_to_target_range_meters;
  retval.source_elevation = elev_source * METERS_PER_FOOT; 
  retval.dest_elevation = elev_dest* METERS_PER_FOOT;

  //fprintf(stdout,"PathReportBURST: los = %d, fresnel_clear = %d, prop_path_loss = %f, free_loss = %f \n ", obstRet.los, retval.first_fresnel_zone_clear, loss, free_space_loss);
  return retval;
}




BOOST_PYTHON_MODULE(libsplathd)
{

 
    using namespace boost::python;

    class_<std::vector<float> >("FloatVec")
        .def(vector_indexing_suite<std::vector<float> >());

    class_<GetLosAndLossReturn>("GetLosAndLossReturn")
      .def("readLosMatrix", &GetLosAndLossReturn::readLosMatrix)
      .def("readLossMatrix", &GetLosAndLossReturn::readLossMatrix)
      .def("readFreeLossMatrix", &GetLosAndLossReturn::readFreeLossMatrix)
      .def("readDistMatrix", &GetLosAndLossReturn::readDistMatrix);

        

    class_<prop_site>("prop_site")
      .def("initialize_heavy", &prop_site::initialize_heavy)
      .def("initialize_light", &prop_site::initialize_light)
      .def("getElevationAtLoc", &prop_site::getElevationAtLoc)
      .def("getElevationAtLocWithoutLoadingDEM", &prop_site::getElevationAtLocWithoutLoadingDEM)
      .def ("getLosAndLoss", &prop_site::getLosAndLoss)
      .def("setLatLonBoundaries", &prop_site::setLatLonBoundaries)
      .def("getLosAndLossMatrix", &prop_site::getLosAndLossMatrix, boost::python::return_value_policy<boost::python::manage_new_object>())
      .def("getLosAndLossRadial", &prop_site::getLosAndLossRadial, boost::python::return_value_policy<boost::python::manage_new_object>())
      .def("getElevationsMatrix", &prop_site::getElevationsMatrix);


}



/////////////////////////////////////// END BOOST functions 


int main(int argc, char *argv[])
{


}
