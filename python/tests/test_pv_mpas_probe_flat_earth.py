# -----------------------------------------------------------------------------
# User configuration
# -----------------------------------------------------------------------------

dataset_destination_path = '/Users/seb/Desktop/mpas_flat_earth_prober'
source_filename = '/Volumes/Backup3TB/DataExploration/Data/MPAS/data/flat_n_primal/LON_LAT_NLAYER-primal_%d_0.vtu'

all_time_serie = range(50, 7201, 50)
quick_time_serie = range(100, 7201, 200)
single_time_serie = [ 50 ]

time_serie = single_time_serie

sampling_arrays = ['temperature', 'salinity']
sampling_size   = [ 500, 250, 30 ]
sampling_bounds = [ -3.2, 3.2,
                    -1.3, 1.5,
                    -3.0, 0.0 ]

# -----------------------------------------------------------------------------

from paraview import simple
from tonic.paraview.dataset_builder import *

# -----------------------------------------------------------------------------
# Pipeline creation
# -----------------------------------------------------------------------------

reader = simple.XMLUnstructuredGridReader(FileName = source_filename % time_serie[0], CellArrayStatus = sampling_arrays)

# -----------------------------------------------------------------------------
# Data Generation
# -----------------------------------------------------------------------------

dpdsb = DataProberDataSetBuilder(reader, dataset_destination_path, sampling_size, sampling_arrays, sampling_bounds)

# Add time information
dpdsb.getDataHandler().registerArgument(priority=1, name='time', values=time_serie, ui='slider', loop='modulo')

# Explore dataset
dpdsb.start()
for time in dpdsb.getDataHandler().time:
    reader.FileName = source_filename % time
    dpdsb.writeData()
dpdsb.stop()
