import time
import RPi.GPIO as GPIO

STEP_PIN = 11
DIR_PIN = 29

GPIO.setwarnings(False)
GPIO.setmode(GPIO.BOARD)

GPIO.setup(DIR_PIN, GPIO.OUT)
GPIO.setup(STEP_PIN, GPIO.OUT)

# Pi idle LOW -> ULN outputs off
GPIO.output(DIR_PIN, GPIO.LOW)
GPIO.output(STEP_PIN, GPIO.LOW)

time.sleep(1)

print("Setting direction...")
GPIO.output(DIR_PIN, GPIO.HIGH)   # try one direction first through ULN
time.sleep(0.1)

print("Pulsing 400 steps...")
for _ in range(400):
    GPIO.output(STEP_PIN, GPIO.HIGH)
    time.sleep(0.001)
    GPIO.output(STEP_PIN, GPIO.LOW)
    time.sleep(0.001)

print("Done.")
GPIO.cleanup()
