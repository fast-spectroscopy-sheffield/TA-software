# TA-software
Software for the transient absorption setup.

### pyTA ###
Measurement setup and data acquisition.

_Thanks to the OE group at Cambridge for some of the original code._

### hdf5-converter ###
Conversion of data files (.hdf5) to useful things.

### usage ###
Open an anaconda command prompt and `cd` to the TA-software folder. Then activate the environment and launch the software by running:
```bat
conda activate pyTA
cd pyTA
python pyTA.py
```
Then to use the hdf5 conversion tool, run:
```bat
cd ..
cd hdf5-converter
python hdf5-converter.py
```
When finished run `conda deactivate`.

### important things to fix ###

 - Fix the wavelength marker. The problem is that the kinetic pixel is found from `plot_waves`, which is cropped by cutoff values, but the data to plot is determined from the full matrix, including the wavelengths that are cropped. The solution is, I think, to find the `kinetic_pixel` by comparing to `self.waves` instead of `self.plot_waves` in the `update_kinetics_wavelength` method.
 - Fix the quality control algorithm in `dtt.py` so that bad data is properly rejected but we don't get stuck in a loop of retaking the data point. Not sure yet what the solution is.
 - Calibration values for the high pixel are not saved properly. Always defaults to pixel 1, wavelength 401.
 
### nice things to have ###
 - log scaling of kinetic plot should be implemented at some point
 - move the hdf5-conversion tool into a new tab on the main software panel
