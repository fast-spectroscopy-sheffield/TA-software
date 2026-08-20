import datetime
import numpy as np


class DataProcessing:

    def __init__(self, probe_array, reference_array, first_pixel, num_pixels):
        self.untrimmed_probe_array = np.array(probe_array, dtype=int)
        self.probe_array = np.array(probe_array, dtype=float)[:, first_pixel:num_pixels+first_pixel]
        self.reference_array = np.array(reference_array, dtype=float)[:, first_pixel:num_pixels+first_pixel]
        self.raw_probe_array = np.array(probe_array, dtype=float)[:, first_pixel:num_pixels+first_pixel]
        self.raw_reference_array = np.array(reference_array, dtype=float)[:, first_pixel:num_pixels+first_pixel]
        self.first_pixel = first_pixel
        self.num_pixels = num_pixels
        
    def update(self, probe_array, reference_array, first_pixel, num_pixels):
        self.untrimmed_probe_array = probe_array
        self.probe_array = probe_array[:, first_pixel:num_pixels+first_pixel]
        self.reference_array = reference_array[:, first_pixel:num_pixels+first_pixel]
        self.first_pixel = first_pixel
        self.num_pixels = num_pixels
        
    def set_linear_pixel_correlation(self):
        """
        only necessary for NIR cameras
        """
        pr_corr = self.raw_probe_array.mean(axis=0)
        ref_corr = self.raw_reference_array.mean(axis=0)
        pr_corr[::2] = pr_corr[::2]/pr_corr[1::2]
        ref_corr[::2] = ref_corr[::2]/ref_corr[1::2]
        pr_corr[1::2] = pr_corr[1::2]/pr_corr[1::2]
        ref_corr[1::2] = ref_corr[1::2]/ref_corr[1::2]
        return pr_corr, ref_corr
        
    def linear_pixel_correlation(self, linear_corr):
        """
        only necessary for NIR cameras
        """
        self.probe_array = self.probe_array/linear_corr[0]
        self.reference_array = self.reference_array/linear_corr[1]
        return
        
    def separate_on_off(self, threshold, tau_flip_request=False):
        high_std = False
        pixel = threshold[0]
        thresh_value = threshold[1]
        self.trigger = []
        for shot in self.untrimmed_probe_array:
            self.trigger.append(shot[pixel])
        self.trigger = np.array(self.trigger)
        if np.abs(self.trigger-self.trigger.mean()).std() > 20:
            print('high std '+str(datetime.datetime.now()))
            #high_std = True #@todo what is the original function of this, and why was it commented out?
            # Presumably it should re-attempt to take data if the triggering goes wrong for a moment.
        if tau_flip_request is True:
            self.trigger = np.roll(self.trigger, 1)
        if (self.untrimmed_probe_array[0, pixel] >= thresh_value and not tau_flip_request) or (self.untrimmed_probe_array[0, pixel] < thresh_value and tau_flip_request):
            self.probe_on_array = self.probe_array[::2,:]
            self.probe_off_array = self.probe_array[1::2,:]
            self.reference_on_array = self.reference_array[::2,:]
            self.reference_off_array = self.reference_array[1::2,:]
        else:
            self.probe_on_array = self.probe_array[1::2,:]
            self.probe_off_array = self.probe_array[::2,:]
            self.reference_on_array = self.reference_array[1::2,:]
            self.reference_off_array = self.reference_array[::2,:]
        #Following for troubleshooting:
        '''
        print('[ length of probe_on_array = '+str(len(self.probe_on_array)))
        print('  length of probe_off_array = '+str(len(self.probe_off_array)))
        print('  length of reference_on_array = '+str(len(self.reference_on_array)))
        print('  length of reference_off_array = '+str(len(self.reference_off_array)))
        print('  length of self.untrimmed_probe_array = '+str(len(self.untrimmed_probe_array)))
        print('  untrimmed_probe_array[0] = '+str(self.untrimmed_probe_array[0][0:500]))
        print('  length of  untrimmed_probe_array[0] = '+str(len(self.untrimmed_probe_array[0])))
        '''
        return high_std
        
    def average_shots(self):
        self.probe_on = self.probe_on_array.mean(axis=0)
        self.probe_off = self.probe_off_array.mean(axis=0)
        self.reference_on = self.reference_on_array.mean(axis=0)
        self.reference_off = self.reference_off_array.mean(axis=0)
        return
        
    def delta_shots(self, use_cutoff=True, cutoff=[200,300]):
        '''
        Step I and II in the flowchat from Horn et al. 2026
        Note, Horn et al. do usual background correction prior to B-matrix referencing.
        Cutoff may be neccessary to speed up the calculations.
        '''
        # Pre-step, cutoff. Use local variables to avoid overwriting those attached to self (global).
        if use_cutoff == False:
            cutoff = [200,300]
            print('Cutoff not checked; defaulted to cutoff=[200,300] for B-matrix')
        probe_on_array = self.probe_on_array[:,cutoff[0]:cutoff[1]]
        probe_off_array = self.probe_on_array[:,cutoff[0]:cutoff[1]]
        reference_on_array = self.reference_on_array[:,cutoff[0]:cutoff[1]]
        reference_off_array = self.reference_off_array[:,cutoff[0]:cutoff[1]]
        # LHS of Step I
        self.probe_delta_array = probe_on_array - probe_off_array
        self.reference_delta_array = reference_on_array - reference_off_array
        # RHS of Step I
        self.probe_off_delta_array = np.zeros((int(probe_off_array.shape[0]/2), probe_off_array.shape[1])) # int accounts for halves, int(140.5) = 141 etc.
        self.reference_off_delta_array = np.zeros((int(reference_off_array.shape[0]/2), reference_off_array.shape[1]))
        for i in range(self.probe_off_delta_array.shape[0]):
            self.probe_off_delta_array[i,:] = probe_off_array[2*i,:] - probe_off_array[2*i+1,:]
            self.reference_off_delta_array[i,:] = reference_off_array[2*i,:] - reference_off_array[2*i+1,:]
        self.probe_off_delta_array = self.probe_off_delta_array.T
        self.reference_off_delta_array = self.reference_off_delta_array.T
        # Now Step II
        self.probe_delta_mean = self.probe_delta_array.mean(axis=0)
        self.reference_delta_mean = self.reference_delta_array.mean(axis=0)
        # ...the next line is also in the above average_shots function. @todo could get rid of one...
        self.probe_off_mean = probe_off_array.mean(axis=0)
        return
    
    def calculate_B_matrix(self):
        '''
        Step III and IV in the flowchart from Horn et al. 2026
        @todo the cross-variance step is currently very slow...
        Should try the DLL from Horn et al. 2026.
        '''
        # Step III, cross-covariance
        print('pre-cross-covariance '+str(datetime.datetime.now()))
        m = self.probe_off_delta_array.shape[0]
        n = self.reference_off_delta_array.shape[0]
        C = np.zeros((m, n))
        for ii in range(m):
            for jj in range(n):
                r = np.cov(self.probe_off_delta_array[jj, :], self.reference_off_delta_array[ii, :])
                C[ii, jj] = r[0, 1]
        print('pre-inverted-covariance '+str(datetime.datetime.now()))
        # Step III, inverted covariance
        A = np.linalg.inv(np.cov(self.reference_off_delta_array))
        # Step IV, calculate B-matrix by matrix multiplication
        print('pre-B-matrix '+str(datetime.datetime.now()))
        self.B_matrix = A @ C
        return
    
    def calculate_dtt_B_matrix(self, max_dtt=1):
        '''
        Step V in the flowchart from Horn et al. 2026
        @todo need to figure out how to collate this with the dtt calculated ratiometrically
        For now, calculate as a 'separate' dtt_B_matrix to enable a comparison
        '''
        high_dtt = False
        self.dtt_B_matrix = (self.probe_delta_mean - self.reference_delta_mean @ self.B_matrix)/(self.probe_off_mean)
        fin_dtt = self.dtt_B_matrix[np.isfinite(self.dtt_B_matrix)]
        if fin_dtt.size == 0 or np.abs(fin_dtt).max() > max_dtt:
            high_dtt = True
            print('High dtt for B-matrix! '+str(datetime.datetime.now()))
        print('post-dtt_by_B-matrix '+str(datetime.datetime.now()))
        return high_dtt
        
    def sub_bgd(self, bgd, tau_flip_request=False):
        if tau_flip_request is False:
            self.probe_on_array = self.probe_on_array - bgd.probe_on
            self.probe_off_array = self.probe_off_array - bgd.probe_off
            self.reference_on_array = self.reference_on_array - bgd.reference_on
            self.reference_off_array = self.reference_off_array - bgd.reference_off
        else: # @todo test this new (2026-08-04) 'else' statement in the lab. Does threshold also need to be considered?
            self.probe_on_array = self.probe_on_array - bgd.probe_off
            self.probe_off_array = self.probe_off_array - bgd.probe_on
            self.reference_on_array = self.reference_on_array - bgd.reference_off
            self.reference_off_array = self.reference_off_array - bgd.reference_on
        return
        
    def manipulate_reference(self, refman):
        """
        manipulates reference to lower noise.
           1. Takes each spectra individually
           2. Centers them on pixel "nfScaleCenter"
           3. Multiplies the x-axis by "nfScaleFactor", to scale the horizontal axis
           4. Re-centers the axis to its initial position
           5. Adds a fixed horizontal offset
           6. Interpolates the Y values mapped onto the ajusted horizontal
              axis back onto an unmodified axis, to fit the probe spectra
        """
        vs, vo, ho, sc, sf = refman
        if vs <= 0:
            vs = 1
        if sf <= 0:
            sf = 1
        x = np.linspace(0,self.num_pixels-1, self.num_pixels)
        new_x = ((x-sc)*sf)+sc-ho
        for i, spectra in enumerate(self.reference_off_array):
            self.reference_off_array[i] = np.interp(new_x, x, spectra*vs+vo)
        for i, spectra in enumerate(self.reference_on_array):
            self.reference_on_array[i] = np.interp(new_x, x, spectra*vs+vo)
        return
        
    def correct_probe_with_reference(self):
        self.refd_probe_on_array = self.probe_on_array/self.reference_on_array
        self.refd_probe_off_array = self.probe_off_array/self.reference_off_array
        return
        
    def average_refd_shots(self):
        self.refd_probe_on = self.refd_probe_on_array.mean(axis=0)
        self.refd_probe_off = self.refd_probe_off_array.mean(axis=0)
        return
        
    def calcuate_dtt(self, use_reference=False, cutoff=[0, 100], use_avg_off_shots=True, max_dtt=1):
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
        if fin_dtt.size == 0 or np.abs(fin_dtt[cutoff[0]:cutoff[1]]).max() > max_dtt:
            high_dtt = True
            print('High dtt! '+str(datetime.datetime.now()))
        return high_dtt
        
    def calculate_dtt_error(self, use_reference=True, use_avg_off_shots=True):
        if use_reference is True:
            if use_avg_off_shots is True:
                self.probe_shot_error = np.std(2*(self.probe_on_array-self.probe_off_array)/(self.probe_on+self.probe_off), axis=0)
                self.ref_shot_error = np.std(2*(self.reference_on_array-self.reference_off)/(self.reference_on_array+self.reference_off), axis=0)
            if use_avg_off_shots is False:
                self.probe_shot_error = np.std(2*(self.probe_on_array-self.probe_off_array)/(self.probe_on_array+self.probe_off_array), axis=0)
                self.ref_shot_error = np.std(2*(self.reference_on_array-self.reference_off_array)/(self.reference_on_array+self.reference_off_array), axis=0)
            self.dtt_error = np.std(self.refd_probe_off_array, axis=0)
        if use_reference is False:
            self.probe_shot_error = np.std(2*(self.probe_on_array-self.probe_off_array)/(self.probe_on_array+self.probe_off_array), axis=0)
        return
        