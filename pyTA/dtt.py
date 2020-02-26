###############################################################################

### SUBTRACT BACKGROUND IS CURRENTLY DISABLED FOR TESTING PUROPOSES ###########

###############################################################################


'''this class handles all the data processing once the probe and reference arrays
   are acquired. this class is instantiated within visTA.py'''
import datetime
import numpy as np

class taDataProcessing:
    '''class for processing ta data'''
    def __init__(self,probe_array,reference_array,first_pixel,num_pixels):
        '''select parts of array which contain the camera data and thus ignoring 
           dummy pixels. A copy of the entire probe array is saved as this will have
           the information from the trigger (photodiode/chopper wheel)'''
        self.untrimmed_probe_array = np.array(probe_array,dtype=int)
        self.probe_array = np.array(probe_array,dtype=float)[:,first_pixel:num_pixels+first_pixel]
        self.reference_array = np.array(reference_array,dtype=float)[:,first_pixel:num_pixels+first_pixel]
        self.raw_probe_array = np.array(probe_array,dtype=float)[:,first_pixel:num_pixels+first_pixel]
        self.raw_reference_array = np.array(reference_array,dtype=float)[:,first_pixel:num_pixels+first_pixel]
        self.first_pixel = first_pixel
        self.num_pixels = num_pixels
        
    def update(self,probe_array,reference_array,first_pixel,num_pixels):
        '''select parts of array which contain the camera data and thus ignoring 
           dummy pixels. A copy of the entire probe array is saved as this will have
           the information from the trigger (photodiode/chopper wheel)'''
        self.untrimmed_probe_array = probe_array
        self.probe_array = probe_array[:,first_pixel:num_pixels+first_pixel]
        self.reference_array = reference_array[:,first_pixel:num_pixels+first_pixel]
        self.first_pixel = first_pixel
        self.num_pixels = num_pixels
        
    def set_linear_pixel_correlation(self):
        '''Mathematical correction for how IR camera reads out even and odd pixels
        differently.  Should only need to be reset once each time the program loads'''
        pr_corr = self.raw_probe_array.mean(axis=0)
        ref_corr = self.raw_reference_array.mean(axis=0)
        pr_corr[::2] = pr_corr[::2]/pr_corr[1::2]
        ref_corr[::2] = ref_corr[::2]/ref_corr[1::2]
        pr_corr[1::2] = pr_corr[1::2]/pr_corr[1::2]
        ref_corr[1::2] = ref_corr[1::2]/ref_corr[1::2]
        return pr_corr, ref_corr
        
    def linear_pixel_correlation(self,linear_corr):
        self.probe_array = self.probe_array/linear_corr[0]
        self.reference_array = self.reference_array/linear_corr[1]
        return
        
    def separate_on_off(self,threshold,tau_flip_request=False):
        '''separates on and off shots in the probe and reference arrays, note that
           when the tau flip is passed as true (long time shots where the delay was 
           offset by 1ms) the trigger is rolled over by one value to compensate. 
           Should get rid of tau flip'''
        high_std = False
        pixel = threshold[0]
        thresh_value = threshold[1]
        self.trigger = []
        for shot in self.untrimmed_probe_array:
            self.trigger.append(shot[pixel])
        self.trigger = np.array(self.trigger)
        if np.abs(self.trigger-self.trigger.mean()).std() > 20:
            print('high std '+str(datetime.datetime.now()))
            high_std = True
        if tau_flip_request is True:
            self.trigger = np.roll(self.trigger,1)
        if self.untrimmed_probe_array[0,pixel] >= thresh_value:
            self.probe_on_array = self.probe_array[::2,:]
            self.probe_off_array = self.probe_array[1::2,:]
            self.reference_on_array = self.reference_array[::2,:]
            self.reference_off_array = self.reference_array[1::2,:]
        else:
            self.probe_on_array = self.probe_array[1::2,:]
            self.probe_off_array = self.probe_array[::2,:]
            self.reference_on_array = self.reference_array[1::2,:]
            self.reference_off_array = self.reference_array[::2,:]
        return high_std
        
    def average_shots(self):
        '''simple enough - averages shots'''
        self.probe_on = self.probe_on_array.mean(axis=0)
        self.probe_off = self.probe_off_array.mean(axis=0)
        self.reference_on = self.reference_on_array.mean(axis=0)
        self.reference_off = self.reference_off_array.mean(axis=0)
        return
        
    def sub_bgd(self,bgd):
        '''subtract background which is passed as an identical class'''
        self.probe_on_array = self.probe_on_array - bgd.probe_on
        self.probe_off_array = self.probe_off_array - bgd.probe_off
        self.reference_on_array = self.reference_on_array - bgd.reference_on
        self.reference_off_array = self.reference_off_array - bgd.reference_off
        return
        
    def manipulate_reference(self,refman):
        '''manipulates reference to lower noise.
           1. Takes each spectra individually
           2. Centers them on pixel "nfScaleCenter"
           3. Multiplies the x axis by "nfScaleFactor", to scale the horizontal axis
           4. Re-centers the axis to its initial position
           5. Adds a fixed horizontal offset
           6. Interpolates the Y values mapped onto the "ajusted" horizontal
              axis back onto an unmodified axis, to fit the probe spectra'''
        vs, vo, ho, sc, sf = refman
        if vs <= 0:
            vs = 1
        if sf <= 0:
            sf = 1
        x = np.linspace(0,self.num_pixels-1,self.num_pixels)
        new_x = ((x-sc)*sf)+sc-ho
        for i,spectra in enumerate(self.reference_off_array):
            self.reference_off_array[i] = np.interp(new_x,x,spectra*vs+vo)
        for i,spectra in enumerate(self.reference_on_array):
            self.reference_on_array[i] = np.interp(new_x,x,spectra*vs+vo)
        return
        
    def correct_probe_with_reference(self):
        '''reference correct the probe'''
        self.refd_probe_on_array = self.probe_on_array/self.reference_on_array
        self.refd_probe_off_array = self.probe_off_array/self.reference_off_array
        return
        
    def average_refd_shots(self):
        '''averages the referenced shots'''
        self.refd_probe_on = self.refd_probe_on_array.mean(axis=0)
        self.refd_probe_off = self.refd_probe_off_array.mean(axis=0)
        return
        
    def calcuate_dtt(self,use_reference=False,cutoff=[0,100],use_avg_off_shots=True,max_dtt=1):
        '''calculate dtt for each shot pair'''
        high_dtt = False
        if use_reference is True:
            if use_avg_off_shots is True:
                self.dtt_array = (self.refd_probe_on_array-self.refd_probe_off_array)/self.refd_probe_off
            if use_avg_off_shots is False:
                self.dtt_array = (self.refd_probe_on_array-self.refd_probe_off_array)/self.refd_probe_off_array
        if use_reference is False:
            if use_avg_off_shots is True:
                self.dtt_array = (self.probe_on_array-self.probe_off_array)/self.probe_off
            if use_avg_off_shots is False:
                self.dtt_array = (self.probe_on_array-self.probe_off_array)/self.probe_off_array
        self.dtt = self.dtt_array.mean(axis=0)
        fin_dtt = self.dtt[np.isfinite(self.dtt)]
        if np.abs(fin_dtt[cutoff[0]:cutoff[1]]).max() > max_dtt:
            high_dtt = True
            print('High dtt! '+str(datetime.datetime.now()))
        return high_dtt
        
    def calculate_dtt_error(self,use_reference=True,use_avg_off_shots=True):
        '''calculates standard deviation of the dtt array'''
        if use_reference is True:
            if use_avg_off_shots is True:
                self.probe_shot_error = np.std(2*(self.probe_on_array-self.probe_off_array)/(self.probe_on+self.probe_off),axis=0)
                self.ref_shot_error = np.std(2*(self.reference_on_array-self.reference_off)/(self.reference_on_array+self.reference_off),axis=0)
            if use_avg_off_shots is False:
                self.probe_shot_error = np.std(2*(self.probe_on_array-self.probe_off_array)/(self.probe_on_array+self.probe_off_array),axis=0)
                self.ref_shot_error = np.std(2*(self.reference_on_array-self.reference_off_array)/(self.reference_on_array+self.reference_off_array),axis=0)
            self.dtt_error = np.std(self.refd_probe_off_array,axis=0)
        if use_reference is False:
            self.probe_shot_error = np.std(2*(self.probe_on_array-self.probe_off_array)/(self.probe_on_array+self.probe_off_array),axis=0)
        return
        