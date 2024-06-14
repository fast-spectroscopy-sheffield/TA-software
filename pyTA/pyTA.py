# general
import sys
import os
from PyQt5 import QtGui, QtCore
from PyQt5.QtCore import pyqtSlot

# gui
from gui import Ui_pyTAgui as pyTAgui

# graphics
import pyqtgraph as pg
pg.setConfigOption('background', 'w')
pg.setConfigOption('foreground', 'k')

# data processing
import numpy as np
import pandas as pd
from dtt import DataProcessing
from sweeps import SweepProcessing

# hardware
from cameras import StresingCameras, Acquisition
from delays import PILongStageDelay, PIShortStageDelay, InnolasPinkLaserDelay

# motors
import motormove as mm
import serial.tools.list_ports
from time import sleep

# metadata
import datetime

# hack to get app to display icon properly (Windows OS only?)
#import ctypes
#ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('pyTA')


class Application(QtGui.QMainWindow):
    
    def __init__(self, last_instance_filename, last_instance_values=None, preloaded=False):        
        super(Application, self).__init__()
        self.ui = pyTAgui()
        self.ui.setupUi(self)
        self.setWindowIcon(QtGui.QIcon('icon.png'))
        self.ui.tabs.setCurrentIndex(0)
        self.ui.diagnostics_tab.setEnabled(False)
        self.ui.acquisition_tab.setEnabled(False)
        self.ui.motor_tab.setEnabled(False)
        self.last_instance_filename = last_instance_filename
        self.last_instance_values = last_instance_values
        self.preloaded = preloaded
        self.camera_connected = False
        self.delay_connected = False
        self.motor_connected = False
        self.motor_controller = None
        self.comport_list = []
        self.timeunits = 'ps'
        self.xlabel = 'Wavelength / Pixel'
        self.datafolder = os.path.join(os.path.expanduser('~'), 'Documents')
        self.timefile_folder = os.path.join(os.path.expanduser('~'), 'Documents')
        self.initialize_gui_values()
        self.setup_gui_connections()
        self.main_thread = QtCore.QThread.currentThread()
        self.metadata = {}
        self.idle = True
        self.finished_acquisition = False
        self.safe_to_exit = True
        self.initialise_gui()
        self.show()
        self.motor_comport = ""
        self.write_app_status('application launched', colour='blue')
        
    def closeEvent(self, event):
        if self.safe_to_exit:
            self.save_gui_values()
            event.accept()
        else:
            event.ignore()
            self.message_unsafe_exit()
            
    def write_app_status(self, message, colour, timeout=0):
        self.ui.statusBar.clearMessage()
        self.ui.statusBar.setStyleSheet('QStatusBar{color:'+colour+';}')
        self.ui.statusBar.showMessage(message, msecs=timeout)
        return
        
    def initialize_gui_values(self):
        # dropdown menus
        self.ui.a_delaytype_dd.addItem('Pink Laser')
        self.ui.a_delaytype_dd.addItem('Long Stage')
        self.ui.a_delaytype_dd.addItem('Short Stage')
        self.ui.a_delaytype_dd.setEnabled(False)
        self.ui.d_delaytype_dd.addItem('Pink Laser')
        self.ui.d_delaytype_dd.addItem('Long Stage')
        self.ui.d_delaytype_dd.addItem('Short Stage')
        self.ui.d_delaytype_dd.setEnabled(False)
        self.ui.d_use_ir_gain.setEnabled(False)
        self.ui.d_display_mode_spectra.addItem('Probe')
        self.ui.d_display_mode_spectra.addItem('Reference')
        self.ui.a_distribution_dd.addItem('Exponential')
        self.ui.a_distribution_dd.addItem('Linear')
        self.ui.h_camera_dd.addItem('VIS')
        self.ui.h_camera_dd.addItem('NIR')
        self.ui.h_delay_dd.addItem('Pink Laser')
        self.ui.h_delay_dd.addItem('Long Stage')
        self.ui.h_delay_dd.addItem('Short Stage')
        # check COM ports for motor connection
        for comport in serial.tools.list_ports.comports():
            self.comport_list.append(comport.name)
            self.ui.h_motorCOM_dd.addItem(comport.name)
        self.ui.h_motor_disconnect_btn.setEnabled(False)
        # progress bars
        self.ui.a_measurement_progress_bar.setValue(0)
        self.ui.a_sweep_progress_bar.setValue(0)
        # other stuff
        self.ui.a_filename_le.setText('newfile')
        self.ui.a_use_calib.toggle()
        self.ui.a_use_cutoff.toggle()
        #self.ui.a_plot_log_t_cb.toggle()
        self.ui.a_plot_log_t_cb.setChecked(False)
        self.ui.a_plot_log_t_cb.setEnabled(False)
        self.use_logscale = False
        self.ui.d_use_linear_corr.setChecked(False)
        self.ui.d_use_reference.setChecked(True)
        self.ui.coosc_stop_button.setEnabled(False)
        self.ui.move_stop_button.setEnabled(False)
        # file
        if self.preloaded is False:
            self.ui.a_use_cutoff.setChecked(1)
            self.ui.a_cutoff_pixel_low.setValue(30)
            self.ui.a_cutoff_pixel_high.setValue(1000)
            self.ui.d_cutoff_pixel_low.setValue(30)
            self.ui.d_cutoff_pixel_high.setValue(1000)
            self.ui.a_use_calib.setChecked(1)
            self.ui.a_calib_pixel_low.setValue(200)
            self.ui.a_calib_pixel_high.setValue(800)
            self.ui.a_calib_wave_low.setValue(400)
            self.ui.a_calib_wave_high.setValue(700)
            self.ui.d_calib_pixel_low.setValue(200)
            self.ui.d_calib_pixel_high.setValue(800)
            self.ui.d_calib_wave_low.setValue(400)
            self.ui.d_calib_wave_high.setValue(700)
            self.ui.a_shortstage_t0.setValue(0)
            self.ui.a_longstage_t0.setValue(0)
            self.ui.a_pinklaser_t0.setValue(0)
            self.ui.d_shortstage_t0.setValue(0)
            self.ui.d_longstage_t0.setValue(0)
            self.ui.d_pinklaser_t0.setValue(0)
            self.ui.a_delaytype_dd.setCurrentIndex(0)
            self.ui.a_distribution_dd.setCurrentIndex(0)
            self.ui.a_tstart_sb.setValue(-5)
            self.ui.a_tend_sb.setValue(100)
            self.ui.a_num_tpoints_sb.setValue(100)
            self.ui.a_num_shots.setValue(200)
            self.ui.a_num_sweeps.setValue(500)
            self.ui.d_display_mode_spectra.setCurrentIndex(0)
            self.ui.d_use_ref_manip.setChecked(1)
            self.ui.d_refman_horiz_offset.setValue(0)
            self.ui.d_refman_scale_center.setValue(250)
            self.ui.d_refman_scale_factor.setValue(1)
            self.ui.d_refman_vertical_offset.setValue(0)
            self.ui.d_refman_vertical_stretch.setValue(1)
            self.ui.d_threshold_pixel.setValue(0)
            self.ui.d_threshold_value.setValue(15000)
            self.ui.d_time.setValue(100)
            self.ui.d_jogstep_sb.setValue(0.01)
            self.ui.d_use_linear_corr.setChecked(0)
            self.ui.d_dcshotfactor_sb.setValue(3)
        else:
            self.ui.a_use_cutoff.setChecked(int(self.last_instance_values['use cutoff']))
            self.ui.a_cutoff_pixel_low.setValue(int(self.last_instance_values['cutoff pixel low']))
            self.ui.a_cutoff_pixel_high.setValue(int(self.last_instance_values['cutoff pixel high']))
            self.ui.d_cutoff_pixel_low.setValue(int(self.last_instance_values['cutoff pixel low']))
            self.ui.d_cutoff_pixel_high.setValue(int(self.last_instance_values['cutoff pixel high']))
            self.ui.a_use_calib.setChecked(int(self.last_instance_values['use calib']))
            self.ui.a_calib_pixel_low.setValue(int(self.last_instance_values['calib pixel low']))
            self.ui.a_calib_pixel_high.setValue(int(self.last_instance_values['calib pixel high']))
            self.ui.a_calib_wave_low.setValue(int(self.last_instance_values['calib wavelength low']))
            self.ui.a_calib_wave_high.setValue(int(self.last_instance_values['calib wavelength high']))
            self.ui.d_calib_pixel_low.setValue(int(self.last_instance_values['calib pixel low']))
            self.ui.d_calib_pixel_high.setValue(int(self.last_instance_values['calib pixel high']))
            self.ui.d_calib_wave_low.setValue(int(self.last_instance_values['calib wavelength low']))
            self.ui.d_calib_wave_high.setValue(int(self.last_instance_values['calib wavelength high']))
            for key in self.last_instance_values.keys():
                if isinstance(self.last_instance_values[key], str):
                    if key != 'motor COM':
                        self.last_instance_values[key] = float(self.last_instance_values[key])
            self.ui.a_shortstage_t0.setValue(self.last_instance_values['short stage time zero'])
            self.ui.a_longstage_t0.setValue(self.last_instance_values['long stage time zero'])
            self.ui.a_pinklaser_t0.setValue(self.last_instance_values['pink laser time zero'])
            self.ui.d_shortstage_t0.setValue(self.last_instance_values['short stage time zero'])
            self.ui.d_longstage_t0.setValue(self.last_instance_values['long stage time zero'])
            self.ui.d_pinklaser_t0.setValue(self.last_instance_values['pink laser time zero'])
            self.ui.a_delaytype_dd.setCurrentIndex(int(self.last_instance_values['delay type']))
            self.ui.a_distribution_dd.setCurrentIndex(int(self.last_instance_values['distribution']))
            self.ui.a_tstart_sb.setValue(self.last_instance_values['tstart'])
            self.ui.a_tend_sb.setValue(self.last_instance_values['tend'])
            self.ui.a_num_tpoints_sb.setValue(int(self.last_instance_values['num tpoints']))
            self.ui.a_num_shots.setValue(int(self.last_instance_values['num shots']))
            self.ui.a_num_sweeps.setValue(int(self.last_instance_values['num sweeps']))
            self.ui.d_display_mode_spectra.setCurrentIndex(int(self.last_instance_values['d display mode spectra']))
            self.ui.d_use_ref_manip.setChecked(int(self.last_instance_values['d use ref manip']))
            self.ui.d_refman_horiz_offset.setValue(self.last_instance_values['d refman horizontal offset'])
            self.ui.d_refman_scale_center.setValue(self.last_instance_values['d refman scale center'])
            self.ui.d_refman_scale_factor.setValue(self.last_instance_values['d refman scale factor'])
            self.ui.d_refman_vertical_offset.setValue(self.last_instance_values['d refman vertical offset'])
            self.ui.d_refman_vertical_stretch.setValue(self.last_instance_values['d refman vertical stretch'])
            self.ui.d_threshold_pixel.setValue(int(self.last_instance_values['d threshold pixel']))
            self.ui.d_threshold_value.setValue(int(self.last_instance_values['d threshold value']))
            self.ui.d_time.setValue(self.last_instance_values['d time'])
            self.ui.d_dcshotfactor_sb.setValue(int(self.last_instance_values['dark correction shot factor']))
            self.ui.d_jogstep_sb.setValue(self.last_instance_values['d jogstep']) 
            if self.last_instance_values['motor COM'] in self.comport_list:
                self.ui.h_motorCOM_dd.setCurrentIndex(self.ui.h_motorCOM_dd.findText(self.last_instance_values['motor COM']))
            self.ui.coosc_m1_zero.setValue(self.last_instance_values['motor coosc zero 1'])
            self.ui.coosc_m2_zero.setValue(self.last_instance_values['motor coosc zero 2'])
            self.ui.coosc_m1_target1.setValue(self.last_instance_values['motor coosc 1 target 1'])
            self.ui.coosc_m1_target2.setValue(self.last_instance_values['motor coosc 1 target 2'])
            self.ui.coosc_m2_target1.setValue(self.last_instance_values['motor coosc 2 target 1'])
            self.ui.coosc_m2_target2.setValue(self.last_instance_values['motor coosc 2 target 2'])
            self.ui.delay_spin.setValue(self.last_instance_values['motor coosc delay'])
            self.ui.move_target_spin.setValue(self.last_instance_values['motor move target'])
            self.ui.d_dcshotfactor_sb.setValue(int(self.last_instance_values['dark correction shot factor']))
        
    def setup_gui_connections(self):
        # acquisition file stuff
        self.ui.a_folder_btn.clicked.connect(self.exec_folder_browse_btn)
        self.ui.a_filename_le.textChanged.connect(self.update_filepath)
        self.ui.a_metadata_pump_wavelength.textChanged.connect(self.metadata_changed)
        self.ui.a_metadata_pump_power.textChanged.connect(self.metadata_changed)
        self.ui.a_metadata_pump_spotsize.textChanged.connect(self.metadata_changed)
        self.ui.a_metadata_probe_wavelength.textChanged.connect(self.metadata_changed)
        self.ui.a_metadata_probe_power.textChanged.connect(self.metadata_changed)
        self.ui.a_metadata_probe_spotsize.textChanged.connect(self.metadata_changed)
        # acquisition times options
        self.ui.a_distribution_dd.currentIndexChanged.connect(self.update_times)
        self.ui.a_tstart_sb.valueChanged.connect(self.update_times)
        self.ui.a_tend_sb.valueChanged.connect(self.update_times)
        self.ui.a_num_tpoints_sb.valueChanged.connect(self.update_times)
        self.ui.a_timefile_cb.toggled.connect(self.update_use_timefile)
        self.ui.a_timefile_btn.clicked.connect(self.exec_timefile_folder_btn)
        self.ui.a_timefile_list.currentIndexChanged.connect(self.update_times_from_file)
        # aquisition acquire options
        self.ui.a_shortstage_t0.valueChanged.connect(self.update_shortstage_t0)
        self.ui.a_longstage_t0.valueChanged.connect(self.update_longstage_t0)
        self.ui.a_pinklaser_t0.valueChanged.connect(self.update_pinklaser_t0)
        self.ui.a_num_shots.valueChanged.connect(self.update_num_shots)
        self.ui.a_num_sweeps.valueChanged.connect(self.update_num_sweeps)
        self.ui.a_dcshotfactor_sb.valueChanged.connect(self.update_a_dcshotfactor)
        # acquisition calibration
        self.ui.a_use_calib.toggled.connect(self.update_use_calib)
        self.ui.a_calib_pixel_low.valueChanged.connect(self.update_calib)
        
        self.ui.a_calib_pixel_high.valueChanged.connect(self.update_calib)
        self.ui.a_calib_wave_low.valueChanged.connect(self.update_calib)
        self.ui.a_calib_wave_high.valueChanged.connect(self.update_calib)
        # acquisition cutoff
        self.ui.a_use_cutoff.toggled.connect(self.update_use_cutoff)
        self.ui.a_cutoff_pixel_low.valueChanged.connect(self.update_cutoff)
        self.ui.a_cutoff_pixel_high.valueChanged.connect(self.update_cutoff)
        # acquisition launch
        self.ui.a_run_btn.clicked.connect(self.exec_run_btn)
        self.ui.a_stop_btn.clicked.connect(self.exec_stop_btn)
        # acquisition plot options
        self.ui.a_plot_log_t_cb.toggled.connect(self.update_plot_log_t)
        # diagnostics reference manipulation
        self.ui.d_refman_vertical_stretch.valueChanged.connect(self.update_refman)
        self.ui.d_refman_vertical_offset.valueChanged.connect(self.update_refman)
        self.ui.d_refman_horiz_offset.valueChanged.connect(self.update_refman)
        self.ui.d_refman_scale_center.valueChanged.connect(self.update_refman)
        self.ui.d_refman_scale_factor.valueChanged.connect(self.update_refman)
        # diagnostics calibration
        self.ui.d_use_calib.toggled.connect(self.update_d_use_calib)
        self.ui.d_calib_pixel_low.valueChanged.connect(self.update_d_calib)
        self.ui.d_calib_pixel_high.valueChanged.connect(self.update_d_calib)
        self.ui.d_calib_wave_low.valueChanged.connect(self.update_d_calib)
        self.ui.d_calib_wave_high.valueChanged.connect(self.update_d_calib)
        # diagnostics cutoff
        self.ui.d_use_cutoff.toggled.connect(self.update_d_use_cutoff)
        self.ui.d_cutoff_pixel_low.valueChanged.connect(self.update_d_cutoff)
        self.ui.d_cutoff_pixel_high.valueChanged.connect(self.update_d_cutoff)
        # diagnstics aquire options
        self.ui.d_shortstage_t0.valueChanged.connect(self.update_d_shortstage_t0)
        self.ui.d_longstage_t0.valueChanged.connect(self.update_d_longstage_t0)
        self.ui.d_pinklaser_t0.valueChanged.connect(self.update_d_pinklaser_t0)
        self.ui.d_num_shots.valueChanged.connect(self.update_d_num_shots)
        self.ui.d_dcshotfactor_sb.valueChanged.connect(self.update_d_dcshotfactor)
        # diagnostics time
        self.ui.d_time.valueChanged.connect(self.update_d_time)
        self.ui.d_move_to_time_btn.clicked.connect(self.exec_d_move_to_time)
        self.ui.d_jogstep_sb.valueChanged.connect(self.update_d_jogstep)
        self.ui.d_jogleft.clicked.connect(self.d_jog_earlier)
        self.ui.d_jogright.clicked.connect(self.d_jog_later)
        self.ui.d_set_current_btn.clicked.connect(self.exec_d_set_current_btn)
        # diagnostics other
        self.ui.d_threshold_pixel.valueChanged.connect(self.update_threshold)
        self.ui.d_threshold_value.valueChanged.connect(self.update_threshold)
        self.ui.d_set_linear_corr_btn.clicked.connect(self.exec_d_set_linear_corr_btn)
        # diagnostics launch
        self.ui.d_run_btn.clicked.connect(self.exec_d_run_btn)
        self.ui.d_stop_btn.clicked.connect(self.exec_d_stop_btn)
        # hardware cameras
        self.ui.h_camera_dd.currentIndexChanged.connect(self.update_cameratype)
        self.ui.h_connect_camera_btn.clicked.connect(self.exec_h_camera_connect_btn)
        self.ui.h_disconnect_camera_btn.clicked.connect(self.exec_h_camera_disconnect_btn)
        # hardware delays
        self.ui.h_delay_dd.currentIndexChanged.connect(self.update_delaytype)
        self.ui.h_connect_delay_btn.clicked.connect(self.exec_h_delay_connect_btn)
        self.ui.h_disconnect_delay_btn.clicked.connect(self.exec_h_delay_disconnect_btn)

        # hardware motors
        self.ui.h_motorCOM_dd.currentIndexChanged.connect(self.update_COMport)
        self.ui.h_motor_connect_btn.clicked.connect(self.exec_h_motor_connect_btn)
        self.ui.h_motor_disconnect_btn.clicked.connect(self.exec_h_motor_disconnect_btn)
        # motor cooscillate
        self.ui.coosc_run_button.clicked.connect(self.exec_coosc_run_button)
        self.ui.coosc_stop_button.clicked.connect(self.exec_coosc_stop_button)
        self.ui.delay_spin.valueChanged.connect(self.update_motor_delay)
        self.ui.motor_1_index_spin.currentIndexChanged.connect(self.update_motor_1_coosc_index)
        self.ui.motor_2_index_spin.currentIndexChanged.connect(self.update_motor_2_coosc_index)
        # motor cooscillate m1
        self.ui.coosc_m1_target1.valueChanged.connect(self.update_m1_coosc_target1)
        self.ui.coosc_m1_target2.valueChanged.connect(self.update_m1_coosc_target2)
        self.ui.coosc_m1_zero.valueChanged.connect(self.update_m1_coosc_zero)
        # motor cooscillate m2
        self.ui.coosc_m2_target1.valueChanged.connect(self.update_m2_coosc_target1)
        self.ui.coosc_m2_target2.valueChanged.connect(self.update_m2_coosc_target2)
        self.ui.coosc_m2_zero.valueChanged.connect(self.update_m2_coosc_zero)
        # motor move
        self.ui.motor_move_index_spin.currentIndexChanged.connect(self.update_move_motor_index)
        self.ui.move_run_button.clicked.connect(self.exec_move_run_button)
        self.ui.move_stop_button.clicked.connect(self.exec_move_stop_button)
        self.ui.move_target_spin.valueChanged.connect(self.update_move_target)
        # motor parameters
        self.ui.param_accel_spin.valueChanged.connect(self.update_motor_acceleration)
        self.ui.param_jerk_spin.valueChanged.connect(self.update_motor_jerk)
        self.ui.param_velocity_spin.valueChanged.connect(self.update_motor_velocity)
        self.ui.param_motor_index.currentIndexChanged.connect(self.update_param_motor_index)
        
    def initialise_gui(self):
        #self.pinklaser_t0 = self.ui.a_pinklaser_t0.value()
        #self.longstage_t0 = self.ui.a_longstage_t0.value()
        #self.shortstage_t0 = self.ui.a_shortstage_t0.value()
        self.update_pinklaser_t0()
        self.update_longstage_t0()
        self.update_shortstage_t0()
        self.update_calib()
        self.update_cutoff()
        self.update_num_shots()
        self.update_num_sweeps()
        self.update_plot_log_t()
        self.update_refman()
        self.update_threshold()
        self.update_use_calib()
        self.update_use_cutoff()
        self.update_d_time()
        self.update_d_jogstep()
        self.update_cameratype()
        self.update_delaytype()
        self.update_use_timefile()
        self.update_use_ir_gain()
        self.update_times()
        self.update_xlabel()
        self.update_filepath()
        self.update_d_dcshotfactor()
        self.update_COMport()
        
    def save_gui_values(self):
        self.last_instance_values['use cutoff'] = 1 if self.ui.a_use_cutoff.isChecked() else 0
        self.last_instance_values['cutoff pixel low'] = self.ui.a_cutoff_pixel_low.value()
        self.last_instance_values['cutoff pixel high'] = self.ui.a_cutoff_pixel_high.value()
        self.last_instance_values['use calib'] = 1 if self.ui.a_use_calib.isChecked() else 0
        self.last_instance_values['calib pixel low'] = self.ui.a_calib_pixel_low.value()
        self.last_instance_values['calib pixel high'] = self.ui.a_calib_pixel_high.value()
        self.last_instance_values['calib wavelength low'] = self.ui.a_calib_wave_low.value()
        self.last_instance_values['calib wavelength high'] = self.ui.a_calib_wave_high.value()
        self.last_instance_values['short stage time zero'] = self.ui.a_shortstage_t0.value()
        self.last_instance_values['long stage time zero'] = self.ui.a_longstage_t0.value()
        self.last_instance_values['pink laser time zero'] = self.ui.a_pinklaser_t0.value()
        self.last_instance_values['delay type'] = self.ui.a_delaytype_dd.currentIndex()
        self.last_instance_values['distribution'] = self.ui.a_distribution_dd.currentIndex()
        self.last_instance_values['tstart'] = self.ui.a_tstart_sb.value()
        self.last_instance_values['tend'] = self.ui.a_tend_sb.value()
        self.last_instance_values['num tpoints'] = self.ui.a_num_tpoints_sb.value()
        self.last_instance_values['num shots'] = self.ui.a_num_shots.value()
        self.last_instance_values['num sweeps'] = self.ui.a_num_sweeps.value()
        self.last_instance_values['d display mode spectra'] = self.ui.d_display_mode_spectra.currentIndex()
        self.last_instance_values['d use ref manip'] = 1 if self.ui.d_use_ref_manip.isChecked() else 0
        self.last_instance_values['d refman horizontal offset'] = self.ui.d_refman_horiz_offset.value()
        self.last_instance_values['d refman scale center'] = self.ui.d_refman_scale_center.value()
        self.last_instance_values['d refman scale factor'] = self.ui.d_refman_scale_factor.value()
        self.last_instance_values['d refman vertical offset'] = self.ui.d_refman_vertical_offset.value()
        self.last_instance_values['d refman vertical stretch'] = self.ui.d_refman_vertical_stretch.value()
        self.last_instance_values['d threshold pixel'] = self.ui.d_threshold_pixel.value()
        self.last_instance_values['d threshold value'] = self.ui.d_threshold_value.value()
        self.last_instance_values['d time'] = self.ui.d_time.value()
        self.last_instance_values['d jogstep'] = self.ui.d_jogstep_sb.value()
        self.last_instance_values['motor COM'] = []
		# self.last_instance_values['motor COM'] = self.motor_comport
		# @todo there is a weird bug here where if you save self.motor_comport, e.g. as 'COM6', all the last_instance_values.txt entries are recognised as strings (I guess because COM# is definitely a string, not a float). Yields a 'ValueError: invalid literal for int() with base 10' when you start pyTA.py. I've hacked a fix by just not saving the last motor COM port (looks blank in the last_instance_values.txt) but a better fix is needed - perhaps use numbers to represent COM ports, similar to the delay type?
        self.last_instance_values['motor coosc index 1'] = self.ui.motor_1_index_spin.currentText()
        self.last_instance_values['motor coosc index 2'] = self.ui.motor_2_index_spin.currentText()
        self.last_instance_values['motor coosc zero 1'] = self.ui.coosc_m1_zero.value()
        self.last_instance_values['motor coosc zero 2'] = self.ui.coosc_m2_zero.value()
        self.last_instance_values['motor coosc 1 target 1'] = self.ui.coosc_m1_target1.value()
        self.last_instance_values['motor coosc 1 target 2'] = self.ui.coosc_m1_target2.value()
        self.last_instance_values['motor coosc 2 target 1'] = self.ui.coosc_m2_target1.value()
        self.last_instance_values['motor coosc 2 target 2'] = self.ui.coosc_m2_target2.value()
        self.last_instance_values['motor coosc delay'] = self.ui.delay_spin.value()
        self.last_instance_values['motor move index'] = self.ui.motor_move_index_spin.currentText()
        self.last_instance_values['motor move target'] = self.ui.move_target_spin.value()
        self.last_instance_values['dark correction shot factor'] = self.ui.d_dcshotfactor_sb.value()
        self.last_instance_values.to_csv(self.last_instance_filename, sep=':', header=False)
        
    def exec_h_camera_connect_btn(self):
        self.ui.h_connect_camera_btn.setEnabled(False)
        self.ui.h_camera_dd.setEnabled(False)
        self.h_update_camera_status('initialising... please wait')
        self.camera = StresingCameras(self.cameratype, self.use_ir_gain)
        self.camera.initialise()
        self.h_update_camera_status('ready')
        self.ui.h_disconnect_camera_btn.setEnabled(True)
        self.camera_connected = True
        self.safe_to_exit = False
        if self.delay_connected:
            self.ui.acquisition_tab.setEnabled(True)
            self.ui.diagnostics_tab.setEnabled(True)
        return        # hardware cameras
        self.ui.h_camera_dd.currentIndexChanged.connect(self.update_cameratype)
        self.ui.h_connect_camera_btn.clicked.connect(self.exec_h_camera_connect_btn)
        self.ui.h_disconnect_camera_btn.clicked.connect(self.exec_h_camera_disconnect_btn)
    
    def exec_h_camera_disconnect_btn(self):
        self.ui.h_disconnect_camera_btn.setEnabled(False)
        self.camera.close()
        self.h_update_camera_status('ready to connect')
        self.ui.h_connect_camera_btn.setEnabled(True)
        self.ui.h_camera_dd.setEnabled(True)
        self.camera_connected = False
        if not self.delay_connected and not self.motor_connected:
            self.safe_to_exit = True
        self.ui.acquisition_tab.setEnabled(False)
        self.ui.diagnostics_tab.setEnabled(False)
        return
    
    def h_update_camera_status(self, message):
        self.ui.h_camera_status.setText(message)
        return
    
    def update_use_ir_gain(self):
        self.use_ir_gain = self.ui.h_use_ir_gain.isChecked()
        self.ui.d_use_ir_gain.setChecked(self.use_ir_gain)
        return
    
    def update_cameratype(self):
        self.cameratype = self.ui.h_camera_dd.currentText()
        if self.cameratype == 'NIR':
            self.ui.d_use_linear_corr.setChecked(True)
            self.ui.d_use_linear_corr.setEnabled(True)
            self.ui.d_set_linear_corr_btn.setEnabled(True)
            self.use_ir_gain = True if self.ui.h_use_ir_gain.isChecked() else False
            self.num_pixels = 512
        else:
            self.ui.d_use_linear_corr.setChecked(False)
            self.ui.d_use_linear_corr.setEnabled(False)
            self.ui.d_set_linear_corr_btn.setEnabled(False)
            self.use_ir_gain = False
            self.num_pixels = 1024
        return
    
    def exec_h_delay_connect_btn(self):
        self.ui.h_connect_delay_btn.setEnabled(False)
        self.ui.h_delay_dd.setEnabled(False)
        self.h_update_delay_status('initialising... please wait')
        if self.delay_type == 2:  # short stage
            self.append_history('Connecting to short delay stage')
            self.delay = PIShortStageDelay(self.shortstage_t0)
        elif self.delay_type == 1:  # long stage
            self.append_history('Connecting to long delay stage')
            self.delay = PILongStageDelay(self.longstage_t0)
        else:  # pink laser, delay_type = 0
            self.append_history('Connecting to delay generator')
            self.delay = InnolasPinkLaserDelay(self.pinklaser_t0)
        self.delay.initialise()
        self.update_d_time_box_limits()
        self.h_update_delay_status('ready')
        self.ui.h_disconnect_delay_btn.setEnabled(True)
        self.delay_connected = True
        self.safe_to_exit = False
        if self.camera_connected:
            self.ui.acquisition_tab.setEnabled(True)
            self.ui.diagnostics_tab.setEnabled(True)
        return
    
    def exec_h_delay_disconnect_btn(self):
        self.ui.h_disconnect_delay_btn.setEnabled(False)
        self.delay.close()
        self.h_update_delay_status('ready to connect')
        self.ui.h_connect_delay_btn.setEnabled(True)
        self.ui.h_delay_dd.setEnabled(True)
        self.delay_connected = False
        if not self.camera_connected and not self.motor_connected:
            self.safe_to_exit = True
        self.ui.acquisition_tab.setEnabled(False)
        self.ui.diagnostics_tab.setEnabled(False)
        return
    
    def h_update_delay_status(self, message):
        self.ui.h_delay_status.setText(message)
        return
    
    def update_delaytype(self):
        self.delay_type = self.ui.h_delay_dd.currentIndex()
        self.ui.d_delaytype_dd.setCurrentIndex(self.delay_type)
        self.ui.a_delaytype_dd.setCurrentIndex(self.delay_type)
        if self.delay_type == 2:  # short stage
            self.ui.a_longstage_t0.setEnabled(False)
            self.ui.d_longstage_t0.setEnabled(False)
            self.ui.a_pinklaser_t0.setEnabled(False)
            self.ui.d_pinklaser_t0.setEnabled(False)
            self.ui.a_shortstage_t0.setEnabled(True)
            self.ui.d_shortstage_t0.setEnabled(True)
            self.timeunits = 'ps'
            self.update_xlabel_kinetics()
        elif self.delay_type == 1:  # long stage
            self.ui.a_shortstage_t0.setEnabled(False)
            self.ui.d_shortstage_t0.setEnabled(False)
            self.ui.a_pinklaser_t0.setEnabled(False)
            self.ui.d_pinklaser_t0.setEnabled(False)
            self.ui.a_longstage_t0.setEnabled(True)
            self.ui.d_longstage_t0.setEnabled(True)
            self.timeunits = 'ps'
            self.update_xlabel_kinetics()
        else:  # pink laser
            self.ui.a_longstage_t0.setEnabled(False)
            self.ui.d_longstage_t0.setEnabled(False)
            self.ui.a_shortstage_t0.setEnabled(False)
            self.ui.d_shortstage_t0.setEnabled(False)
            self.ui.a_pinklaser_t0.setEnabled(True)
            self.ui.d_pinklaser_t0.setEnabled(True)
            self.timeunits = 'ns'
            self.update_xlabel_kinetics()
        return
            
    def update_filepath(self):
        self.filename = self.ui.a_filename_le.text()
        self.filepath = os.path.join(self.datafolder, self.filename)
        self.ui.a_filepath_le.setText(self.filepath)
        return
   
    def exec_folder_browse_btn(self):
        self.datafolder = QtGui.QFileDialog.getExistingDirectory(None, 'Select Folder', self.datafolder)
        self.datafolder = os.path.normpath(self.datafolder)
        self.update_filepath()
        return
        
    def metadata_changed(self):
        self.metadata['pump wavelength'] = self.ui.a_metadata_pump_wavelength.text()
        self.metadata['pump power'] = self.ui.a_metadata_pump_power.text()
        self.metadata['pump size'] = self.ui.a_metadata_pump_spotsize.text()
        self.metadata['probe wavelengths'] = self.ui.a_metadata_probe_wavelength.text()
        self.metadata['probe power'] = self.ui.a_metadata_probe_power.text()
        self.metadata['probe size'] = self.ui.a_metadata_probe_power.text()
    
    def update_metadata(self): # these tell you what options/values were specified in the GUI
        self.metadata['date (yyyy-mm-dd)'] = str(datetime.date.today())
		# self.metadata['time'] = str(datetime.datetime.now().strftime('%H:%M:%S'))
        # @todo This time seems to the time a final sweep starts. i.e. if there's 10 sweeps then the time reported is the start of the 10th sweep. Probably there's a way to adjust to the start of the 1st or the end of the 10th.
        self.metadata_changed()
        self.metadata['camera type'] = self.cameratype
        if self.delay_type == 2:  # as defined in the drop down box in the GUI
            self.metadata['delay type'] = 'Short Stage'
            self.metadata['time zero'] = self.shortstage_t0
        if self.delay_type == 1:
            self.metadata['delay type'] = 'Long Stage'
            self.metadata['time zero'] = self.longstage_t0
        if self.delay_type == 0:
            self.metadata['delay type'] = 'Pink Laser'
            self.metadata['time zero'] = self.pinklaser_t0
        self.metadata['time units'] = self.timeunits
        self.metadata['num shots'] = self.num_shots
        self.metadata['dark correction shot factor'] = self.dcshotfactor
        
        self.metadata['use calibration'] = self.ui.d_use_calib.isChecked()
        self.metadata['calib pixel low'] = self.calib[0]
        self.metadata['calib pixel high'] = self.calib[1]
        self.metadata['calib wavelength low'] = self.calib[2]
        self.metadata['calib wavelength high'] = self.calib[3]
        
        self.metadata['use cutoff'] = self.use_cutoff
        self.metadata['cutoff pixel low'] = self.cutoff[0]
        self.metadata['cutoff pixel high'] = self.cutoff[1]
        
        self.metadata['use reference'] = self.ui.d_use_reference.isChecked()
        self.metadata['avg off shots'] = self.ui.d_use_avg_off_shots.isChecked()
        self.metadata['use ref manip'] = self.ui.d_use_ref_manip.isChecked()
        self.metadata['ref manip vertical stretch'] = self.refman[0] # Note that self.refman = [...] somewhere in pyTA.py
        self.metadata['ref manip vertical offset'] = self.refman[1]
        self.metadata['ref manip horizontal offset'] = self.refman[2]
        self.metadata['ref manip scale centre'] = self.refman[3]
        self.metadata['ref manip scale factor'] = self.refman[4]
        
        
    def update_use_timefile(self):
        self.use_timefile = self.ui.a_timefile_cb.isChecked()
        if self.use_timefile:
            self.ui.a_distribution_dd.setEnabled(False)
            self.ui.a_tstart_sb.setEnabled(False)
            self.ui.a_tend_sb.setEnabled(False)
            self.ui.a_num_tpoints_sb.setEnabled(False)
            self.ui.a_timefile_btn.setEnabled(True)
            self.ui.a_timefile_list.setEnabled(True)
        else:
            self.ui.a_distribution_dd.setEnabled(True)
            self.ui.a_tstart_sb.setEnabled(True)
            self.ui.a_tend_sb.setEnabled(True)
            self.ui.a_num_tpoints_sb.setEnabled(True)
            self.ui.a_timefile_btn.setEnabled(False)
            self.ui.a_timefile_list.setEnabled(False)
            self.update_times()
        return
            
    def update_times(self):
        distribution = self.ui.a_distribution_dd.currentText()
        if distribution == 'Linear':
            self.ui.a_num_tpoints_sb.setMinimum(5)
            #self.ui.a_plot_log_t_cb.setChecked(False)
        else:
            self.ui.a_num_tpoints_sb.setMinimum(25)
            #self.ui.a_plot_log_t_cb.setChecked(True)
        start_time = self.ui.a_tstart_sb.value()
        end_time = self.ui.a_tend_sb.value()
        num_points = self.ui.a_num_tpoints_sb.value()
        times = np.linspace(start_time, end_time, num_points)
        if distribution == 'Exponential':
            times = self.calculate_times_exponential(start_time, end_time, num_points)
        self.times = times
        self.display_times()
        return
    
    def exec_timefile_folder_btn(self):
        self.timefile = QtGui.QFileDialog.getOpenFileName(None, 'Select TimeFile', self.timefile_folder, 'TimeFiles (*.tf)')
        self.timefile_folder = os.path.dirname(self.timefile[0])
        if self.timefile_folder.endswith('/'):
            self.timefile_folder = self.timefile_folder[:-1]
        self.timefile = os.path.basename(self.timefile[0])
        self.load_timefiles_to_list()
        return
        
    def load_timefiles_to_list(self):
        self.ui.a_timefile_list.clear()
        self.timefiles = []
        for file in os.listdir(self.timefile_folder):
            if file.endswith('.tf'):
                self.timefiles.append(file)
        current_index = 0
        for i, timefile in enumerate(self.timefiles):
            self.ui.a_timefile_list.addItem(timefile)
            if timefile == self.timefile:
                current_index = i
        self.ui.a_timefile_list.setCurrentIndex(current_index)
        self.update_times_from_file()
        return
    
    def update_times_from_file(self):
        self.timefile = self.timefiles[self.ui.a_timefile_list.currentIndex()]
        self.times = np.genfromtxt(os.path.join(self.timefile_folder, self.timefile), dtype=float)
        self.display_times()
        return

    def display_times(self):
        self.ui.a_times_list.clear()
        for time in self.times:
            self.ui.a_times_list.appendPlainText('{0:.2f}'.format(time))
        return
    
    @staticmethod
    def calculate_times_exponential(start_time, end_time, num_points):
        num_before_zero = 20
        step = 0.1
        before_zero = np.linspace(start_time, 0, num_before_zero, endpoint=False)
        zero_onwards = np.geomspace(step, end_time+step, num_points-num_before_zero)-step
        times = np.concatenate((before_zero, zero_onwards))
        return times
    
    def update_d_time_box_limits(self):
        self.ui.d_time.setMaximum(self.delay.tmax)
        self.ui.d_time.setMinimum(self.delay.tmin)
        return
        
    def update_shortstage_t0(self):
        self.shortstage_t0 = self.ui.a_shortstage_t0.value()
        self.ui.d_shortstage_t0.setValue(self.shortstage_t0)
        if self.delay_connected:
            self.delay.t0 = self.shortstage_t0
            self.delay.set_max_min_times()
            self.update_d_time_box_limits()
        return
        
    def update_d_shortstage_t0(self):
        self.shortstage_t0 = self.ui.d_shortstage_t0.value()
        self.ui.a_shortstage_t0.setValue(self.shortstage_t0)
        if self.delay_connected:
            self.delay.t0 = self.shortstage_t0
            self.delay.set_max_min_times()
            self.update_d_time_box_limits()
        return
        
    def update_longstage_t0(self):
        self.longstage_t0 = self.ui.a_longstage_t0.value()
        self.ui.d_longstage_t0.setValue(self.longstage_t0)
        if self.delay_connected:
            self.delay.t0 = self.longstage_t0
            self.delay.set_max_min_times()
            self.update_d_time_box_limits()
        return
        
    def update_d_longstage_t0(self):
        self.longstage_t0 = self.ui.d_longstage_t0.value()
        self.ui.a_longstage_t0.setValue(self.longstage_t0)
        if self.delay_connected:
            self.delay.t0 = self.longstage_t0
            self.delay.set_max_min_times()
            self.update_d_time_box_limits()
        return
    
    def update_pinklaser_t0(self):
        self.pinklaser_t0 = self.ui.a_pinklaser_t0.value()
        self.ui.d_pinklaser_t0.setValue(self.pinklaser_t0)
        if self.delay_connected:
            self.delay.t0 = self.pinklaser_t0
            self.delay.set_max_min_times()
            self.update_d_time_box_limits()
        return
        
    def update_d_pinklaser_t0(self):
        self.pinklaser_t0 = self.ui.d_pinklaser_t0.value()
        self.ui.a_pinklaser_t0.setValue(self.pinklaser_t0)
        if self.delay_connected:
            self.delay.t0 = self.pinklaser_t0
            self.delay.set_max_min_times()
            self.update_d_time_box_limits()
        return
        
    def update_num_shots(self):
        if self.idle is True:
            self.num_shots = self.ui.a_num_shots.value()
            self.ui.d_num_shots.setValue(self.num_shots)
        return
        
    def update_d_num_shots(self):
        if self.idle is True:
            self.num_shots = self.ui.d_num_shots.value()
            self.ui.a_num_shots.setValue(self.num_shots)
        return
            
    def update_num_sweeps(self):
        if self.idle is True:
            self.num_sweeps = self.ui.a_num_sweeps.value()
        return
        
    def update_use_calib(self):
        self.use_calib = self.ui.a_use_calib.isChecked()
        self.ui.d_use_calib.setChecked(self.use_calib)
        self.update_xlabel()
        return
        
    def update_d_use_calib(self):
        self.use_calib = self.ui.d_use_calib.isChecked()
        self.ui.a_use_calib.setChecked(self.use_calib)
        self.update_xlabel()
        return
    
    def update_a_dcshotfactor(self): # Via Acquisition tab
        if self.idle == True: # Stop from being updated while a measurement is running
            self.dcshotfactor = self.ui.a_dcshotfactor_sb.value() # Update from one in Acquisition
            self.ui.d_dcshotfactor_sb.setValue(self.dcshotfactor) # Link to one in Diagnostics
        return
    
    def update_d_dcshotfactor(self): # Via Diagnostics tab
        if self.idle == True: # Stop from being updated while a measurement is running
            self.dcshotfactor = self.ui.d_dcshotfactor_sb.value() # Update from one in Diagnostics
            self.ui.a_dcshotfactor_sb.setValue(self.dcshotfactor) # Link to one in Acquisition
        return
    
    def update_xlabel(self):
        self.xlabel = 'Wavelength (nm)' if self.use_calib else 'Pixel Number'
        self.ui.a_last_shot_graph.plotItem.setLabels(bottom=self.xlabel)
        self.ui.a_spectra_graph.plotItem.setLabels(bottom=self.xlabel)
        self.ui.d_last_shot_graph.plotItem.setLabels(bottom=self.xlabel)
        self.ui.d_error_graph.plotItem.setLabels(bottom=self.xlabel)
        self.ui.d_probe_ref_graph.plotItem.setLabels(bottom=self.xlabel)
        return
    
    def update_xlabel_kinetics(self):
        label = 'Time ({0})'.format(self.timeunits)
        self.ui.a_kinetic_graph.plotItem.setLabels(bottom=label)
        return
        
    def update_calib(self):
        self.calib  = [self.ui.a_calib_pixel_low.value(),
                       self.ui.a_calib_pixel_high.value(),
                       self.ui.a_calib_wave_low.value(),
                       self.ui.a_calib_wave_high.value()]
        self.ui.d_calib_pixel_low.setValue(self.calib[0])
        self.ui.d_calib_pixel_high.setValue(self.calib[1])
        self.ui.d_calib_wave_low.setValue(self.calib[2])
        self.ui.d_calib_wave_high.setValue(self.calib[3])
        return
        
    def update_d_calib(self):
        self.calib  = [self.ui.d_calib_pixel_low.value(),
                       self.ui.d_calib_pixel_high.value(),
                       self.ui.d_calib_wave_low.value(),
                       self.ui.d_calib_wave_high.value()]
        self.ui.a_calib_pixel_low.setValue(self.calib[0])
        self.ui.a_calib_pixel_high.setValue(self.calib[1])
        self.ui.a_calib_wave_low.setValue(self.calib[2])
        self.ui.a_calib_wave_high.setValue(self.calib[3])
        return
             
    def update_use_cutoff(self):
        self.use_cutoff = self.ui.a_use_cutoff.isChecked()
        self.ui.d_use_cutoff.setChecked(self.use_cutoff)
        return
        
    def update_d_use_cutoff(self):
        self.use_cutoff = self.ui.d_use_cutoff.isChecked()
        self.ui.a_use_cutoff.setChecked(self.use_cutoff)
        return
             
    def update_cutoff(self):
        if self.ui.a_cutoff_pixel_high.value() > self.ui.a_cutoff_pixel_low.value():
            self.cutoff = [self.ui.a_cutoff_pixel_low.value(),
                           self.ui.a_cutoff_pixel_high.value()]
            self.ui.d_cutoff_pixel_low.setValue(self.cutoff[0])
            self.ui.d_cutoff_pixel_high.setValue(self.cutoff[1])
        else:
            self.append_history('Cutoff Values Incompatible')
        return
              
    def update_d_cutoff(self):
        if self.ui.d_cutoff_pixel_high.value() > self.ui.d_cutoff_pixel_low.value():
            self.cutoff = [self.ui.d_cutoff_pixel_low.value(),
                           self.ui.d_cutoff_pixel_high.value()]
            self.ui.a_cutoff_pixel_low.setValue(self.cutoff[0])
            self.ui.a_cutoff_pixel_high.setValue(self.cutoff[1])
        else:
            self.append_history('Cutoff Values Incompatible')
        return
        
    def update_plot_log_t(self):
        self.use_logscale = self.ui.a_plot_log_t_cb.isChecked()
        return
        
    def update_refman(self):
        self.refman = [self.ui.d_refman_vertical_stretch.value(),
                       self.ui.d_refman_vertical_offset.value(),
                       self.ui.d_refman_horiz_offset.value(),
                       self.ui.d_refman_scale_center.value(),
                       self.ui.d_refman_scale_factor.value()]
        return
        
    def update_threshold(self):
        self.threshold = [self.ui.d_threshold_pixel.value(),
                          self.ui.d_threshold_value.value()]
        return
        
    def update_d_time(self):
        self.d_time = self.ui.d_time.value()
        return
    
    def update_d_jogstep(self):
        self.d_jogstep = self.ui.d_jogstep_sb.value()
        return
        
    def exec_d_set_linear_corr_btn(self):
        try:
            self.linear_corr = self.bgd.set_linear_pixel_correlation()
            self.append_history('Successfully set linear pixel correction')
            print(self.linear_corr)
        except:
            self.append_history('Error setting linear pixel correction, line~774')
        return
        
    def append_history(self, message):
        self.ui.a_history.appendPlainText(message)
        self.ui.d_history.appendPlainText(message)
        return
                       
    def create_plots(self):
        self.ui.a_last_shot_graph.plotItem.setLabels(left='dtt', bottom=self.xlabel)
        self.ui.a_last_shot_graph.plotItem.showAxis('top', show=True)
        self.ui.a_last_shot_graph.plotItem.showAxis('right', show=True)

        self.ui.a_kinetic_graph.plotItem.setLabels(left='dtt', bottom='Time ({0})'.format(self.timeunits))
        self.ui.a_kinetic_graph.plotItem.showAxis('top', show=True)
        self.ui.a_kinetic_graph.plotItem.showAxis('right', show=True)
        
        self.ui.a_spectra_graph.plotItem.setLabels(left='dtt', bottom=self.xlabel)
        self.ui.a_spectra_graph.plotItem.showAxis('top', show=True)
        self.ui.a_spectra_graph.plotItem.showAxis('right', show=True)
        
        self.ui.d_last_shot_graph.plotItem.setLabels(left='dtt', bottom=self.xlabel) 
        self.ui.d_last_shot_graph.plotItem.showAxis('top', show=True)
        self.ui.d_last_shot_graph.plotItem.showAxis('right', show=True)
        
        self.ui.d_error_graph.plotItem.setLabels(left='Log(Error)', bottom=self.xlabel)
        self.ui.d_error_graph.plotItem.showAxis('top', show=True)
        self.ui.d_error_graph.plotItem.showAxis('right', show=True)
        
        self.ui.d_trigger_graph.plotItem.setLabels(left='Trigger Signal', bottom='Shot Number')
        self.ui.d_trigger_graph.plotItem.showAxis('top', show=True)
        self.ui.d_trigger_graph.plotItem.showAxis('right', show=True)
        
        self.ui.d_probe_ref_graph.plotItem.setLabels(left='Counts', bottom=self.xlabel)
        self.ui.d_probe_ref_graph.plotItem.showAxis('top', show=True)
        self.ui.d_probe_ref_graph.plotItem.showAxis('right', show=True)
        
        self.probe_error_region = pg.FillBetweenItem(brush=(255, 0, 0, 50))
        #self.ui.d_probe_ref_graph.addItem(self.probe_error_region)
        self.ref_error_region = pg.FillBetweenItem(brush=(0, 0, 255, 50))
        #self.ui.d_probe_ref_graph.addItem(self.ref_error_region)
        return
    
    def set_waves_and_times_axes(self):
        # wavelength/pixel axes
        self.waves = self.pixels_to_waves()
        if self.use_calib is True:
            self.plot_waves = self.pixels_to_waves()
        else:
            self.plot_waves = np.linspace(0, self.num_pixels-1,  self.num_pixels)
        # time axis
        self.plot_times = self.times
        return
        
    def create_plot_waves_and_times(self):
        self.set_waves_and_times_axes()

        if not self.diagnostics_on:
            self.plot_kinetic_avg = self.current_sweep.avg_data[:, self.kinetics_pixel]
            self.plot_kinetic_current = self.current_sweep.current_data[:, self.kinetics_pixel]
        
        if self.diagnostics_on is False:
            self.plot_dtt = self.current_sweep.avg_data[:]
            
        self.plot_ls = self.current_data.dtt[:]
        self.plot_probe_shot_error = self.current_data.probe_shot_error[:]
        
        if self.ui.d_use_reference.isChecked() is True:
            self.plot_ref_shot_error = self.current_data.ref_shot_error[:]
            self.plot_dtt_error = self.current_data.dtt_error[:]
            
        self.plot_probe_on = self.current_data.probe_on[:]
        self.plot_reference_on = self.current_data.reference_on[:]
        self.plot_probe_on_array = self.current_data.probe_on_array[:]
        self.plot_reference_on_array = self.current_data.reference_on_array[:]
        
        if self.use_cutoff is True:
            self.plot_waves = self.plot_waves[self.cutoff[0]:self.cutoff[1]]
            
            if self.diagnostics_on is False:
                self.plot_dtt = self.plot_dtt[:,self.cutoff[0]:self.cutoff[1]]
                
            self.plot_ls = self.plot_ls[self.cutoff[0]:self.cutoff[1]]
            self.plot_probe_shot_error = self.plot_probe_shot_error[self.cutoff[0]:self.cutoff[1]]
            
            if self.ui.d_use_reference.isChecked() is True:
                self.plot_ref_shot_error = self.plot_ref_shot_error[self.cutoff[0]:self.cutoff[1]]
                self.plot_dtt_error = self.plot_dtt_error[self.cutoff[0]:self.cutoff[1]]
                
            self.plot_probe_on = self.plot_probe_on[self.cutoff[0]:self.cutoff[1]]
            self.plot_reference_on = self.plot_reference_on[self.cutoff[0]:self.cutoff[1]]
            self.plot_probe_on_array = self.plot_probe_on_array[:,self.cutoff[0]:self.cutoff[1]]
            self.plot_reference_on_array = self.plot_reference_on_array[:,self.cutoff[0]:self.cutoff[1]]        
        return
        
    def pixels_to_waves(self):
        slope = (self.calib[3]-self.calib[2])/(self.calib[1]-self.calib[0])
        y_int = self.calib[2]-slope*self.calib[0]
        return np.linspace(0,self.num_pixels-1,self.num_pixels)*slope+y_int
                
    def ls_plot(self):
        self.ui.a_last_shot_graph.plotItem.plot(self.plot_waves, self.plot_ls, clear=True, pen='b')
        return
        
    def top_plot(self):
        self.ui.a_colourmap.setImage(self.plot_dtt, scale=(len(self.plot_waves)/len(self.times), 1))
        return
    
    def add_time_marker(self):
        finite_times = self.plot_times[np.isfinite(self.plot_times)]
        self.time_marker = pg.InfiniteLine(finite_times[int(len(finite_times)/2)], movable=True, bounds=[min(self.plot_times), max(self.plot_times)])
        self.ui.a_kinetic_graph.addItem(self.time_marker)
        self.time_marker.sigPositionChangeFinished.connect(self.update_time_pixel)
        self.time_marker_label = pg.InfLineLabel(self.time_marker, text='{value:.2f}'+self.timeunits, movable=True, position=0.9)
        self.update_time_pixel()
        return
    
    def update_time_pixel(self):
        self.spectrum_time = self.time_marker.value()
        self.time_pixel = np.where((self.plot_times-self.spectrum_time)**2 == min((self.plot_times-self.spectrum_time)**2))[0][0]
        if self.finished_acquisition:
            self.create_plot_waves_and_times()
            self.spec_plot()
        return
    
    def add_wavelength_marker(self):
        self.wavelength_marker = pg.InfiniteLine(self.plot_waves[int(len(self.plot_waves)/2)], movable=True, bounds=[min(self.plot_waves), max(self.plot_waves)])
        self.ui.a_spectra_graph.addItem(self.wavelength_marker)
        self.wavelength_marker.sigPositionChangeFinished.connect(self.update_kinetics_wavelength)
        self.wavelength_marker_label = pg.InfLineLabel(self.wavelength_marker, text='{value:.2f}nm', movable=True, position=0.9)
        self.update_kinetics_wavelength()
        return
    
    def update_kinetics_wavelength(self):
        self.kinetics_wavelength = self.wavelength_marker.value()
        self.kinetics_pixel = np.where((self.waves-self.kinetics_wavelength)**2 == min((self.waves-self.kinetics_wavelength)**2))[0][0]  # self.waves rather than self.plot_waves?
        if self.finished_acquisition:
            self.create_plot_waves_and_times()
            self.kin_plot()
        return
        
    def kin_plot(self):
        for item in self.ui.a_kinetic_graph.plotItem.listDataItems():
            self.ui.a_kinetic_graph.plotItem.removeItem(item)
        if self.finished_acquisition:
            self.ui.a_kinetic_graph.plotItem.plot(self.plot_times, self.plot_kinetic_avg, pen='b', symbol='s', symbolPen='b', symbolBrush=None, symbolSize=4, clear=False)
        else:
            if self.current_sweep.sweep_index > 0:
                self.ui.a_kinetic_graph.plotItem.plot(self.plot_times[0:self.timestep+1], self.plot_kinetic_current[0:self.timestep+1], pen='c', symbol='s', symbolPen='c', symbolBrush=None, symbolSize=4, clear=False)
                self.ui.a_kinetic_graph.plotItem.plot(self.plot_times, self.plot_kinetic_avg, pen='b', symbol='s', symbolPen='b', symbolBrush=None, symbolSize=4, clear=False)
            else:
                self.ui.a_kinetic_graph.plotItem.plot(self.plot_times[0:self.timestep+1], self.plot_kinetic_current[0:self.timestep+1], pen='c', symbol='s', symbolPen='c', symbolBrush=None, symbolSize=4, clear=False)
        return
        
    def spec_plot(self):
        for item in self.ui.a_spectra_graph.plotItem.listDataItems():
            self.ui.a_spectra_graph.plotItem.removeItem(item)
        self.ui.a_spectra_graph.plotItem.plot(self.plot_waves, self.plot_dtt[self.time_pixel,:], pen='r', clear=False)
        return
        
    def d_error_plot(self):
        self.ui.d_error_graph.plotItem.plot(self.plot_waves, np.log10(self.plot_probe_shot_error), pen='r', clear=True, fillBrush='r')
        if self.ui.d_use_reference.isChecked() is True:         
            self.ui.d_error_graph.plotItem.plot(self.plot_waves, np.log10(self.plot_ref_shot_error), pen='b', clear=False, fillBrush='b')    
            self.ui.d_error_graph.plotItem.plot(self.plot_waves, np.log10(self.plot_dtt_error), pen='g', clear=False, fillBrush='g')
        self.ui.d_error_graph.plotItem.setYRange(-4, 1, padding=0)
        return
        
    def d_trigger_plot(self):
        self.ui.d_trigger_graph.plotItem.plot(np.arange(self.num_shots), self.current_data.trigger, pen=None, symbol='o', clear=True)
        return
        
    def d_probe_ref_plot(self):
        for item in self.ui.d_probe_ref_graph.plotItem.listDataItems():
            self.ui.d_probe_ref_graph.plotItem.removeItem(item)
        probe_std = np.std(self.plot_probe_on_array, axis=0)
        self.ui.d_probe_ref_graph.plotItem.plot(self.plot_waves, self.plot_probe_on, pen='r')
        pcurve1 = pg.PlotDataItem(self.plot_waves, self.plot_probe_on-2*probe_std, pen='r')
        pcurve2 = pg.PlotDataItem(self.plot_waves, self.plot_probe_on+2*probe_std, pen='r')
        self.probe_error_region.setCurves(pcurve1, pcurve2)
        self.ui.d_probe_ref_graph.addItem(self.probe_error_region)            
        if self.ui.d_use_reference.isChecked() is True:
            ref_std = np.std(self.plot_reference_on_array, axis=0)
            self.ui.d_probe_ref_graph.plotItem.plot(self.plot_waves, self.plot_reference_on, pen='b')
            rcurve1 = pg.PlotDataItem(self.plot_waves, self.plot_reference_on-2*ref_std, pen='b')
            rcurve2 = pg.PlotDataItem(self.plot_waves, self.plot_reference_on+2*ref_std, pen='b')
            self.ref_error_region.setCurves(rcurve1, rcurve2)
            self.ui.d_probe_ref_graph.addItem(self.ref_error_region)
        return
        
    def d_ls_plot(self):
        self.ui.d_last_shot_graph.plotItem.plot(self.plot_waves, self.plot_ls, pen='b', clear=True)
        return
        
    def message_block(self):
        msg = QtGui.QMessageBox()
        msg.setIcon(QtGui.QMessageBox.Information)
        msg.setText("Block Probe and Reference")
        msg.setInformativeText("Just press once (be patient)")
        msg.setStandardButtons(QtGui.QMessageBox.Ok)
        retval = msg.exec_()
        return retval
        
    def message_unblock(self):
        msg = QtGui.QMessageBox()
        msg.setIcon(QtGui.QMessageBox.Information)
        msg.setText("Unblock Probe and Reference")
        msg.setInformativeText("Just press once (be patient)")
        msg.setStandardButtons(QtGui.QMessageBox.Ok)
        retval = msg.exec_()
        return retval
        
    def message_time_points(self):
        msg = QtGui.QMessageBox()
        msg.setIcon(QtGui.QMessageBox.Information)
        msg.setText("One or more time point exceeds limit!")
        msg.setInformativeText("Don't be greedy...")
        msg.setStandardButtons(QtGui.QMessageBox.Ok)
        retval = msg.exec_()
        return retval
        
    def message_error_saving(self):
        msg = QtGui.QMessageBox()
        msg.setIcon(QtGui.QMessageBox.Information)
        msg.setText("Error Saving File")
        msg.setStandardButtons(QtGui.QMessageBox.Ok)
        retval = msg.exec_()
        return retval
    
    def message_unsafe_exit(self):
        msg = QtGui.QMessageBox()
        msg.setIcon(QtGui.QMessageBox.Information)
        msg.setText('cannot close application')
        msg.setInformativeText('stop acquisition and disconnect from hardware')
        msg.setStandardButtons(QtGui.QMessageBox.Ok)
        retval = msg.exec_()
        return retval
        
    def running(self):
        self.idle = False
        self.ui.hardware_tab.setEnabled(False)
        self.ui.a_run_btn.setDisabled(True)
        self.ui.d_run_btn.setDisabled(True)
        self.ui.a_file_box.setDisabled(True)
        self.ui.a_times_box.setDisabled(True)
        self.ui.a_acquire_box.setDisabled(True)
        self.ui.a_calib_box.setDisabled(True)
        self.ui.a_cutoff_box.setDisabled(True)
        if self.diagnostics_on is False:
            self.ui.d_times_box.setDisabled(True)
            self.ui.d_other_box.setDisabled(True)
            self.ui.d_calib_box.setDisabled(True)
            self.ui.d_cutoff_box.setDisabled(True)
            self.ui.d_refmanip_box.setDisabled(True)
            self.ui.d_acquire_box.setDisabled(True)
        return
            
    def idling(self):
        self.idle = True
        self.ui.hardware_tab.setEnabled(True)
        self.ui.a_run_btn.setDisabled(False)
        self.ui.d_run_btn.setDisabled(False)
        self.ui.a_file_box.setDisabled(False)
        self.ui.a_times_box.setDisabled(False)
        self.ui.a_acquire_box.setDisabled(False)
        self.ui.a_calib_box.setDisabled(False)
        self.ui.a_cutoff_box.setDisabled(False)
        self.ui.d_refmanip_box.setDisabled(False)
        self.ui.d_acquire_box.setDisabled(False)
        self.ui.d_other_box.setDisabled(False)
        self.ui.d_calib_box.setDisabled(False)
        self.ui.d_cutoff_box.setDisabled(False)
        self.ui.d_times_box.setDisabled(False)
        return
       
    def motor_running(self):
        self.ui.hardware_tab.setEnabled(False)
        self.ui.coosc_run_button.setEnabled(False)
        self.ui.delay_spin.setEnabled(False)
        self.ui.coosc_m1_target1.setEnabled(False)
        self.ui.coosc_m1_target2.setEnabled(False)
        self.ui.coosc_m1_zero.setEnabled(False)
        self.ui.coosc_m2_target1.setEnabled(False)
        self.ui.coosc_m2_target2.setEnabled(False)
        self.ui.coosc_m2_zero.setEnabled(False)
        self.ui.motor_1_index_spin.setEnabled(False)
        self.ui.motor_2_index_spin.setEnabled(False)
        self.ui.motor_move_index_spin.setEnabled(False)
        self.ui.move_run_button.setEnabled(False)
        self.ui.move_target_spin.setEnabled(False)
        self.ui.param_accel_spin.setEnabled(False)
        self.ui.param_jerk_spin.setEnabled(False)
        self.ui.param_motor_index.setEnabled(False)
        self.ui.param_velocity_spin.setEnabled(False)
        
        self.ui.coosc_stop_button.setEnabled(True)
        self.ui.move_stop_button.setEnabled(True)
        
    def motor_idling(self):
        self.ui.hardware_tab.setEnabled(True)
        self.ui.coosc_run_button.setEnabled(True)
        self.ui.delay_spin.setEnabled(True)
        self.ui.coosc_m1_target1.setEnabled(True)
        self.ui.coosc_m1_target2.setEnabled(True)
        self.ui.coosc_m1_zero.setEnabled(True)
        self.ui.coosc_m2_target1.setEnabled(True)
        self.ui.coosc_m2_target2.setEnabled(True)
        self.ui.coosc_m2_zero.setEnabled(True)
        self.ui.motor_1_index_spin.setEnabled(True)
        self.ui.motor_2_index_spin.setEnabled(True)
        self.ui.motor_move_index_spin.setEnabled(True)
        self.ui.move_run_button.setEnabled(True)
        self.ui.move_target_spin.setEnabled(True)
        self.ui.param_accel_spin.setEnabled(True)
        self.ui.param_jerk_spin.setEnabled(True)
        self.ui.param_motor_index.setEnabled(True)
        self.ui.param_velocity_spin.setEnabled(True)
        
        self.ui.coosc_stop_button.setEnabled(False)
        self.ui.move_stop_button.setEnabled(False)
        
    def update_progress_bars(self):
        self.ui.a_sweep_progress_bar.setValue(self.timestep+1)
        self.ui.a_measurement_progress_bar.setValue((len(self.times)*self.current_sweep.sweep_index)+self.timestep+1)
        return
        
    def acquire(self):
        self.append_history('Acquiring '+str(self.num_shots)+' shots')
        self.acquisition.start_acquire.emit()  # connects to the Acquire signal in the camera class, which results in a signal data_ready being emitted containing the data from probe and reference. This signal connects to post_acquire method, which loops back to acquire
        return
    
    @pyqtSlot(np.ndarray, np.ndarray, int, int)    
    def post_acquire(self, probe, reference, first_pixel, num_pixels):
        try:
            self.current_data.update(probe,
                                     reference,
                                     first_pixel,
                                     num_pixels)
        except:
             self.current_data = DataProcessing(probe,
                                                reference,
                                                first_pixel,
                                                num_pixels)
        if self.ui.d_use_linear_corr.isChecked():
            try:
                self.current_data.linear_pixel_correlation(self.linear_corr)
            except:
                self.append_history('Error using linear pixel correction, line~1075')
        self.high_trig_std = self.current_data.separate_on_off(self.threshold, self.tau_flip_request)
        if self.ui.a_test_run_btn.isChecked() is False:
            self.current_data.sub_bgd(self.bgd)
        if self.ui.d_use_ref_manip.isChecked() is True:
            self.current_data.manipulate_reference(self.refman)
        self.current_data.average_shots()
        if self.ui.d_use_reference.isChecked() is True:
            self.current_data.correct_probe_with_reference()
            self.current_data.average_refd_shots()
            self.high_dtt = self.current_data.calcuate_dtt(use_reference=True, cutoff=self.cutoff, use_avg_off_shots=self.ui.d_use_avg_off_shots.isChecked(), max_dtt=np.abs(self.ui.d_max_dtt.value()))
            self.current_data.calculate_dtt_error(use_reference=True ,use_avg_off_shots=self.ui.d_use_avg_off_shots.isChecked())
        else:
            self.high_dtt = self.current_data.calcuate_dtt(use_reference=False,cutoff=self.cutoff, use_avg_off_shots=self.ui.d_use_avg_off_shots.isChecked(), max_dtt=np.abs(self.ui.d_max_dtt.value()))
            self.current_data.calculate_dtt_error(use_reference=False, use_avg_off_shots=self.ui.d_use_avg_off_shots.isChecked())
        if (self.high_trig_std is False) and (self.high_dtt is False):
            self.current_sweep.add_current_data(self.current_data.dtt, time_point=self.timestep)
            self.create_plot_waves_and_times()
            if self.ui.acquisition_tab.isVisible() is True:
                self.ls_plot()
                self.top_plot()
                self.kin_plot()
                self.spec_plot()
            if self.ui.diagnostics_tab.isVisible() is True:
                self.d_ls_plot()
                self.d_error_plot()
                self.d_trigger_plot()
                self.d_probe_ref_plot()
            if self.stop_request is True:
                self.finish()
            if self.timestep == len(self.times)-1:
                self.post_sweep()
            else:
                self.timestep = self.timestep+1
                self.time = self.times[self.timestep]
                self.ui.a_time_display.display(self.time)
                self.update_progress_bars()
                self.move(self.time)
                self.acquire()
        else:
            if self.stop_request is True:
                self.finish()
            self.append_history('retaking point')
            self.acquire()
        return
   
    def acquire_bgd(self):
        self.append_history('Acquiring '+str(self.num_shots*self.dcshotfactor)+' shots')
        self.acquisition.start_acquire.emit()
        return
    
    @pyqtSlot(np.ndarray, np.ndarray, int, int)    
    def post_acquire_bgd(self, probe, reference, first_pixel, num_pixels):      
        self.message_unblock()
        self.bgd = DataProcessing(probe,
                                  reference,
                                  first_pixel,
                                  num_pixels)
        if self.ui.d_use_linear_corr.isChecked():
            try:
                self.bgd.linear_pixel_correlation(self.linear_corr)
            except:
                self.append_history('Error using linear pixel correction, line~1137')
        self.bgd.separate_on_off(self.threshold)
        self.bgd.average_shots() 
        self.run()          
        return    
    
    def exec_run_btn(self):
        if self.ui.a_test_run_btn.isChecked() is True:
            self.append_history('Launching Test Run!')
        else:
            self.append_history('Launching Run!')
        
        self.stop_request = False
        self.diagnostics_on = False
        self.running()
        self.update_num_shots()
        
        success = self.delay.check_times(self.times)
        if success is False:
            self.message_time_points()
            self.idling()
            return
        
        self.finished_acquisition = False
        self.set_waves_and_times_axes()
        try:
            self.ui.a_kinetic_graph.removeItem(self.time_marker)
        except:
            pass
        self.add_time_marker()
        try:
            self.ui.a_spectra_graph.removeItem(self.wavelength_marker)
        except:
            pass
        self.add_wavelength_marker()
        
        self.acquire_thread = QtCore.QThread()
        self.acquire_thread.start()
        
        self.acquisition = Acquisition(self.camera, number_of_scans=self.num_shots*self.dcshotfactor)
        
        self.acquisition.moveToThread(self.acquire_thread)
        self.acquisition.start_acquire.connect(self.acquisition.acquire)
        self.acquisition.data_ready.connect(self.post_acquire_bgd)
        
        if self.ui.a_test_run_btn.isChecked() is False:
            self.message_block()
            self.append_history('Taking Background')
            self.acquire_bgd()
        else:
            self.run()
        return
            
    def run(self):
        self.update_metadata()
        self.current_sweep = SweepProcessing(self.times,self.num_pixels,self.filepath,self.metadata)    
        
        self.acquisition.update_number_of_scans(self.num_shots)
        self.acquisition.data_ready.disconnect(self.post_acquire_bgd)
        self.acquisition.data_ready.connect(self.post_acquire)
        
        self.append_history('Starting Sweep '+str(self.current_sweep.sweep_index))
        self.ui.a_sweep_display.display(self.current_sweep.sweep_index+1)
        self.ui.a_sweep_progress_bar.setMaximum(len(self.times))
        self.ui.a_measurement_progress_bar.setMaximum(len(self.times)*self.num_sweeps)
        self.start_sweep()
        
    def finish(self):
        self.acquire_thread.quit()
        self.idling()
        self.finished_acquisition = True
        if not self.stop_request:
            self.create_plot_waves_and_times()
            if self.ui.acquisition_tab.isVisible() is True:
                self.ls_plot()
                self.top_plot()
                self.kin_plot()
                self.spec_plot()
            if self.ui.diagnostics_tab.isVisible() is True:
                self.d_ls_plot()
                self.d_error_plot()
                self.d_trigger_plot()
                self.d_probe_ref_plot()
        return
        
    def start_sweep(self):
        self.timestep = 0
        self.time = self.times[self.timestep]
        self.ui.a_time_display.display(self.time)
        self.update_progress_bars()
        self.move(self.time)
        self.acquire()
        return
        
    def post_sweep(self):
        if self.ui.a_test_run_btn.isChecked() is False:
            self.append_history('Saving Sweep '+str(self.current_sweep.sweep_index))
            try:
                self.current_sweep.save_current_data(self.waves)
                self.current_sweep.save_avg_data(self.waves)
                self.current_sweep.save_metadata_each_sweep(self.current_data.probe_on,
                                                            self.current_data.reference_on,
                                                            self.current_data.probe_shot_error)
            except:
                self.message_error_saving()
        
        self.current_sweep.next_sweep()
        
        if self.current_sweep.sweep_index == self.num_sweeps:
            self.finish()
        else:
            self.append_history('Starting Sweep '+str(self.current_sweep.sweep_index))
            self.ui.a_sweep_display.display(self.current_sweep.sweep_index+1)
            self.start_sweep()
        return
        
    def exec_stop_btn(self):
        self.append_history('Stopped')
        self.stop_request=True
        return
        
    def move(self, new_time): 
        self.append_history('Moving to: '+str(new_time))
        self.tau_flip_request = self.delay.move_to(new_time)
        return
    
    def d_jog_earlier(self):
        newtime = self.d_time-self.d_jogstep
        self.move(newtime)
        self.ui.d_time.setValue(newtime)
        return
        
    def d_jog_later(self):
        newtime = self.d_time+self.d_jogstep
        self.move(newtime)
        self.ui.d_time.setValue(newtime)
        return
    
    def exec_d_set_current_btn(self):
        if self.delay_type == 2:  # short stage
            self.ui.d_shortstage_t0.setValue(self.shortstage_t0-self.d_time)
        elif self.delay_type == 1:  # long stage
            self.ui.d_longstage_t0.setValue(self.longstage_t0-self.d_time)
        else:  # pink laser
            self.ui.d_pinklaser_t0.setValue(self.pinklaser_t0-self.d_time)
        self.ui.d_time.setValue(0)
        self.update_d_time()
        self.move(self.d_time)
        return
   
    def d_acquire(self):
        self.append_history('Acquiring '+str(self.num_shots)+' shots')
        self.acquisition.start_acquire.emit()
        return
        
    @pyqtSlot(np.ndarray, np.ndarray, int, int)
    def d_post_acquire(self, probe, reference, first_pixel, num_pixels):
        try:
            self.current_data.update(probe,
                                     reference,
                                     first_pixel,
                                     num_pixels)
        except:
             self.current_data = DataProcessing(probe,
                                                reference,
                                                first_pixel,
                                                num_pixels)
        if self.ui.d_use_linear_corr.isChecked():
            try:
                self.current_data.linear_pixel_correlation(self.linear_corr)
            except:
                self.append_history('Error using linear pixel correction, line~1308')
        self.current_data.separate_on_off(self.threshold,self.tau_flip_request)
        if self.ui.a_test_run_btn.isChecked() is False:
            self.current_data.sub_bgd(self.bgd)
        if self.ui.d_use_ref_manip.isChecked() is True:
            self.current_data.manipulate_reference(self.refman)
        self.current_data.average_shots()
        if self.ui.d_use_reference.isChecked() is True:
            self.current_data.correct_probe_with_reference()
            self.current_data.average_refd_shots()
            self.current_data.calcuate_dtt(use_reference=True,cutoff=self.cutoff,use_avg_off_shots=self.ui.d_use_avg_off_shots.isChecked())
            self.current_data.calculate_dtt_error(use_reference=True,use_avg_off_shots=self.ui.d_use_avg_off_shots.isChecked())
        else:
            self.current_data.calcuate_dtt(use_reference=False,cutoff=self.cutoff,use_avg_off_shots=self.ui.d_use_avg_off_shots.isChecked())
            self.current_data.calculate_dtt_error(use_reference=False,use_avg_off_shots=self.ui.d_use_avg_off_shots.isChecked())

        self.create_plot_waves_and_times()
        self.d_ls_plot()
        self.d_error_plot()
        self.d_trigger_plot()
        self.d_probe_ref_plot()
        
        if self.stop_request is True:
            self.d_finish()
        else:
            self.d_acquire()
        return
        
    def d_acquire_bgd(self):
        self.append_history('Acquiring '+str(self.num_shots*self.dcshotfactor)+' shots')
        self.acquisition.start_acquire.emit()
        return
        
    @pyqtSlot(np.ndarray, np.ndarray, int, int)
    def d_post_acquire_bgd(self, probe, reference, first_pixel, num_pixels):      
        self.message_unblock()
        self.bgd = DataProcessing(probe,
                                  reference,
                                  first_pixel,
                                  num_pixels)
        if self.ui.d_use_linear_corr.isChecked():
            try:
                self.bgd.linear_pixel_correlation(self.linear_corr)
            except:
                self.append_history('Error using linear pixel correction, line~1352')
        self.bgd.separate_on_off(self.threshold)
        self.bgd.average_shots()
        self.d_run()          
        return
        
    def exec_d_run_btn(self):
        self.append_history('Launching Diagnostics!')
        self.stop_request = False
        self.diagnostics_on = True
        self.tau_flip_request = False
        self.running()
        self.ui.a_test_run_btn.setChecked(0)
        self.update_d_num_shots()
        
        success = self.delay.check_time(self.d_time)
        if success is False:
            self.message_time_points()
            self.idling()
            return
        
        self.acquire_thread = QtCore.QThread()
        self.acquire_thread.start()
        
        self.acquisition = Acquisition(self.camera, number_of_scans=self.num_shots*self.dcshotfactor)

        self.acquisition.moveToThread(self.acquire_thread)
        self.acquisition.start_acquire.connect(self.acquisition.acquire)
        self.acquisition.data_ready.connect(self.d_post_acquire_bgd)
        
        self.message_block()
        self.append_history('Taking Background')
        self.d_acquire_bgd()

    def d_run(self):
        self.move(self.d_time)
        self.acquisition.update_number_of_scans(self.num_shots)
        self.acquisition.data_ready.disconnect(self.d_post_acquire_bgd)
        self.acquisition.data_ready.connect(self.d_post_acquire)
        self.d_acquire()
        
    def d_finish(self):  
        self.acquire_thread.quit()
        self.idling()
        return
        
    def exec_d_stop_btn(self):
        self.stop_request = True
        return
        
    def exec_d_move_to_time(self):
        self.move(self.d_time)
        return
        
    def update_COMport(self):
        self.motor_comport = self.ui.h_motorCOM_dd.currentText()
        return
    
    def exec_h_motor_connect_btn(self):
        self.update_COMport()
        self.ui.h_motor_connect_btn.setEnabled(False)
        self.ui.h_motorCOM_dd.setEnabled(False)
        self.h_update_motor_status('initialising... please wait')
        # sleep(0.2)
        ## connect to motors
        
        self.motor_controller = mm.Controller(instrument=self.motor_comport, zeroarray=(4.5, 5.5, 0, 0), parent=self)
        
        self.motor_thread = QtCore.QThread()
        self.motor_thread.start()
        
        self.motor_controller.moveToThread(self.motor_thread)
        
        self.motor_controller.discover()
        self.motor_controller.get_motor_parameters()
        self.pack_motor_tab_values()
        
        ## extract all the values to the motor tabs
        self.h_update_motor_status('ready')
        self.ui.h_motor_disconnect_btn.setEnabled(True)
        self.motor_connected = True
        self.safe_to_exit = False
        self.ui.motor_tab.setEnabled(True)
        return
        
    def exec_h_motor_disconnect_btn(self):
        self.ui.motor_tab.setEnabled(False)
        self.ui.h_motor_disconnect_btn.setEnabled(False)
        self.motor_controller.close()
        self.motor_thread.quit()
        self.h_update_motor_status('ready to connect')
        self.ui.h_motor_connect_btn.setEnabled(True)
        self.ui.h_motorCOM_dd.setEnabled(True)
        self.motor_connected = False
        if not self.delay_connected and not self.camera_connected:
            self.safe_to_exit = True
        self.ui.motor_tab.setEnabled(False)
        return
        
    def h_update_motor_status(self, message):
        self.ui.h_motor_status.setText(message)
        self.ui.h_motor_status.repaint()
        return
        
    def pack_motor_tab_values(self):
        # add motor indices to drop down menus
        for i in range(0, 4):
            if self.motor_controller.motors[i]:
                self.ui.motor_1_index_spin.addItem(str(i+1))
                self.ui.motor_2_index_spin.addItem(str(i+1))
                self.ui.motor_move_index_spin.addItem(str(i+1))
                self.ui.param_motor_index.addItem(str(i+1))
        if self.ui.motor_1_index_spin.currentIndex() == self.ui.motor_2_index_spin.currentIndex():
            self.ui.motor_2_index_spin.setCurrentIndex(self.ui.motor_2_index_spin.currentIndex()+1%self.ui.motor_2_index_spin.count())
        # when it updates, pack all the right values into the other widgets, and remove itself from the other coosc drop down in the case of the coosc one
        # load from last values: if the saved value is in the list of values, set the value of the box to it. otherwise don't0
        if self.last_instance_values['motor coosc index 1'] in self.comport_list:
            self.motor_1_index_spin.setCurrentIndex(self.motor_1_index_spin.findText(self.last_instance_values['motor coosc index 1']))
        if self.last_instance_values['motor coosc index 2'] in self.comport_list:
            self.motor_2_index_spin.setCurrentIndex(self.motor_2_index_spin.findText(self.last_instance_values['motor coosc index 2']))
        if self.last_instance_values['motor coosc index 1'] in self.comport_list:
            self.motor_move_index_spin.setCurrentIndex(self.motor_move_index_spin.findText(self.last_instance_values['motor move index']))
        self.update_motor_1_coosc_index()
        self.update_motor_2_coosc_index()
        self.update_move_motor_index()
        self.update_param_motor_index()
        # the rest of the update stuff
        self.update_motor_delay()
        self.update_m1_coosc_target1()
        self.update_m1_coosc_target2()
        self.update_m2_coosc_target1()
        self.update_m2_coosc_target2()
        self.update_m1_coosc_zero()
        self.update_m2_coosc_zero()
        self.update_move_target()
        return
        
    
    def exec_coosc_run_button(self):
        self.append_motor_log("Running cooscillation")
        self.motor_controller.move_stop_command = False
        
        self.coosc_thread = QtCore.QThread()
        self.coosc_thread.start()
        
        self.coosc_handler = mm.motorHandler(self.motor_controller, self)
        self.coosc_handler.moveToThread(self.coosc_thread)
        
        self.coosc_handler.do_motor_cooscillate.connect(self.coosc_handler.co_oscillate)
        self.motor_controller.update_coosc_m1_pos_lcd.connect(self.update_coosc_motor1_pos)
        self.motor_controller.update_coosc_m2_pos_lcd.connect(self.update_coosc_motor2_pos)
        self.motor_controller.update_coosc_time_lcd.connect(self.update_coosc_motor_time)
        self.motor_controller.stopped_cooscillation.connect(self.on_cooscillation_finish)
        
        self.motor_running()
        self.coosc_handler.do_motor_cooscillate.emit(int(self.ui.motor_1_index_spin.currentText()), int(self.ui.motor_2_index_spin.currentText()), self.motor_1_coosc_target1, self.motor_1_coosc_target2, self.motor_2_coosc_target1, self.motor_2_coosc_target2, self.motor_1_zero, self.motor_2_zero, self.motor_delay)
        return
                    
    def exec_coosc_stop_button(self):
        self.motor_controller.move_stop_command = True
        self.append_motor_log("Stopping cooscillation")
        return
    
    @pyqtSlot(float)
    def update_coosc_motor1_pos(self, pos):
        self.ui.coosc_m1_current_pos.display(pos)
        self.ui.coosc_m1_current_pos.repaint()
        return
        
    @pyqtSlot(float)
    def update_coosc_motor2_pos(self, pos):
        self.ui.coosc_m2_current_pos.display(pos)
        self.ui.coosc_m2_current_pos.repaint()
        return
        
    @pyqtSlot(float)
    def update_coosc_motor_time(self, t):
        self.ui.coosc_time_readout.display(t)
        self.ui.coosc_time_readout.repaint()
        return
        
    @pyqtSlot()
    def on_cooscillation_finish(self):
        self.motor_controller.zero(zeroarray=(self.motor_1_zero, self.motor_2_zero))
        self.motor_idling()
        self.coosc_thread.quit()
        self.motor_controller.update_coosc_m1_pos_lcd.disconnect(self.update_coosc_motor1_pos)
        self.motor_controller.update_coosc_m2_pos_lcd.disconnect(self.update_coosc_motor2_pos)
        self.motor_controller.update_coosc_time_lcd.disconnect(self.update_coosc_motor_time)
        self.motor_controller.stopped_cooscillation.disconnect(self.on_cooscillation_finish)
        
        self.ui.coosc_m1_current_pos.display(self.motor_controller.positions[int(self.ui.motor_1_index_spin.currentText())])
        self.ui.coosc_m2_current_pos.display(self.motor_controller.positions[int(self.ui.motor_2_index_spin.currentText())])
        self.ui.move_current_pos_readout.display(self.motor_controller.positions[int(self.ui.motor_move_index_spin.currentText())])
        return
    
    def update_motor_delay(self):
        self.motor_delay = self.ui.delay_spin.value()
        self.append_motor_log("Motor delay changed: {}s".format(self.motor_delay))
        return
    
    def update_motor_1_coosc_index(self):
        if self.motor_connected:
            self.motor_controller.get_motor_parameters()
            index = int(self.ui.motor_1_index_spin.currentText())-1
            self.ui.coosc_m1_target1.setRange(self.motor_controller.software_limits[index][0], self.motor_controller.software_limits[index][1])
            self.ui.coosc_m1_target2.setRange(self.motor_controller.software_limits[index][0], self.motor_controller.software_limits[index][1])
            self.ui.coosc_m1_zero.setRange(self.motor_controller.software_limits[index][0], self.motor_controller.software_limits[index][1])
            self.ui.coosc_m1_current_pos.display(self.motor_controller.positions[index])
            if self.ui.motor_1_index_spin.currentIndex() == self.ui.motor_2_index_spin.currentIndex():
                self.ui.motor_2_index_spin.setCurrentIndex((self.ui.motor_2_index_spin.currentIndex()+1)%self.ui.motor_2_index_spin.count())
                prev_targ_zero = [self.ui.coosc_m1_target1.value(), self.ui.coosc_m1_target2.value(), self.ui.coosc_m1_zero.value()]
                self.ui.coosc_m1_target1.setValue(self.ui.coosc_m2_target1.value())
                self.ui.coosc_m1_target2.setValue(self.ui.coosc_m2_target2.value())
                self.ui.coosc_m1_zero.setValue(self.ui.coosc_m2_zero.value())
                self.ui.coosc_m2_target1.setValue(prev_targ_zero[0])
                self.ui.coosc_m2_target2.setValue(prev_targ_zero[1])
                self.ui.coosc_m2_zero.setValue(prev_targ_zero[2])
        return
    
    def update_motor_2_coosc_index(self):
        if self.motor_connected:
            self.motor_controller.get_motor_parameters()
            index = int(self.ui.motor_1_index_spin.currentText())-1
            self.ui.coosc_m1_target1.setRange(self.motor_controller.software_limits[index][0], self.motor_controller.software_limits[index][1])
            self.ui.coosc_m1_target2.setRange(self.motor_controller.software_limits[index][0], self.motor_controller.software_limits[index][1])
            self.ui.coosc_m1_zero.setRange(self.motor_controller.software_limits[index][0], self.motor_controller.software_limits[index][1])
            self.ui.coosc_m2_current_pos.display(self.motor_controller.positions[index])
            if self.ui.motor_1_index_spin.currentIndex() == self.ui.motor_2_index_spin.currentIndex():
                self.ui.motor_1_index_spin.setCurrentIndex((self.ui.motor_1_index_spin.currentIndex()+1)%self.ui.motor_1_index_spin.count())
                prev_targ_zero = [self.ui.coosc_m2_target1.value(), self.ui.coosc_m2_target2.value(), self.ui.coosc_m2_zero.value()]
                self.ui.coosc_m2_target1.setValue(self.ui.coosc_m1_target1.value())
                self.ui.coosc_m2_target2.setValue(self.ui.coosc_m1_target2.value())
                self.ui.coosc_m2_zero.setValue(self.ui.coosc_m1_zero.value())
                self.ui.coosc_m1_target1.setValue(prev_targ_zero[0])
                self.ui.coosc_m1_target2.setValue(prev_targ_zero[1])
                self.ui.coosc_m1_zero.setValue(prev_targ_zero[2])
        return
    
    def update_m1_coosc_target1(self):
        self.motor_1_coosc_target1 = self.ui.coosc_m1_target1.value()
        self.append_motor_log("Cooscillation motor 1 target 1 changed: {}".format(self.motor_1_coosc_target1))
        return
       
    def update_m1_coosc_target2(self):
        self.motor_1_coosc_target2 = self.ui.coosc_m1_target2.value()
        self.append_motor_log("Cooscillation motor 1 target 2 changed: {}".format(self.motor_1_coosc_target2))
        return
       
    def update_m1_coosc_zero(self):
        self.motor_1_zero = self.ui.coosc_m1_zero.value()
        self.append_motor_log("Cooscillation motor 1 zero changed: {}".format(self.motor_1_zero))
        return
        
    def update_m2_coosc_target1(self):
        self.motor_2_coosc_target1 = self.ui.coosc_m2_target1.value()
        self.append_motor_log("Cooscillation motor 2 target 1 changed: {}".format(self.motor_2_coosc_target1))
        return
        
    def update_m2_coosc_target2(self):
        self.motor_2_coosc_target2 = self.ui.coosc_m2_target2.value()
        self.append_motor_log("Cooscillation motor 2 target 2 changed: {}".format(self.motor_2_coosc_target2))
        return
        
    def update_m2_coosc_zero(self):
        self.motor_2_zero = self.ui.coosc_m2_zero.value()
        self.append_motor_log("Cooscillation motor 2 zero changed: {}".format(self.motor_2_zero))
        return
        
    def update_move_motor_index(self):
        self.motor_controller.get_motor_parameters()
        index = int(self.ui.motor_move_index_spin.currentText())-1
        self.ui.move_target_spin.setRange(self.motor_controller.software_limits[index][0], self.motor_controller.software_limits[index][1])
        self.ui.move_current_pos_readout.display(self.motor_controller.positions[index])
        return

    def exec_move_run_button(self):
        self.append_motor_log("Starting movement")
        self.motor_controller.move_stop_command = False
        
        self.move_thread = QtCore.QThread()
        self.move_thread.start()
        
        self.move_handler = mm.motorHandler(self.motor_controller, self)
        self.move_handler.moveToThread(self.move_thread)
        
        self.move_handler.do_motor_move.connect(self.move_handler.move)
        self.motor_controller.update_move_pos_lcd.connect(self.update_moving_motor_pos)
        self.motor_controller.update_move_time_lcd.connect(self.update_moving_motor_time)
        self.motor_controller.stopped_move.connect(self.on_motion_finish)
        
        # connect the signals to relevant slots
        self.motor_running()
        self.move_handler.do_motor_move.emit(int(self.ui.motor_move_index_spin.currentText()), self.move_target)
        # disable ALL the move stuff
        # I also need to set certain things to be disabled when the motion is started and enable them when the motion finishes, either naturally or by command.
        return
    
    def exec_move_stop_button(self):
        self.motor_controller.move_stop_command = True
        self.append_motor_log("Stopping movement")
        return
    
    @pyqtSlot(float)
    def update_moving_motor_pos(self, pos):
        self.ui.move_current_pos_readout.display(pos)
        self.ui.move_current_pos_readout.repaint()
        return
        
    @pyqtSlot(float)
    def update_moving_motor_time(self, t):
        self.ui.move_current_time_readout.display(t)
        self.ui.move_current_time_readout.repaint()
        return
    
    @pyqtSlot()
    def on_motion_finish(self):
        # re-enable ALL the move stuff
        # unbind the connections
        self.motor_idling()
        self.move_thread.quit()
        self.motor_controller.update_move_pos_lcd.disconnect(self.update_moving_motor_pos)
        self.motor_controller.update_move_time_lcd.disconnect(self.update_moving_motor_time)
        self.motor_controller.stopped_move.disconnect(self.on_motion_finish)
        self.ui.coosc_m1_current_pos.display(self.motor_controller.positions[int(self.ui.motor_1_index_spin.currentText())])
        self.ui.coosc_m2_current_pos.display(self.motor_controller.positions[int(self.ui.motor_2_index_spin.currentText())])
        self.ui.move_current_pos_readout.display(self.motor_controller.positions[int(self.ui.motor_move_index_spin.currentText())])
        return
        
    def update_move_target(self):
        self.move_target = self.ui.move_target_spin.value()
        self.append_motor_log("Motion target changed: {}".format(self.move_target))
        return
    
    #also look up the limits of these values.
    def update_motor_acceleration(self):
        self.motor_controller.setAcceleration(int(self.ui.param_motor_index.currentText()), float(self.ui.param_accel_spin.value()))
        self.append_motor_log("Motor acceleration changed")
        return
    
    def update_motor_jerk(self):
        self.motor_controller.setJerk(int(self.ui.param_motor_index.currentText()), float(self.ui.param_jerk_spin.value()))
        self.append_motor_log("Motor jerk changed")
        return

    def update_motor_velocity(self):
        self.motor_controller.setVelocity(int(self.ui.param_motor_index.currentText()), float(self.ui.param_velocity_spin.value()))
        self.append_motor_log("Motor velocity changed")
        return

    def update_param_motor_index(self):
        index = int(self.ui.param_motor_index.currentText())-1
        self.ui.param_accel_spin.setValue(self.motor_controller.accelerations[index])
        self.ui.param_jerk_spin.setValue(self.motor_controller.jerks[index])
        self.ui.param_velocity_spin.setValue(self.motor_controller.velocities[index])
        return
        
    def append_motor_log(self, message):
        self.ui.motor_log.appendPlainText(message)
        self.ui.motor_log.repaint()
        return
        
def main():
    
    # create application
    QtGui.QApplication.setStyle('Fusion')
    app = QtGui.QApplication(sys.argv)
    
    # load the parameter values from last time and launch GUI
    last_instance_filename = 'last_instance_values.txt'
    last_instance_values = pd.read_csv(last_instance_filename, sep=':', header=None, index_col=0).squeeze('columns')
    
    ex = Application(last_instance_filename, last_instance_values=last_instance_values, preloaded=True)
    
    ex.show()
    ex.create_plots()
    
    # kill application
    sys.exit(app.exec_())
   

if __name__ == '__main__':
    main()
