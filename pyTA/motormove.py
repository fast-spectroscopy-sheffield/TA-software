import clr
# We assume Newport.CONEXPP.CommandInterface.dll is copied to our folder
clr.AddReference("Newport.CONEXPP.CommandInterface")
from CommandInterfaceConexPP import *
from time import sleep
from time import time
from datetime import datetime
import sys
import keyboard
import threading
import numpy as np
from queue import Queue
from queue import Empty
from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot
from PyQt5 import QtCore

class Controller(QObject):

    update_move_pos_lcd = pyqtSignal(float)
    update_move_time_lcd = pyqtSignal(float)
    update_coosc_m1_pos_lcd = pyqtSignal(float)
    update_coosc_m2_pos_lcd = pyqtSignal(float)
    update_coosc_time_lcd = pyqtSignal(float)
    update_log = pyqtSignal(str)
    # should_motor_stop = pyqtSignal(int, bool, float)
    # do_move_loop = pyqtSignal(int, float)
    stopped_move = pyqtSignal()
    stopped_cooscillation = pyqtSignal()
    def __init__(self, instrument='COM4', output=None, zeroarray=(0, 0, 0, 0), parent=None):
        super(QObject, self).__init__()
        self.controller = ConexPP()
        self.controller.OpenInstrument(instrument)
        self.errString = ''
        self.motors = [0, 0, 0, 0]
        self.positions = [0, 0, 0, 0]
        self.velocities = [0, 0, 0, 0]
        self.accelerations = [0, 0, 0, 0]
        self.jerks = [0, 0, 0, 0]
        self.software_limits = [[0, 0], [0, 0], [0, 0], [0, 0]]
        self.num_motors = 0
        self.zeroarray = zeroarray
        self.threads = []
        self.output = output
        self.move_stop_command = False
        self.parent = parent
    
    def discover(self, spec_indices=None):
        if spec_indices is None:
            spec_indices = [1, 2]# , 3, 4]
        spec_indices.sort()
        for index in spec_indices:
            result = self.controller.TS(index, "", "", self.errString)
            self.motors[index-1] = result[0]+1

        for i in range(0, 4):
            if self.motors[i]:
                result = self.controller.OR(i+1, '')
                state = "1E"
                while state == "1E":
                    result = self.controller.TS(i+1, '', '', self.errString)
                    state = result[2]
                    sleep(0.2)
                    
        self.num_motors = sum(self.motors)
        return self.motors, self.num_motors
        
    def get_motor_parameters(self):
        # get velocity, acceleration, jerk, software limits, current positions
        for i in range(0, 4):
            if self.motors[i]:
                self.velocities[i] = self.controller.VA_Get(i+1, 0, self.errString)[1]
                self.positions[i] = self.controller.TP(i+1, 0, self.errString)[1]
                self.accelerations[i] = self.controller.AC_Get(i+1, 0, self.errString)[1]
                self.jerks[i] = self.controller.JR_Get(i+1, 0, self.errString)[1]
                self.software_limits[i][0] = self.controller.SL_Get(i+1, 0, self.errString)[1]
                self.software_limits[i][1] = self.controller.SR_Get(i+1, 0, self.errString)[1]
        
        return (self.velocities, self.positions, self.accelerations, self.jerks, self.software_limits)

    def zero(self, zeroarray=None):
        if zeroarray == None:
            zeroarray = self.zeroarray
        zeroing_string = "\rZeroing motors..."
        if self.output:
            self.output(zeroing_string)
        else:
            sys.stdout.write(zeroing_string)
        for motor, motorTrue in enumerate(self.motors):
            if motorTrue:
                self.move_abs(motor + 1, zeroarray[motor])
                zeroing_string = zeroing_string + "."
                if self.output:
                    self.output(zeroing_string)
                else:
                    sys.stdout.write(zeroing_string)
        if self.output:
            self.output("Zeroing complete!")
        else:
            sys.stdout.write("\r")
            sys.stdout.flush()
            print("Zeroing complete!")

    def discover_and_zero(self, spec_indices=None):
        self.discover(spec_indices)
        self.zero()

    def move_abs(self, motor, target, verbose = False):
        if self.motors[motor-1]:
            result = self.controller.PA_Set(motor, target, self.errString)
            donecheck = False
            t_0 = time()
            while not donecheck:
                result = self.controller.TS(motor, '', '', '')
                pos = self.controller.TP(motor, 0, '')[1]
                self.positions[motor-1] = pos
                curr_time = time()-t_0
                if verbose:
                    self.update_move_pos_lcd.emit(pos)
                    self.update_move_time_lcd.emit(curr_time)
                if result[0] != -1:
                    try:
                        state = int(result[2])
                        if state in [34, 32, 33]:
                            donecheck=True
                        sleep(0.1)
                    except ValueError as err:
                        if self.output:
                            self.output("Motor {} returned unexpected state".format(motor))
                            self.output(result, err)
                        else:
                            print("Motor {} returned unexpected state".format(motor))
                            print(result, err)
                        self.motors[motor - 1] = 0
                        self.num_motors -= 1
                        if self.num_motors == 0:
                            self.close()
                else:
                    if self.output:
                        self.output("Motor {} returned error".format(motor))
                        self.output(result)
                    else:
                        print("Motor {} returned error".format(motor))
                        print(result)
                    donecheck = True
                    self.motors[motor - 1] = 0
                    self.num_motors -= 1
                    if self.num_motors == 0:
                        self.close()
                if self.move_stop_command:
                    self.controller.ST(motor, self.errString)
                    donecheck = True
                    self.move_stop_command = False
                    break
        else:
            if self.output:
                self.output("Motor "+str(motor)+" has yet to be initialised")
            else:
                print("Motor "+str(motor)+" has yet to be initialised")

                
    
    # def move_to_target(self, motor, target):
        # if self.motors[motor-1]:
            # self.should_motor_stop.connect(self.to_stop)
            # self.do_move_loop.connect(self.move_loop)
            # result = self.controller.PA_Set(motor, target, self.errString)
            # t_0 = time()
            # print("done setup: beginning loop")
            # self.do_move_loop.emit(motor, t_0)
        # return
    
    # @pyqtSlot(int, float)
    # def move_loop(self, motor, t_0):
        # result = self.controller.TS(motor, '', '', '')
        # pos = self.controller.TP(motor, 0, '')[1]
        # self.positions[motor-1] = pos
        # self.update_move_pos_lcd.emit(pos)
        # curr_time = time()-t_0
        # self.update_move_time_lcd.emit(curr_time)
        # donecheck = False
        # if result[0] != -1:
            # try:
                # state = int(result[2])
                # if state in [34, 32, 33]:
                    # donecheck=True
                # sleep(0.5)
            # except ValueError as err:
                # # connect this to log
                # self.motors[motor - 1] = 0
                # self.num_motors -= 1
                # if self.num_motors == 0:
                    # self.close()
                # pass
        # else:
            # # connect this to log
            # self.motors[motor - 1] = 0
            # self.num_motors -= 1
            # if self.num_motors == 0:
                # self.close()
        # print("move_loop")
        # self.should_motor_stop.emit(motor, donecheck, t_0)
        # # self.to_stop(motor, donecheck, t_0)
        # return
    
    # @pyqtSlot(int, bool, float)
    # def to_stop(self, motor, donecheck, t_0):
        # if self.move_stop_command or donecheck:
            # self.controller.ST(motor, self.errString)
            # self.moveToThread(self.parent.main_thread)
            # # self.should_motor_stop.disconnect(self.to_stop)
            # # self.do_move_loop.disconnect(self.move_loop)
            # print("to_stop: stopping")
            # self.stopped_move.emit()
            # return
        # else:
            # print("to_stop: continuing")
            # self.do_move_loop.emit(motor, t_0)
            # print("should call after each loop")
            # # self.move_loop(motor, t_0)
            # return

    def oscillate(self, motor, target1, target2, stopkey=None):
        state = 28
        targets = [target1, target2]
        target_index = 0
        result = ""
        if stopkey is None:
            stopkey = str(motor)
        if self.output:
            self.output("Commencing oscillation...")
        else:
            print("Commencing oscillation...")
        try:
            while True:
                target = targets[target_index]
                self.move_abs(motor, target, stopkey)
                target_index = (target_index+1) % 2
                if keyboard.is_pressed(stopkey):
                    break
        except ValueError as err:
            if self.output:
                self.output(result, err)
            else:
                print(result, err)
            # self.controller.ST(motor, self.errString)
            self.motors[motor-1] = 0
            self.num_motors -= 1
            if self.num_motors == 0:
                self.close()

    def co_oscillate(self, motor1, motor2, targets1, targets2, delay=0.0):
        # so how does this need to change? I need to make it so that the first thread sends its position to the second
        # thread, which starts the motion and sends its position to the first thread and so on. I may have to change
        # how this works, fundamentally
        #
        # the best way it seems to do this is to use queues. a queue is basically an object that holds data slash an
        # object and mediates communication between two threads. you can use queue.put(data) to assign a value, object,
        # or whatever else to the queue and queue.get() to retrieve the data held in the queue.

        def cooscillation_handler(motor, targets, in_queue, out_queue, signal, savecheck=False, t_0=None):
            target_index = 0
            target = targets[target_index]
            centre = (targets[0] + targets[1])/2
            result = int(self.controller.TS(motor, '', '', '')[2])
            last_pos = float(self.controller.TP(motor, 0, '')[1])
            data = []
            t = []
            if t_0 is None:
                t_0 = time()

            if self.output:
                self.output("Commencing motor " + str(motor) + " oscillation...")
            else:
                print("Commencing motor " + str(motor) + " oscillation...")

            try:
                while True:
                    result = int(self.controller.TS(motor, '', '', '')[2])
                    if result == 28:
                        motor_pos = float(self.controller.TP(motor, 0, '')[1])
                        signal.emit(motor_pos)
                        self.positions[motor-1] = motor_pos
                        data.append(motor_pos)
                        curr_time = time()-t_0
                        t.append(curr_time)
                        self.update_coosc_time_lcd.emit(curr_time)
                        if abs(target - motor_pos) < abs(target - centre):
                            try:
                                out_queue.get(block=False)
                            except Empty:
                                pass    
                            out_queue.put(True)
                    else:
                        try:
                            out_queue.get(block=False)
                        except Empty:
                            pass    
                        out_queue.put(False)
                        in_response = in_queue.get()
                        if in_response:
                            target_index = (target_index + 1) % 2
                            target = targets[target_index]
                            self.controller.PA_Set(motor, target, self.errString)
                    if self.move_stop_command:
                        # save data to file. also save time points?
                        sys.stdout.flush()
                        if savecheck:
                            data = np.array([data])
                            t = np.array([t])
                            data_time = np.concatenate((t, data), axis=0).T
                            dmy, hms = datetime.now().strftime("%d/%m/%Y %H:%M:%S").split(" ")
                            dmy_split = dmy.split("/")
                            hms_split = hms.split(":")
                            # print(dmy_split, hms_split)
                            filename = "C:/Users/Lab_Test/Documents/CrystalStageMotor/motion_data/" + dmy_split[2]+"_"+dmy_split[1]+"_"+\
                                       dmy_split[0]+"-"+hms_split[0]+"_"+hms_split[1]+"_"+hms_split[2]+"-motor_" +\
                                       str(motor) + "_positional_data.txt"
                            np.savetxt(filename, data_time)
                            meta_file = open("cooscillation_config.txt", "r")
                            metadata = meta_file.read()
                            meta_file.close()
                            meta_save_file_name = "C:/Users/Lab_Test/Documents/CrystalStageMotor/motion_data/" + dmy_split[2]+"_"+dmy_split[1]+"_"\
                                                  + dmy_split[0]+"-"+hms_split[0]+"_"+hms_split[1]+"_"+hms_split[2] + \
                                                  "_metadata.txt"
                            meta_save_file = open(meta_save_file_name, "w")
                            meta_save_file.write(metadata)
                        break
            except ValueError as err:
                if self.output:
                    self.output(result, err)
                else:
                    print(result, err)
                # self.controller.ST(motor, self.errString)
                self.motors[motor - 1] = 0
                self.num_motors -= 1
                if self.num_motors == 0:
                    self.close()

        q1 = Queue()
        q2 = Queue()

        q1.put(True)
        q2.put(True)

        t_0 = time()

        t1 = threading.Thread(target=cooscillation_handler, args=(motor1, (targets1[0], targets1[1]), q2, q1, self.update_coosc_m1_pos_lcd,  False, t_0))
        t2 = threading.Thread(target=cooscillation_handler, args=(motor2, (targets2[0], targets2[1]), q1, q2, self.update_coosc_m2_pos_lcd, False, t_0))
        
        self.threads.append(t1)
        self.threads.append(t2)
        t1.start()
        sleep(delay)
        t2.start()
        return
        
    def setVelocity(self, motor, velocity):
        ret = self.controller.VA_Set(motor, velocity, self.errString)
        sleep(0.1)
        self.get_motor_parameters()
        return

    def setAcceleration(self, motor, acceleration):
        ret = self.controller.AC_Set(motor, acceleration, self.errString)
        sleep(0.1)
        self.get_motor_parameters()
        return
        
    def setJerk(self, motor, jerk):
        ret = self.controller.JR_Set(motor, jerk, self.errString)
        sleep(0.1)
        self.get_motor_parameters()
        return

    def close(self, init_fail = False):
        if not init_fail:
            for entry in self.threads:
                entry.join()
            for motor in self.motors:
                self.controller.ST(motor, self.errString)
            self.controller.CloseInstrument()
        # add management for motor thread from parent here
        else:
            pass


