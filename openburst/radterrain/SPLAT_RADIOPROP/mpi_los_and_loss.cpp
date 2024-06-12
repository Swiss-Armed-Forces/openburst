
/**************************************************************************** \
* 	       parallelization of grid propagation loss computations             *
*    uses SPLAT!: An RF Signal Path Loss And Terrain Analysis Tool           *
******************************************************************************
*	                   
*			                 Last update: 22-March-2024								             *
******************************************************************************
* see also: https://www.boost.org/doc/libs/1_68_0/doc/html/mpi/tutorial.html *
* should be installed: libboost-mpi-dev libmpich-dev openmpi-bin             *
* run e.g.: mpiexec -np 4 ./mpi_los_and_loss 800 4 3 45.6 8.7 5000 3000 88.8 1*
* first input: the long int is the length of the shared memory dem array     *  
* second input: number of elements in the lats shared array                  * 
* third input: number of elements in the lons shared array                   *     
******************************************************************************
*                                                                            *
*  This program is free software; you can redistribute it and/or modify it   *
*  under the terms of the GNU General Public License as published by the     *
*  Free Software Foundation; either version 2 of the License or any later    *
*  version.								                                                   *
* 									                                                         *
*  This program is distributed in the hope that it will useful, but WITHOUT  *
*  ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or     *
*  FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License     *
*  for more details.							                                           *
*									                                                           *
\****************************************************************************/



#include "splatBurst.h"
#include <math.h>

namespace bmpi = boost::mpi;

int getCurrLatIndex(int ind, int nof_lats, int nof_lons){
  int lat_ind = floor ((float)ind / (float)nof_lons);
  return lat_ind;
 }
int getCurrLonIndex(int ind, int nof_lats, int nof_lons){
  int lon_ind = ind %  nof_lons;
  return lon_ind;
}

