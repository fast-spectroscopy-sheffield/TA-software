import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec

def init_plotting():
    #plt.rcParams['figure.figsize'] = (3,3)
    #plt.rcParams['figure.dpi'] = 300
    #plt.rcParams['font.size'] = 11
    plt.rcParams['font.family'] = 'Arial'
    #plt.rcParams['axes.labelsize'] = plt.rcParams['font.size']
    #plt.rcParams['axes.titlesize'] = 1.5*plt.rcParams['font.size']
    #plt.rcParams['legend.fontsize'] = 8
    #plt.rcParams['xtick.labelsize'] = plt.rcParams['font.size']
    #plt.rcParams['ytick.labelsize'] = plt.rcParams['font.size']
    #plt.rcParams['savefig.dpi'] = 2*plt.rcParams['savefig.dpi']
    plt.rcParams['xtick.major.size'] = 3
    plt.rcParams['xtick.minor.size'] = 1.5
    plt.rcParams['xtick.major.width'] = 0.5
    plt.rcParams['xtick.minor.width'] = 0.5
    plt.rcParams['ytick.major.size'] = 3
    plt.rcParams['ytick.minor.size'] = 1.5
    plt.rcParams['ytick.major.width'] = 0.5
    plt.rcParams['ytick.minor.width'] = 0.5
    plt.rcParams['legend.frameon'] = False
    plt.rcParams['legend.numpoints'] = 1
    plt.rcParams['legend.scatterpoints'] = 1
    plt.rcParams['axes.linewidth'] = 0.5
    
def st_kin_fig():
    gs = gridspec.GridSpec(1, 2,width_ratios=[1,3])
    f = plt.figure()
    l1 = f.add_subplot(gs[0]);
    l2 = f.add_subplot(gs[1]);
    l2.set_xscale('log');
    l1.locator_params(axis='x',nbins=4)
    l1.spines['right'].set_visible(False)
    l1.tick_params(right=0);
    l2.tick_params(left=0,labelleft=0);
    l2.spines['left'].set_visible(False);
    l1.set_xlabel('Time (ps)');
    l2.set_xlabel('Time (s)');
    l1.set_ylabel('$\Delta$$T$/$T$');
    return f, l1, l2
    
def st_image_fig():
    gs = gridspec.GridSpec(1, 2,width_ratios=[1,3])
    f = plt.figure()
    l1 = f.add_subplot(gs[0]);
    l2 = f.add_subplot(gs[1]);
    l2.set_xscale('log');
    l1.locator_params(axis='x',nbins=4)
    l1.spines['right'].set_visible(False)
    l1.tick_params(right=0);
    l2.tick_params(left=0,labelleft=0);
    l2.spines['left'].set_visible(False);
    l1.set_xlabel('Time (ps)');
    l2.set_xlabel('Time (s)');
    l1.set_ylabel('Wavelength (nm)');
    return f, l1, l2
    
def left_right_y():
    f,l1 = plt.subplots();
    l2 = l1.twinx();
    return f, l1, l2