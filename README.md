# TA-software
Software for the transient absorption setup.

Code adapted with permission from that written by various members of the OE group at Cambridge.
Original code can be found at https://gitlab.com/Fastlab/PyTA.

### visTA
For use with the double-line VIS cameras detecting wavelengths in the visible.

#### Version Information
Current version: 1.0.1  
David Bossanyi (19-02-2019)  
<dgbossanyi1@sheffield.ac.uk>

#### To Do
Main development needed is to include pump on/off recognition. This can be achieved by connecting the chopper reference output (500Hz) to the upper opto BNC cinch connector on the PCI adapter board. The result is that the first pixel value alternates between a large negative number (should be 1 according to manual?) and 0 for pump on/off. This pixel can be accessed within the camera class as
```python
self.data[:,0]
```
So I need to adapt camera_class.py, ta_data_processing_class.py and visTA.py to take this triggering information and use it to determine pump on/off. Also need to check what gets plotted in the trigger graph on the diagnostics tab.
