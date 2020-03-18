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

### known issues ###

 - wavelength marker for updating the kinetic plot does not take pixel-wavelength calibration into account
 - log scaling of kinetic plot should be implemented
