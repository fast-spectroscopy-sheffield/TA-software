'''scripts to help create ta_gui_class.py from the QtCreator .ui file'''

import PyQt5.uic
import os

fpath = 'ta_gui.ui'

with open('ta_gui_class.py','w') as file:
    PyQt5.uic.compileUi(fpath, file)