class motorHandler(QObject):
    do_motor_move = pyqtSignal(int, float)
    do_motor_cooscillate = pyqtSignal(int, int, float, float, float, float, float, float, float)
    def __init__(self, controller, parent):
        super(QObject, self).__init__()
        self.parent = parent
        self.controller = controller
    
    @pyqtSlot(int, float)
    def move(self, motor, target):
        self.controller.move_abs(motor, target, verbose=True)
        self.controller.stopped_move.emit()
    
    @pyqtSlot(int, int, float, float, float, float, float, float, float) 
    def co_oscillate(self, motor1, motor2, m1_target1, m1_target2, m2_target1, m2_target2, zero1, zero2, delay):
        self.controller.zero((zero1, zero2, 0, 0))
        self.controller.co_oscillate(motor1, motor2, (m1_target1, m1_target2), (m2_target1, m2_target2), delay)
        for entry in self.controller.threads:
            entry.join()
            self.controller.threads.remove(entry)
        self.controller.stopped_cooscillation.emit()
        return
        
if __name__ == "__main__":
    # print(struct.calcsize("P") * 8)
    # ser = serial.Serial("COM4", baudrate=9600)
    PP = Controller()
    PP.discover()
    # ser.close()
    # # PP.oscillate(1, 0, 8)
    # PP.co_oscillate(1, 2, (0, 8), (0, 8), delay=7.185)
    # # PP.move_abs(2, 3)
    # # PP.move_abs(1, 3)
    # # print(result)
    PP.close()



