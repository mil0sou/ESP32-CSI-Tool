import serial, sys
s = serial.Serial()
s.port = '/dev/ttyACM0'
s.baudrate = 115200
s.dtr = False
s.rts = False
s.open()
while True:
    sys.stdout.write(s.readline().decode(errors='ignore'))
    sys.stdout.flush()