int main(int argc, char *argv[])
{
  bmpi::environment env;
  bmpi::communicator world;
  int rank = world.rank();

  std::cout << "[MPI] started process: " << world.rank() << " of " << world.size() << "." << std::endl;
  
  unsigned int len_dem_array = strtoul(argv[1], NULL, 0);
  int nof_lats = atoi(argv[2]);
  int nof_lons = atoi(argv[3]);
  int nof_los =  nof_lats * nof_lons;
  float src_lat = std::stof(argv[4]);
  float src_lon = std::stof(argv[5]);
  float src_alt_feet = std::stof(argv[6]);
  float dest_alt_feet = std::stof(argv[7]);
  float freq = std::stof(argv[8]);
  int asl = atoi(argv[9]);
  int justLos = atoi(argv[10]);
  float minlat = std::stof(argv[11]);
  float maxlat = std::stof(argv[12]);
  float minlon = std::stof(argv[13]);
  float maxlon = std::stof(argv[14]);
  int reverseDirection = atoi(argv[15]);
 										      

  ////////// MAKE variables to read shared memories (needs linker flag -lrt) /////
  if (rank ==0){
    std::cout << "MPI gotten::::: " << nof_lats << "; " << nof_lons << ", " << src_lat << ", " << src_lon << ", " << src_alt_feet << ", " << dest_alt_feet << ", "  << ", minlat = " << minlat << ", " << maxlat << ", " << minlon << ", " << maxlon << std::endl;
  }
 
  ////////////////////// LATS ////////////////////////////////////////////////////
  auto lats_shm_read = bi::shared_memory_object{
    bi::open_only, 
    "lats_shared_memory_segment",
    bi::read_only
  };

  auto lats_region_read = bi::mapped_region{lats_shm_read, bi::read_only}; 
  void* lats_pMem_read = lats_region_read.get_address(); 
  float* lats_arr_read = static_cast<float*>(lats_pMem_read);
  
  ////////////////////// LONS //////////////////////////////////////////////////////
  auto lons_shm_read = bi::shared_memory_object{
    bi::open_only, 
    "lons_shared_memory_segment",
    bi::read_only
  };
  auto lons_region_read = bi::mapped_region{lons_shm_read, bi::read_only}; 
  void* lons_pMem_read = lons_region_read.get_address(); 
  float* lons_arr_read = static_cast<float*>(lons_pMem_read);

  ////////////////////// DIST /////////////////////////////////////////////////////////
  auto dist_shm_write = bi::shared_memory_object{
    bi::open_only, 
    "dist_shared_memory_segment",
    bi::read_write
  };
  auto dist_region_write = bi::mapped_region{dist_shm_write, bi::read_write}; 
  void* dist_pMem_write = dist_region_write.get_address(); 
  float* dist_arr_write = static_cast<float*>(dist_pMem_write);

  ////////////////////// LOS /////////////////////////////////////////////////////////
  auto los_shm_write = bi::shared_memory_object{
    bi::open_only, 
    "los_shared_memory_segment",
    bi::read_write
  };

  auto los_region_write = bi::mapped_region{los_shm_write, bi::read_write}; 
  void* los_pMem_write = los_region_write.get_address(); 
  float* los_arr_write = static_cast<float*>(los_pMem_write);

  ////////////////////// PROPAGATION LOSS /////////////////////////////////////////////
  auto loss_shm_write = bi::shared_memory_object{
    bi::open_only, 
    "loss_shared_memory_segment",
    bi::read_write
  };

  auto loss_region_write = bi::mapped_region{loss_shm_write, bi::read_write}; 
  void* loss_pMem_write = loss_region_write.get_address(); 
  float* loss_arr_write = static_cast<float*>(loss_pMem_write);

  ////////////////////// FREE SPACE LOSS //////////////////////////////////////////////
  auto free_loss_shm_write = bi::shared_memory_object{
    bi::open_only, 
    "free_loss_shared_memory_segment",
    bi::read_write
  };

  auto free_loss_region_write = bi::mapped_region{free_loss_shm_write, bi::read_write}; 
  void* free_loss_pMem_write = free_loss_region_write.get_address(); 
  float* free_loss_arr_write = static_cast<float*>(free_loss_pMem_write);  
  ///////////////////////////////////////////////////////////////////////////////////////

  float diel_const = 13.0; // Earth Dielectric Constant (Relative permittivity);
  float earth_cond = 0.002; // Earth Conductivity (Siemens per meter)
  float at_bend =  301.00; // Atmospheric Bending Constant (N-units)
  float radio_climate = 5.0; // Radio Climate (5 = Continental Temperate)
  float pol = 0.0; // Polarization (0 = Horizontal, 1 = Vertical)
  float ground_clutter = 0.0; // ground clutter in feet
  float frac_of_situ = 0.5;
  float frac_of_time = 0.9;

  ///////////////////////////////////////////////////////////////////////////////////////

  prop_site p_site;
  // prepare parallel computation
  int nof_comps = nof_lats * nof_lons; // these are number of Los or LosAndLoss call to be made. divide this
  int nof_procs = world.size(); // nof processes

  int cpp = floor ((float)nof_comps / (float)nof_procs); // nof computations per process
  int leftovers = nof_comps %  nof_procs;
  // get the computations for this rank
  int curr_ind, curr_lat_ind, curr_lon_ind;
  float curr_lat, curr_lon;

  //// rank 0 with do the heavy DEM load and then inform all other processes
  if (rank == 0){
    p_site.initialize_heavy(minlat, maxlat, minlon, maxlon, diel_const, earth_cond, at_bend, radio_climate, pol, frac_of_situ, frac_of_time, ground_clutter);
  }

  world.barrier();
  std::cout << "[MPI] process: " << world.rank() << ", barrier over..starting" << std::endl;
   //////////////////////////////////////////////////NOW ALL RANKS SHOULD LIGHT INITIALIZE/////////////////////////////////////////77777
   if (rank > 0){
     std::cout << "[MPI] RANK: " << rank << ", MPI going to light_init" << std::endl;
     p_site.initialize_light(diel_const, earth_cond, at_bend, radio_climate, pol, frac_of_situ, frac_of_time, ground_clutter);
     std::cout << "[MPI] RANK: " << rank << ", finished light_init..." << std::endl;
   }

  
  //----------------------------- now rank specific stuff
  for (int i = 0; i < cpp; i++){
    curr_ind = rank*cpp + i; 
    curr_lat_ind = getCurrLatIndex(curr_ind, nof_lats, nof_lons);
    curr_lon_ind = getCurrLonIndex(curr_ind, nof_lats, nof_lons);    
    // do splat for this lat lon
    std::vector<float> ret = p_site.getLosAndLoss( src_lat, src_lon, src_alt_feet, lats_arr_read[curr_lat_ind], lons_arr_read[curr_lon_ind], dest_alt_feet, freq, asl, justLos, reverseDirection);
    
    if (rank == 0){
      std::cout << "[MPI] rank: " << rank << ", progress[%]: " << int(100.0*(float)i/float(cpp)) << std::endl;
    }
    // now write the shared mem variables
    if (justLos == 0){
      los_arr_write[curr_ind] = ret[0]; // LOS [0/1]
      loss_arr_write[curr_ind] = ret[1]; // PROPAGATION LOS [dB]
      free_loss_arr_write[curr_ind] = ret[2]; // FREE SPACE LOSS [dB]
      dist_arr_write[curr_ind] = ret[3]; // distance [km]
    }
    else{
      los_arr_write[curr_ind] = ret[0]; // LOS [0/1]
      dist_arr_write[curr_ind] = ret[3]; // point_to_point distnace [m]
      
    }
    
  }

  // -----------------------------special case for rank zero only
  if (rank == 0){
    std::cout << "nof_comps = " << nof_comps << ", cpp = " << cpp << ", leftovers = " << leftovers << std::endl;
    // handle the leftovers
    if (leftovers > 0){
      for (int i = 0; i < leftovers; i++){
	curr_ind = cpp * nof_procs + i;
	curr_lat_ind = getCurrLatIndex(curr_ind, nof_lats, nof_lons);
	curr_lon_ind = getCurrLonIndex(curr_ind, nof_lats, nof_lons);
	std::vector<float> ret = p_site.getLosAndLoss( src_lat, src_lon, src_alt_feet, lats_arr_read[curr_lat_ind], lons_arr_read[curr_lon_ind], dest_alt_feet, freq, asl, 0, reverseDirection);
	
	// now write the shared mem
	los_arr_write[curr_ind] = ret[0];
	loss_arr_write[curr_ind] = ret[1];
	free_loss_arr_write[curr_ind] = ret[2];
	dist_arr_write[curr_ind] = ret[6]; // point to point dist
	
      }
    }
   }
  
  return 0;
}


