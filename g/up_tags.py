# TAGs for data sending to web
from logic.tag import *

TAG_TEMPERATURE = RealOutputTag("th", "{:-.2f}")
TAG_HEATER_STATUS = DiscreteOutputTag("heater_status")