import os
import ctypes as ct
import numpy as np
from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot


class StresingCameraVIS(QObject):
    def __init__(self):
        super(QObject, self).__init__()
        self.dll = ct.WinDLL(os.path.join(os.path.expanduser('~'), 'Documents', 'StresingCameras', '64bit', '64FFT1200CAM2', 'ESLSCDLL_64', 'x64', 'Release', '2cam', 'ESLSCDLL_64.dll'))
        self.board_number = 1 #Use 1 for PCI board
        self.zadr = 1 #Not needed, only if in addressed mode
        self.fft_lines = 64  # 0 for most (IR?) sensors, is number of lines for binning if FFT sensor. Set to zero by cambridge
        self.vfreq = 7  # vertical frequency for FFT sensor, given as 7 in examples from Stresing
        self.pixels = 1200 #including dummy pixels
        self.num_pixels = 1024
        self.first_pixel = 16
        self.fkt = 1 #1 for standard read, others are possible, could try 0 but unlikely
        self.sym = 0 #for FIFO, depends on sensor
        self.burst = 1 #for FIFO, depends on sensor
        self.waits = 3 #depends on sensor, sets the pixel read frequency
        self.flag816 = 1 #1 if AD resolution 12 is 16bit, =2 if 8bit
        self.pportadr = 378 #address if parallel port is used
        self.pclk = 2 #pixelclock, not used here
        self.xckdelay = 3 #Cambridge had this as 2200, 99% sure that's wrong #depends on sensor, sets a delay after xck goes high, -7 for sony sensors
        self.freq = 0 #read frequency in Haz, should be 0 if exposure time is given
        self.threadp = 15 #priority of thread, 31 is highest
        self.clear_cnt = 8 #Number of reads to clear the sensor, depends on sensor
        self.release_ms = -1 #Less than zero don't release
        self.exttrig = 1 #1 is use external trigger
        self.block_trigger = 0 #true (not 0) if one external trigger starts block of nos scans which run with internal timer
        self.adrdelay = 3 #not sure...  
        self.dat_10ns = 100 #delay after trigger
        self.setArgTypes() # Required on 64-bit to ensure that pointers to the data array have the correct type
    
    # Required on 64-bit to ensure that pointers to the data array have the correct type
    def setArgTypes(self):
        self.dll.DLLReadFFLoop.argtypes = [ct.c_uint32,
                                           np.ctypeslib.ndpointer(dtype=np.int32, ndim=2, flags=['C', 'W']),
                                           ct.c_uint32,
                                           ct.c_int32,
                                           ct.c_uint32,
                                           ct.c_uint32,
                                           ct.c_uint32,
                                           ct.c_uint32,
                                           ct.c_uint32,
                                           ct.c_uint32,
                                           ct.c_uint16,
                                           ct.c_uint8,
                                           ct.c_uint8]
        self.dll.DLLGETCCD.argtypes = [ct.c_uint32,
                                       np.ctypeslib.ndpointer(dtype=np.int32, ndim=2, flags=['C', 'W']),
                                       ct.c_uint32,
                                       ct.c_int32,
                                       ct.c_uint32]
        self.dll.DLLReadFifo.argtypes = [ct.c_uint32,
                                         np.ctypeslib.ndpointer(dtype=np.int32, ndim=2, flags=['C', 'W']),
                                         ct.c_int32]
    
    #Combined Methods to Call Camera Easily
    def Initialize(self, number_of_scans=100, exposure_time_us=10):
        self.number_of_scans = number_of_scans
        self.exposure_time_us = int(exposure_time_us)
        self.CCDDrvInit()
        self.Wait(1000000)
        #self.RsTOREG()  # may not need this? Commented out by Cambridge
        #self.Wait(1000000)
        self.InitBoard()
        self.Wait(1000000)
        self.WriteLongS0(100,52)        
        self.Wait(1000000)
        self.RsTOREG()  # moved line to here to be consistent with labview
        self.Wait(1000000)
        #self.SetISPDA(0) # may not need to explicitly write this
        #self.Wait(1000000)
        self.SetISFFT(1) # needed for FFT sensors
        self.Wait(1000000)
        self.SetupVCLK()  # added. Needed for FFT sensors? although not in Cambridge apparently
        self.Wait(1000000)
        self.Cal16bit()
        self.Wait(1000000)
        self.RSFifo()
        self.Wait(1000000)
        #self.WriteLongS0(2147483648+self.dat_10ns,32)
        self.array = np.zeros((self.number_of_scans+10, self.pixels*2), dtype=np.dtype(np.int32))
        self.data = self.array[10:]
        self.Wait(1000000)
        return 
        
    def Wait(self, time_us):
        self.InitSysTimer()
        tick_start = self.TicksTimestamp()
        time_start = self.Tickstous(tick_start)
        tick_end = self.TicksTimestamp()
        time_end = self.Tickstous(tick_end)
        while (time_end - time_start) < time_us:
            tick_end = self.TicksTimestamp()
            time_end = self.Tickstous(tick_end)
        return
    
    start_acquire = pyqtSignal()
    data_ready = pyqtSignal(np.ndarray, np.ndarray, int, int)
    @pyqtSlot()
    def Acquire(self):
        self.ReadFFLoop(self.number_of_scans, self.exposure_time_us)
        self.Construct_Data_Vec()
        self.data_ready.emit(self.probe, self.reference, self.first_pixel, self.num_pixels)
        self.overflow = self.FFOvl()
        return
        
    def Construct_Data_Vec(self):
        # dtype of self.data is uint32
        hiloArray = self.data.view(np.uint16)[:, 0:self.pixels*2]  # temp = shots x (2*pixels)
        hiloArray = hiloArray.reshape(hiloArray.shape[0], 2, self.pixels)
        self.probe = hiloArray[:, 0, :]  # pointers onto self.data
        self.reference = hiloArray[:, 1, :]
    
    _exit = pyqtSignal()
    @pyqtSlot()
    def Exit(self):
        self.CCDDrvExit()
        
    ###########################################################################
    ###########################################################################
    ###########################################################################
    #Library methods from DLL (Do not Edit)
        
    def AboutDrv(self):
        self.dll.DLLAboutDrv(ct.c_uint32(self.board_number))
        
    def ActCooling(self):
        self.dll.DLLActCooling(ct.c_uint32(self.board_number),
                               ct.c_uint8(1))
                               
    def ActMouse(self):
        self.dll.DLLActMouse(ct.c_uint32(self.board_number))
    
    def Cal16bit(self):
        self.dll.DLLCal16Bit(ct.c_uint32(self.board_number),
                             ct.c_uint32(self.zadr))

    def CCDDrvExit(self):
        self.dll.DLLCCDDrvExit(ct.c_uint32(self.board_number))
        
    def CCDDrvInit(self):
        found = self.dll.DLLCCDDrvInit(ct.c_uint32(self.board_number))
        return bool(found)
        
    def CloseShutter(self):
        self.dll.DLLCloseShutter(ct.c_uint32(self.board_number))
        
    def ClrRead(self, clr_count):
        self.dll.DLLClrRead(ct.c_uint32(self.board_number),
                            ct.c_uint32(self.fft_lines),
                            ct.c_uint32(self.zadr),
                            ct.c_uint32(clr_count))
                            
    def ClrShCam(self):
        self.dll.DLLClrShCam(ct.c_uint32(self.board_number),
                             ct.c_uint32(self.zadr))
    
    def DeactMouse(self):
        self.dll.DLLDeactMouse(ct.c_uint32(self.board_number))
    
    def DisableFifo(self):
        self.dll.DLLDisableFifo(ct.c_uint32(self.board_number))
        
    def EnableFifo(self):
        self.dll.DLLEnableFifo(ct.c_uint32(self.board_number))
    
    def FFOvl(self):
        overflow = self.dll.DLLFFOvl(ct.c_uint32(self.board_number))
        return bool(overflow)
        
    def FFValid(self):
        valid = self.dll.DLLFFValid(ct.c_uint32(self.board_number))
        return bool(valid)
        
    def FlagXCKI(self):
        active = self.dll.DLLFlagXCKI(ct.c_uint32(self.board_number))
        return bool(active)
    
    # changed seond argument from self.array.ctypes.data to self.array
    # also included an argument type definition for DLLReadFFLoop
    # see setArgTypes
    # changed fkt argument to accept signed 32-bit integer (typo from Cambridge?)    
    def GetCCD(self):
        self.dll.DLLGETCCD(ct.c_uint32(self.board_number),
                           self.array,
                           ct.c_uint32(self.fft_lines),
                           ct.c_int32(self.fkt),
                           ct.c_uint32(self.zadr))
        return self.array
        
    def HighSlope(self):
        self.dll.DLLHighSlope(ct.c_uint32(self.board_number))
     
    def InitBoard(self):
        self.dll.DLLInitBoard(ct.c_uint32(self.board_number),
                              ct.c_int8(self.sym),
                              ct.c_uint8(self.burst),
                              ct.c_uint32(self.pixels),
                              ct.c_uint32(self.waits),
                              ct.c_uint32(self.flag816),
                              ct.c_uint32(self.pportadr),
                              ct.c_uint32(self.pclk),
                              ct.c_uint32(self.adrdelay))
    
    def InitSysTimer(self):
        return self.dll.DLLInitSysTimer()
        
    def LowSlope(self):
        self.dll.DLLLowSlope(ct.c_uint32(self.board_number))
    
    def OpenShutter(self):
        self.dll.DLLOpenShutter(ct.c_uint32(self.board_number))
    
    def OutTrigHigh(self):
        self.dll.DLLOutTrigHigh(ct.c_uint32(self.board_number))
        
    def OutTrigLow(self):
        self.dll.DLLOutTrigLow(ct.c_uint32(self.board_number))
    
    def OutTrigPulse(self, pulse_width):
        self.dll.DLLOutTrigPulse(ct.c_uint32(self.board_number),
                                 ct.c_uint32(pulse_width))
    
    # changed seond argument from self.array.ctypes.data to self.array
    # also included an argument type definition for DLLReadFFLoop
    # see setArgTypes
    # changed fkt argument to accept signed 32-bit integer (typo from Cambridge?)
    def ReadFifo(self):
        self.dll.DLLReadFifo(ct.c_uint32(self.board_number),
                             self.array,
                             ct.c_int32(self.fkt))
        return self.array
    
    def ReadFFCounter(self):
        counter = self.dll.DLLReadFFCounter(ct.c_uint32(self.board_number))
        return counter        
    
    # changed seond argument from self.array.ctypes.data to self.array
    # also included an argument type definition for DLLReadFFLoop
    # see setArgTypes
    def ReadFFLoop(self, number_of_scans, exposure_time_us):
        self.dll.DLLReadFFLoop(ct.c_uint32(self.board_number),
                               self.array,
                               ct.c_uint32(self.fft_lines),
                               ct.c_int32(self.fkt),
                               ct.c_uint32(self.zadr),
                               ct.c_uint32(number_of_scans+10),
                               ct.c_uint32(exposure_time_us),
                               ct.c_uint32(self.freq),
                               ct.c_uint32(self.threadp),
                               ct.c_uint32(self.clear_cnt),
                               ct.c_uint16(self.release_ms),
                               ct.c_uint8(self.exttrig),
                               ct.c_uint8(self.block_trigger))
                               
    def RSFifo(self):
        self.dll.DLLRSFifo(ct.c_uint32(self.board_number))
        
    def RsTOREG(self):
        self.dll.DLLRsTOREG(ct.c_uint32(self.board_number))
        
    def SetADAmpRed(self, gain):
        self.dll.DLLSetADAmpRed(ct.c_uint32(self.board_number),
                                ct.c_uint32(gain))
    
    def SetAD16Default(self):
        self.dll.DLLSetAD16Default(ct.c_uint32(self.board_number),
                                   ct.c_uint32(1))
                                   
    def SetExtTrig(self):
        self.dll.DLLSetExtTrig(ct.c_uint32(self.board_number))
        
    def StopFFTimer(self):
        self.dll.DLLStopFFTimer(ct.c_uint32(self.board_number))
        
    def SetIntTrig(self):
        self.dll.DLLSetIntTrig(ct.c_uint32(self.board_number))
        
    def SetISFFT(self, _set):
        self.dll.DLLSetISFFT(ct.c_uint32(self.board_number),
                             ct.c_uint8(_set))
    
    def SetISPDA(self, _set):
        self.dll.DLLSetISPDA(ct.c_uint32(self.board_number),
                             ct.c_uint8(_set))
                             
    def SetOvsmpl(self):
        self.dll.DLLSetOvsmpl(ct.c_uint32(self.board_number),
                              ct.c_uint32(self.zadr))
    
    def SetTemp(self, level):
        self.dll.DLLSetTemp(ct.c_uint32(self.board_number),
                            ct.c_uint32(level))
    
    def SetupDelay(self, delay):
        self.dll.DLLSetupDELAY(ct.c_uint32(self.board_number),
                               ct.c_uint32(delay))
    
    def SetupHAModule(self, fft_lines):
        self.dll.DLLSetupHAModule(ct.c_uint32(self.board_number),
                                  ct.c_uint32(fft_lines))
        
    def SetupVCLK(self):
        self.dll.DLLSetupVCLK(ct.c_uint32(self.board_number),
                              ct.c_uint32(self.fft_lines),
                              ct.c_uint8(self.vfreq))
    
    def StartTimer(self, exposure_time):
        self.dll.DLLStartTimer(ct.c_uint32(self.board_number),
                               ct.c_uint32(exposure_time))
    
    def TempGood(self, channel):
        self.dll.DLLTempGood(ct.c_uint32(self.board_number),
                             ct.c_uint32(channel))
                             
    def TicksTimestamp(self):
        ticks = self.dll.DLLTicksTimestamp()
        return ticks
        
    def Tickstous(self, ticks):
        us = self.dll.DLLTickstous(ct.c_uint64(ticks))
        return us
    
    def Von(self):
        self.dll.DLLVon(ct.c_uint32(self.board_number))
        
    def Voff(self):
        self.dll.DLLVoff(ct.c_uint32(self.board_number))
        
    def WaitforTelapsed(self, t_us):
        success = self.dll.DLLWaitforTelapsed(ct.c_uint32(t_us))
        return bool(success)
        
    def WriteLongS0(self, val, offset):
        success = self.dll.DLLWriteLongS0(ct.c_uint32(self.board_number),
                                          ct.c_uint32(val),
                                          ct.c_uint32(offset))
        return print('set dat '+str(bool(success)))
          