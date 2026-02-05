# TAGs for data sending up to HMI
from logic.tag import *

# current temperature
UPTAG_CUR_TEMPERATURE = RealOutputTag("cur_temerature", "{:-.2f}")

# lamp state
UPTAG_LAMP_STATE = DiscreteOutputTag("lamp_state")

#lamp countdown timer
UPTAG_COUNTDOWN_TIMER = IntOutputTag("countdown_timer")