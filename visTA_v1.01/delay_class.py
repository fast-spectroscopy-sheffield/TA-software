###############################################################################
#Obsolete import statements for the Cambridge Thorlabs stage and Newport stage classes
#
#from PyAPT import APTMotor
#from XPS_C8_drivers import XPS
###############################################################################

"""
# MAY NEED TO CHANGE THE WAY TIMES ARE CALCULATED DEPENDING ON t0 DEFINITION! #
"""

import visa

# for the long stage
from pipython import GCSDevice, pitools  # eventually change these import statements so that the pi files needed are loaded from the project directory rather than from the package
# for the short stage
from pipython.gcscommands import GCSCommands
from pipython.gcsmessages import GCSMessages
from pipython.interfaces.pisocket import PISocket
from time import sleep


class PILongStageDelay:
    def __init__(self, t0):
        self.t0 = t0
        self.stage = GCSDevice('HYDRA')  # alternatively self.stage = GCSDevice(gcsdll='PI_HydraPollux_GCS2_DLL_x64.dll') for a fail safe option
        self.stage.ConnectTCPIP(ipaddress='192.168.0.2', ipport=400)
        self.stage.VEL('1', 30.0)  # set the velocity to some low value to avoid crashes!
        pitools.startup(self.stage)
        self.stage.FRF('1')  # reference the axis
        pitools.waitontarget(self.stage, '1', timeout=300)
        self.initialized = True

    def home(self):
    		self.stage.GOH('1')
    		pitools.waitontarget(self.stage, '1', timeout=300)
    		return    
		
    def move_to(self, time_point_ps):
        new_pos_mm = self.convert_ps_to_mm(float(time_point_ps-self.t0))
        self.stage.MOV('1', new_pos_mm)
        pitools.waitontarget(self.stage, '1', timeout=300)
        return False
    
    def convert_ps_to_mm(self,time_ps):
        pos_mm = 0.299792458*time_ps/2
        return pos_mm
    
    def close(self):
        self.stage.CloseConnection()
        
    def check_times(self, times):
        all_on_stage = True
        for time in times:
            pos = self.convert_ps_to_mm(float(time-self.t0))
            if (pos>self.stage.qTMX()['1']) or (pos<self.stage.qTMN()['1']):
                all_on_stage = False
        return all_on_stage
        
    def check_time(self, time):
        on_stage = True
        pos = self.convert_ps_to_mm(float(time-self.t0))
        if (pos>self.stage.qTMX()['1']) or (pos<self.stage.qTMN()['1']):
            on_stage = False
        return on_stage
       

class PIShortStageDelay:
    def __init__(self, t0):
        self.t0 = t0
        self.gateway = PISocket(host='192.168.0.1', port=50000)
        self.stage = GCSCommands(GCSMessages(self.gateway))
        self.stage.VEL('A', 10.0)  # set the velocity to a low value to avoid crashes!
        pitools.startup(self.stage)
        self.stage.REF('A')  # reference the axis
        self.controller_error = True
        while self.controller_error:
            try:
                pitools.waitontarget(self.stage, 'A', timeout=300)
                self.controller_error = False
            except:
                sleep(0.2)
        self.initialized = True

    def home(self):
        self.stage.GOH('A')
        self.controller_error = True
        while self.controller_error:
            try:
                pitools.waitontarget(self.stage, 'A', timeout=300)
                self.controller_error = False
            except:
                sleep(0.2)
        return
		
    def move_to(self, time_point_ps):
        new_pos_mm = self.convert_ps_to_mm(float(time_point_ps-self.t0))
        self.stage.MOV('A', new_pos_mm)
        self.controller_error = True
        while self.controller_error:
            try:
                pitools.waitontarget(self.stage, 'A', timeout=300)
                self.controller_error = False
            except:
                sleep(0.2)
        return False
		
    def convert_ps_to_mm(self,time_ps):
        pos_mm = 0.299792458*time_ps/2
        return pos_mm

    def close(self):
        self.gateway.close()
		
    def check_times(self, times):
        all_on_stage = True
        for time in times:
            pos = self.convert_ps_to_mm(float(time-self.t0))
            if (pos>self.stage.qTMX()['A']) or (pos<self.stage.qTMN()['A']):
                all_on_stage = False
        return all_on_stage
        
    def check_time(self, time):
        on_stage = True
        pos = self.convert_ps_to_mm(float(time-self.t0))
        if (pos>self.stage.qTMX()['A']) or (pos<self.stage.qTMN()['A']):
            on_stage = False
        return on_stage
    
    
