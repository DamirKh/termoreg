# TAGs for data reciving down from HMI
from logic.tag import *

# LAMP timer preset
DWTAG_PRESET_LAMP_TIMER = IntInputTag('preset_lamp_timer')

# LAMP command
DWTAG_COMMAND_LAMP_ON = DiscreteInputTag('command_lamp_on')
DWTAG_COMMAND_LAMP_OFF = DiscreteInputTag('command_lamp_off')