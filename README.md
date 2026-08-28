# TA-software
Software for the transient absorption (TA) setup.

### pyTA ###
Measurement setup and data acquisition.

### hdf5-converter ###
Conversion of data files (.hdf5) to useful things.

## usage ##
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

## development ##

Things to fix throughout the python code are denoted with `@todo`.

To update the GUI, make changes to `gui.ui` with Qt Designer (`designer.exe`), save, and then run the updater script:
```bat
conda activate pyTA
cd pyTA
python gui_update.py
```
which will update `gui.py`.

### key things to implement ###

 - [x] Set up and test NIR detectors for sub-ps TA
 - [x] Set up and test NIR detectors for nsTA
 - [ ] B-matrix referencing - the maths is all there in `dtt.py`, and is fast thanks to the DLL. Just need to figure out nicer incorporation into the GUI (_Acquisition_ tab), saving it, ...

### important things to fix ###

 - [ ] Fix the quality control algorithm in `dtt.py` so that bad data is properly rejected but we don't get stuck in a loop of retaking the data point. Not sure yet what the solution is
 - [x] Output correct metadata.txt file (e.g. seems to think we're always using the `short delay stage` currently), and output more things (the more information the better)
 - [ ] **Properly** fix weird bug in saving which motor COM port was last used (seems to be due to putting a string into the `last_instance_values.txt`; may have to fix using 'pickle'). Currently doesn't save it at all as a hack-fix!
 - [x] Fix the IR gain selection bug. Before August 2026, to use IR gain with the NIR detectors (recommended), you must **first** tick the 'IR gain' box in the hardware tab, **then** select 'NIR' in the dropdown menu. The log/history reports if it's been done correctly
 - [x] (?) Fix $\tau$-flip bugs associated with the electronic delay. We think the artefacts arised from the `sub_bgd` function in `dtt.py` and the way the arrays get reordered post-$\tau$ (note the background is always taken pre-$\tau$, so the background is now 'flipped' before subtraction in post-$\tau$). This 'fix' was made on 04-08-2026, but it needs testing in the lab with a sample demonstrating these artefacts strongly (e.g. strong background fluorescence)
 - [ ] Fix sharp features seen using electronic delay at late time delays. Could be a hardware thing...
 
### nice things to have ###
 - [x] Have *dark correction shots x* in the _Acquisition_ tab as well
 - [ ] Log scaling of kinetic plot
 - [ ] Move the hdf5-conversion tool into a new tab on the main software panel
 - [ ] Put in an option for converting to `.ufs` files in the hdf5-conversion tool (note, these open fine in the August 2026 version (4.5.14) of the associated software)
 - [ ] Show rough time remaining for an experimental run
 - [ ] _Random_ and _Bilinear_ stepping order (currently only _Linear_)
 - [ ] More options for the 'Exponential' time point model (how many points before time zero, initial spacing)
 - [x] Remove the 'Log' (notetaking) tab, as it lacks functionality and it's often confused with the other, more useful logs/histories
 - [ ] Option for saving the useful logs/histories to a .txt file?
 - [ ] Virtual or mock mode (of the whole software, or individual parts – detector, delays, ...), which may enable troubleshooting without the prescence of hardware
 - [ ] Option for $\Delta A$ view in the software, in addition to the current $\Delta T/T$ (...though maybe the logarithm required is computationally expensive?)

## acknowledgements ##

Many thanks to:
- The Optoelectronics group at the University of Cambridge, UK for some of the original code.
- Maximilian M. Horn and others from the FemtoMat group (Prof. Natalie Banerji) at the University of Bern, Switzerland for their exceptionally clear publication on B-matrix implementation in TA (Rev. Sci. Instrum. __97__, 073001 (2026); doi: 10.1063/5.0334487), and also for sharing their python code and 'fast cross-covariance' DLL `dll\CrossCovarianceMH.dll` (on the UniBe BORIS Portal, doi: https://doi.org/10.48620/97448).