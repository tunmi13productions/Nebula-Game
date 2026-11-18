import os
import sys

# Tests must never make sound: force OpenAL Soft's null driver before anything opens a device.
os.environ['ALSOFT_DRIVERS'] = 'null'
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