class InnolasPinkLaserDelay:
    def __init__(self, t0):
        self.dg_tcpip_address = 'TCPIP::192.168.0.4::INSTR'
        self.rm = visa.ResourceManager()
        self.dg = self.rm.open_resource(self.dg_tcpip_address)
        self.t0 = t0
        self.Initialize()
        self.initialized=True
        
    def Initialize(self):
        self.dg.write('TSRC 1\r')  # set to external trigger
        self.dg.write('TLVL 1.0\r')  # set external trigger level
        self.dg.write('LOFF 1,0.0\r')  # set the level offset of AB channel to 0
        self.dg.write('LAMP 1,4.0\r')  # set level amplitude to +4V
        self.dg.write('LPOL 1,1\r')  # set level polarity positive
        self.dg.write('DLAY 3,2,1e-7\r')  # set output pulse width to 100 ns
        self.dg.write('DLAY 2,0,0\r')  # set output pulse delay to (arbitrary value of) 0
        
    def move_to(self, time_point_ns):
        tau_flip_request = False
        new_time = (self.t0-time_point_ns)*1E-9  # is this correct since we are delaying the pump here not the probe?
        if new_time < 0:
            tau_flip_request = True
            new_time = new_time + 0.001  # add 1ms (rep rate is 1kHz)
        self.dg.write('DLAY 2,0,{0:.5e}\r'.format(new_time))  # delay channel AB by new_time seconds from channel T0
        return tau_flip_request
    
    def close(self):
        self.dg.close()
        self.rm.close()
        
    def check_times(self,times):
        all_between_two_shots = True
        for time in times:
            new_time = (self.t0-time)*1E-9  # is this correct since we are delaying the pump here not the probe?
            if (new_time<-0.001) or (new_time>0.001):
                all_between_two_shots = False
        return all_between_two_shots
        
    def check_time(self,time):
        between_two_shots = True
        new_time = (self.t0-time)*1E-9  # is this correct since we are delaying the pump here not the probe?
        if (new_time<-0.001) or (new_time>0.001):
            between_two_shots = False
        return between_two_shots


"""
##### OBSOLETE CLASSES FROM CAMBRIDGE CODE - DON'T DELETE JUST IN CASE !  #####

class pink_laser_delay_cambridge_version:
    def __init__(self,t0):
        self.gen_gpib_address = 'GPIB::15::INSTR'
        self.rm = visa.ResourceManager()
        self.gen = self.rm.open_resource(self.gen_gpib_address)
        self.t0 = t0
        self.initialized=True
        
    def move_to(self,time_point_ns):
        tau_flip_request = False
        new_time = (self.t0-time_point_ns)*1E-9
        if new_time < 0:
            tau_flip_request = True
            new_time = new_time + 0.001
        time_point_string = '%.5e' % (new_time)
        self.gen.write('DT 2,1,'+time_point_string)
        return tau_flip_request
        
    def check_times(self,times):
        all_between_two_shots = True
        for time in times:
            new_time = (self.t0-time)*1E-9
            if (new_time<-0.001) or (new_time>0.001):
                all_between_two_shots = False
        return all_between_two_shots
        
    def check_time(self,time):
        between_two_shots = True
        new_time = (self.t0-time)*1E-9
        if (new_time<-0.001) or (new_time>0.001):
            between_two_shots = False
        return between_two_shots


class thorlabs_delay_stage:
    def __init__(self,t0):
        self.stage = APTMotor(94862873,HWTYPE=44)
        self.stage.initializeHardwareDevice()
        self.t0 = t0
        self.initialized=True
    
    def home(self):
        self.stage.go_home()
        return
        
    def move_to(self,time_point_ps):
        new_pos_mm = self.convert_ps_to_mm(float(self.t0-time_point_ps))
        self.stage.mcAbs(new_pos_mm,moveVel=50)
        return False
        
    def convert_ps_to_mm(self,time_ps):
        pos_mm = 0.29979*time_ps/2
        return pos_mm
        
    def close(self):
        self.stage.cleanUpAPT()
        return
        
    def check_times(self,times):
        all_on_stage = True
        for time in times:
            pos = self.convert_ps_to_mm(float(self.t0-time))
            if (pos>300) or (pos<0):
                all_on_stage = False
        return all_on_stage
        
    def check_time(self,time):
        on_stage = True
        pos = self.convert_ps_to_mm(float(self.t0-time))
        if (pos>300) or (pos<0):
            on_stage = False
        return on_stage
        
class newport_delay_stage:
    def __init__(self,t0):
        self.t0 = t0
        self.stage = XPS()
        self.group = 'GROUP1'
        self.positioner = self.group+'.POSITIONER'
        self.socketId = self.stage.TCP_ConnectToServer('192.168.0.254', 5001, 20)
        [errorCode, returnString] = self.stage.GroupInitialize(self.socketId,self.group)
        print([errorCode, returnString])
        if errorCode != 0:
            self.stage.GroupKill(self.socketId,self.group)
            [errorCode, returnString] = self.stage.GroupInitialize(self.socketId,self.group)
            self.stage.GroupHomeSearch(self.socketId,self.group)
        if errorCode !=0:
            self.initialized=False
        if errorCode ==0:
            self.initialized=True
        
    def home(self):
        [errorCode, returnString] = self.stage.GroupHomeSearch(self.socketId,self.group)
        return
        
    def move_to(self,time_point_ps):
        new_pos_mm = self.convert_ps_to_mm(float(self.t0-time_point_ps))
        [errorCode, returnString] = self.stage.GroupMoveAbsolute(self.socketId,self.positioner, [new_pos_mm])
        print([errorCode, returnString])
        [errorCode, currentPosition] = self.stage.GroupPositionCurrentGet(self.socketId,self.positioner, 1)
        print([errorCode, currentPosition])
        return
        
    def convert_ps_to_mm(self,time_ps):
        pos_mm = 0.29979*time_ps/2
        return pos_mm
        
    def close(self):
        self.stage.TCP_CloseSocket(self.socketId) 
        
    def check_times(self,times):
        all_on_stage = True
        for time in times:
            pos = self.convert_ps_to_mm(float(self.t0-time))
            if (pos>279) or (pos<0):
                all_on_stage = False
        return all_on_stage
        
    def check_time(self,time):
        on_stage = True
        pos = self.convert_ps_to_mm(float(self.t0-time))
        if (pos>300) or (pos<0):
            on_stage = False
        return on_stage
"""