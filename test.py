#Written By: Unknown
#Extensively Modified By:Jeff Akerson for use as a Backgauge on a Brakepress

from tkinter import *
from time import sleep
# import RPi.GPIO as GPIO

try:
    import RPi.GPIO as GPIO
except ImportError:
    print("GPIO not available, using dummy mode")

    class DummyGPIO:
        BOARD = OUT = IN = HIGH = LOW = PUD_DOWN = True

        def setwarnings(self, *a): pass
        def setmode(self, *a): pass
        def setup(self, *a, **k): pass
        def output(self, *a): pass
        def input(self, *a): return False
        def cleanup(self): pass

    GPIO = DummyGPIO()



#Build the GUI Main Frame
root = Tk()
root.attributes('-fullscreen',True)

#Getting Screen Width and Height of Display
width= root.winfo_screenwidth()
height= root.winfo_screenheight()

#Setting Tkinter Window Size
root.geometry("%dx%d" % (width, height))
root.title("Visionary Metals Backgauge Control")

#cChange the Size of Buttons and Frames
xpadframe=0
xpadbutton=10
xpadnums=30
xpadsymbols=20
ypadbutton=30

#Seting the Calculator Frame Size
calframe= LabelFrame(root, text="Calculator", padx=xpadframe, pady=20)
calframe.grid(row=0, column=0, sticky= N, padx=10, pady=10)

#Seting the Depth Frame Size
fenceframe=LabelFrame(root, text= "Stop Depth", padx=xpadframe, pady=20)
fenceframe.grid(row=0, column=1, sticky= N, padx= 10, pady=10)

#Seting the Height Frame Size
heightframe=LabelFrame(root, text= "Stop Height", padx=xpadframe, pady=20 )
heightframe.grid(row=0, column=2, sticky= N, padx=10, pady=10)

#Seting the Height Shorcut Frame Size
h_shortcutframe=LabelFrame(heightframe, text= "Height Shortcuts", padx=xpadframe, pady=10 )
h_shortcutframe.grid(row=5, column=0, padx=0, pady=10, columnspan=4)

#Seting the Depth Shorcut Frame Size
d_shortcutframe=LabelFrame(fenceframe, text= "Depth Shortcuts", padx=xpadframe, pady=10 )
d_shortcutframe.grid(row=5, column=0, padx=0, pady=10, columnspan=4)

GPIO.setwarnings(False)

######Setup Pins
#Depth Position Outputs
DIR_f = 29   # Direction GPIO Pin for Fence
STEP_f = 11  # Step GPIO Pin
MAX_f = 240  #this is the dimension that should be displayed when the depth is on the max limit sensor
MIN_f = 0    #this is the dimension that should be displayed when the depth is on the min limit sensor
CW_f = 0     # Clockwise Rotation
CCW_f = 1    # Counterclockwise Rotation


#Height Position Outputs
DIR_h = 31   # Direction GPIO Pin
STEP_h = 13  # Step GPIO Pin
MAX_h = 150  #this is the dimension that should be displayed when the height is on the max limit sensor
MIN_h = 0    #this is the dimension that should be displayed when the height is on the min limit sensor
CW_h = 0     # Clockwise Rotation
CCW_h = 1    # Counterclockwise Rotation

#Sensor inputs
fencezero =  11   # GPIO Pin depth zero
fenceendpos = 29  # GPIO Pin depth end of travel
heightzero = 18   # GPIO Pin height zero
heightend = 22    # GPIO Pin depth end of travel

#defining speed for motors
#Depth
RPM_f = 500
steps_per_revolution_f = 400
fdelay = 1/((RPM_f*steps_per_revolution_f)/60)
stp_per_inch_f = 200


#Height
RPM_h = 500
steps_per_revolution_h = 400
hdelay = 1/((RPM_h*steps_per_revolution_h)/60)
stp_per_inch_h = 200

#Entry Panels and Locations
#Calc Entry Box Start#######################
cal = Entry(calframe, width=10, borderwidth=5, font=("arial", 38))
cal.grid(row=0, column=0, columnspan=4, padx=0, pady=10)
#Calc Entry Box End#######################

#Stop Depth Entry Box Start#######################
Current_fence_position = Entry(fenceframe, width=10, borderwidth=5, font=("arial", 38))
Current_fence_position.grid(row=0, column=0, columnspan=4, padx=0, pady=10)
Current_fence_position.insert(0, 0)
#Stop Depth Entry Box End#######################

#Stop Height Entry Box Start#######################
C_height_e = Entry(heightframe, width=10, borderwidth=5, font=("arial", 38))
C_height_e.grid(row=0, column=0, columnspan=4, padx=0, pady=10)
C_height_e.insert(0, 0)
#Stop Height Entry Box End#######################

#Commanded Stop Depth Entry Box Text Start#######################
C_fence_position =Label (fenceframe, text = "Commanded \nDepth ", font=("Arial", 12))
C_fence_position.grid (row=3, column=0)
#Stop Depth Entry Box Text End#######################

#Commanded Stop Depth EntryBox Start##################
fen = Entry(fenceframe, width=7, borderwidth=2, font=("Arial", 38))
fen.grid(row=3, column=1)
fen.insert(0,0)
#Commanded Stop Depth Entry Box Start##################

#Commanded Stop Height Entry Box Text Start#######################
C_blade_height = Label (heightframe, text = "Commanded \nHeight ", font=("Arial",12))
C_blade_height.grid (row=3, column=0)
#Commanded Stop Height Entry Box Text End#######################

#Commanded Stop Height Entry Box Start##################
height = Entry(heightframe, width=7, borderwidth=2, font=("Arial", 38))
height.grid(row=3, column=1)
height.insert(0,0)
#Commanded Stop Height Entry Box Start##################

#Calculator functions
def button_click(number):
    current = cal.get()
    cal.delete(0, END)
    cal.insert(0, str(current) + str(number))

def button_clear():
    cal.delete(0, END)

def button_add():
    first_number = cal.get()
    global f_num
    global math
    math = "addition"
    f_num = float(first_number)
    cal.delete(0, END)

def button_equal():
    second_number = cal.get()
    cal.delete(0, END)
    
    if math == "addition":
        cal.insert(0, f_num + float(second_number))

    if math == "subtraction":
        cal.insert(0, f_num - float(second_number))

    if math == "multiplication":
        cal.insert(0, f_num * float(second_number))

    if math == "division":
        cal.insert(0, f_num / float(second_number))

def button_subtract():
    first_number = cal.get()
    global f_num
    global math
    math = "subtraction"
    f_num = float(first_number)
    cal.delete(0, END)

def button_multiply():
    first_number = cal.get()
    global f_num
    global math
    math = "multiplication"
    f_num = float(first_number)
    cal.delete(0, END)

def button_divide():
    first_number = cal.get()
    global f_num
    global math
    math = "division"
    f_num = float(first_number)
    cal.delete(0, END)

def Inch_to_mm():
    C_num= cal.get()
    ans_in_mm = float(C_num)* 25.4
    cal.delete(0, END)
    cal.insert(0, ans_in_mm)
def mm_to_Inch():
    C_num= cal.get()
    ans_in_inch = float(C_num)/ 25.4
    cal.delete(0, END)
    cal.insert(0, ans_in_inch)

####Move motors
#Move Depth
def move_fence():
    #setup variables
    global Current_fence_position
    Startposition= Current_fence_position.get()
    new_position = float(fen.get())
    
    #task to complete first
    fen.delete(0, END)
    GPIO.setmode(GPIO.BOARD)
    GPIO.setup(DIR_f, GPIO.OUT)
    GPIO.setup(STEP_f, GPIO.OUT)
    GPIO.setup(fencezero, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
    GPIO.setup(fenceendpos, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
    
    if float(Startposition) < float(new_position):
        dis_to_move =  float(new_position)- float(Startposition)
    
        move_fence_steps = int(stp_per_inch_f * float(dis_to_move))
        
        for steps in range(move_fence_steps):
            if GPIO.input(fenceendpos) == True:
                Current_fence_position.delete(0,END)
                Current_fence_position.insert(0, str(MAX_f))
                break
            GPIO.output(DIR_f, CW_f)
            GPIO.output(STEP_f, GPIO.HIGH)
            sleep(fdelay)
            GPIO.output(STEP_f, GPIO.LOW)
            sleep(fdelay)
            Current_fence_position.delete(0,END)
            Current_fence_position.insert(0, str(new_position))
        
    elif float(Startposition) > float(new_position):
        dis_to_move =  float(Startposition)- float(new_position)
    
        move_fence_steps = int(stp_per_inch_f * float(dis_to_move))
        for steps in range(move_fence_steps):
            if GPIO.input(fencezero) == True:
                Current_fence_position.delete(0,END)
                Current_fence_position.insert(0, str(MIN_f))
                break
            GPIO.output(DIR_f, CCW_f)
            GPIO.output(STEP_f, GPIO.HIGH)
            sleep(fdelay)
            GPIO.output(STEP_f, GPIO.LOW)
            sleep(fdelay)
            Current_fence_position.delete(0,END)
            Current_fence_position.insert(0, str(new_position))
    elif Startposition == new_position:
        return

#reset things for next function
    GPIO.cleanup()
    
#Move Height
def move_blade():
    #setup variables
    global C_height_e
    Startposition= C_height_e.get()
    new_position = float(height.get())
    
    #task to complete first
    height.delete(0, END)
    GPIO.setmode(GPIO.BOARD)
    GPIO.setup(DIR_h, GPIO.OUT)
    GPIO.setup(STEP_h, GPIO.OUT)
    GPIO.setup(heightzero, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
    GPIO.setup(heightend, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
    
    if float(Startposition) < float(new_position):
        dis_to_move =  float(new_position)- float(Startposition)
    
        move_height_steps = int(stp_per_inch_h * float(dis_to_move))
        
        for steps in range(move_height_steps):
            if GPIO.input(heightend)== True:
               C_height_e.delete(0,END)
               C_height_e.insert(0, str(MAX_h))
               break
            GPIO.output(DIR_h, CW_h)
            GPIO.output(STEP_h, GPIO.HIGH)
            sleep(hdelay)
            GPIO.output(STEP_h, GPIO.LOW)
            sleep(hdelay)
            C_height_e.delete(0,END)
            C_height_e.insert(0, str(new_position))
        
    elif float(Startposition) > float(new_position):
        dis_to_move =  float(Startposition)- float(new_position)
    
        move_height_steps = int(stp_per_inch_h * float(dis_to_move))
        for steps in range(move_height_steps):
            if GPIO.input(heightzero)== True:
                C_height_e.delete(0,END)
                C_height_e.insert(0, str(MIN_h))
                break
            GPIO.output(DIR_h, CCW_h)
            GPIO.output(STEP_h, GPIO.HIGH)
            sleep(hdelay)
            GPIO.output(STEP_h, GPIO.LOW)
            sleep(hdelay)
            C_height_e.delete(0,END)
            C_height_e.insert(0, str(new_position))
        
    elif Startposition == new_position:
        return

    GPIO.cleanup()

#####Shortcut functions
#Die Shortcuts
def shortcut_h0():
    C_num= 10
    cal.delete(0, END)
    height.delete(0, END)
    height.insert(0, C_num)
    print ('Calling function...')
    move_blade()

def shortcut_h1():
    C_num= 11
    cal.delete(0, END)
    height.delete(0, END)
    height.insert(0, C_num)
    print ('Calling function...')
    move_blade()

def shortcut_h2():
    C_num= 12
    cal.delete(0, END)
    height.delete(0, END)
    height.insert(0, C_num)
    print ('Calling function...')
    move_blade()

def shortcut_h3():
    C_num= 13
    cal.delete(0, END)
    height.delete(0, END)
    height.insert(0, C_num)
    print ('Calling function...')
    move_blade()

#Jog Height Sortcuts
def shortcut_h4():
    jog_first_number = C_height_e.get()
    global h_jog
    h_jog = float (jog_first_number)
    height.delete(0, END)
    height_num = (h_jog + float(.1))
    height_num = round (height_num, 4)
    height.insert (0, height_num)
    print ('Calling function...')
    move_blade()

def shortcut_h5():
    jog_first_number = C_height_e.get()
    global h_jog
    h_jog = float (jog_first_number)
    height.delete(0, END)
    height_num = (h_jog + float(.01))
    height_num = round (height_num, 4)
    height.insert (0, height_num)
    print ('Calling function...')
    move_blade()
    
def shortcut_h6():
    jog_first_number = C_height_e.get()
    global h_jog
    h_jog = float (jog_first_number)
    height.delete(0, END)
    height_num = (h_jog + float(.001))
    height_num = round (height_num, 4)
    height.insert (0, height_num)
    print ('Calling function...')
    move_blade()
    
def shortcut_h7():
    jog_first_number = C_height_e.get()
    global h_jog
    h_jog = float (jog_first_number)
    height.delete(0, END)
    height_num = (h_jog - float(.1))
    height_num = round (height_num, 4)
    height.insert (0, height_num)
    print ('Calling function...')
    move_blade()
    
def shortcut_h8():
    jog_first_number = C_height_e.get()
    global h_jog
    h_jog = float (jog_first_number)
    height.delete(0, END)
    height_num = (h_jog - float(.01))
    height_num = round (height_num, 4)
    height.insert (0, height_num)
    print ('Calling function...')
    move_blade()
    
def shortcut_h9():
    jog_first_number = C_height_e.get()
    global h_jog
    h_jog = float (jog_first_number)
    height.delete(0, END)
    height_num = (h_jog - float(.001))
    height_num = round (height_num, 4)
    height.insert (0, height_num)
    print ('Calling function...')
    move_blade()

#Jog Depth Sortcuts
def shortcut_d0():
    jog_first_number = Current_fence_position.get()
    global d_jog
    d_jog = float (jog_first_number)
    fen.delete(0, END)
    fen_num = (d_jog + float(.1))
    fen_num = round (fen_num, 4)
    fen.insert (0, fen_num)
    print ('Calling function...')
    move_fence()

def shortcut_d1():
    jog_first_number = Current_fence_position.get()
    global d_jog
    d_jog = float (jog_first_number)
    fen.delete(0, END)
    fen_num = (d_jog + float(.01))
    fen_num = round (fen_num, 4)
    fen.insert (0, fen_num)
    print ('Calling function...')
    move_fence()

    
def shortcut_d2():
    jog_first_number = Current_fence_position.get()
    global d_jog
    d_jog = float (jog_first_number)
    fen.delete(0, END)
    fen_num = (d_jog + float(.001))
    fen_num = round (fen_num, 4)
    fen.insert (0, fen_num)
    print ('Calling function...')
    move_fence()

    
def shortcut_d3():
    jog_first_number = Current_fence_position.get()
    global d_jog
    d_jog = float (jog_first_number)
    fen.delete(0, END)
    fen_num = (d_jog - float(.1))
    fen_num = round (fen_num, 4)
    fen.insert (0, fen_num)
    print ('Calling function...')
    move_fence()

    
def shortcut_d4():
    jog_first_number = Current_fence_position.get()
    global d_jog
    d_jog = float (jog_first_number)
    fen.delete(0, END)
    fen_num = (d_jog - float(.01))
    fen_num = round (fen_num, 4)
    fen.insert (0, fen_num)
    print ('Calling function...')
    move_fence()
    
def shortcut_d5():
    jog_first_number = Current_fence_position.get()
    global d_jog
    d_jog = float (jog_first_number)
    fen.delete(0, END)
    fen_num = (d_jog - float(.001))
    fen_num = round (fen_num, 4)
    fen.insert (0, fen_num)
    print ('Calling function...')
    move_fence()


def move_cal_to_fence():
    C_num= float(cal.get())
    cal.delete(0, END)
    fen.delete(0, END)
    fen.insert(0, C_num)

def move_cal_to_height():
    C_num= float(cal.get())
    cal.delete(0, END)
    height.delete(0, END)
    height.insert(0, C_num)

def clear_fen():
    fen.delete(0, END)

def clear_height():
    height.delete(0, END)

####Homing Shortcuts
#Home All
def home_all():
    C_num= 100
    cal.delete(0, END)
    fen.delete(0, END)
    fen.insert(0, C_num)
    height.delete(0, END)
    height.insert(0, C_num)
    print ('Calling function...')
    move_fence()
    move_blade()

#Home Depth
def home_depth():
    C_num= 100
    cal.delete(0, END)
    fen.delete(0, END)
    fen.insert(0, C_num)
    print ('Calling function...')
    move_fence()
    
#Home Height   
def home_height():
    C_num= 100
    cal.delete(0, END)
    height.delete(0, END)
    height.insert(0, C_num)
    print ('Calling function...')
    move_blade()
    
# Define Calulator Buttons
button_1 = Button(calframe, text="1", padx=xpadnums, pady=ypadbutton, command=lambda: button_click(1))
button_2 = Button(calframe, text="2", padx=xpadnums, pady=ypadbutton, command=lambda: button_click(2))
button_3 = Button(calframe, text="3", padx=xpadnums, pady=ypadbutton, command=lambda: button_click(3))
button_4 = Button(calframe, text="4", padx=xpadnums, pady=ypadbutton, command=lambda: button_click(4))
button_5 = Button(calframe, text="5", padx=xpadnums, pady=ypadbutton, command=lambda: button_click(5))
button_6 = Button(calframe, text="6", padx=xpadnums, pady=ypadbutton, command=lambda: button_click(6))
button_7 = Button(calframe, text="7", padx=xpadnums, pady=ypadbutton, command=lambda: button_click(7))
button_8 = Button(calframe, text="8", padx=xpadnums, pady=ypadbutton, command=lambda: button_click(8))
button_9 = Button(calframe, text="9", padx=xpadnums, pady=ypadbutton, command=lambda: button_click(9))
button_0 = Button(calframe, text="0", padx=xpadnums, pady=ypadbutton, command=lambda: button_click(0))
button_decimal = Button(calframe, text=".", font=("Arial", 24), padx=30, pady=20, command=lambda: button_click("."))
button_add = Button(calframe, text="+", padx=xpadsymbols, pady=ypadbutton, command=button_add)
button_equal = Button(calframe, text="=", padx=xpadnums, pady=ypadbutton, command=button_equal)
button_clear = Button(calframe, text="Clear", padx=8, pady=ypadbutton, command=button_clear)
button_subtract = Button(calframe, text="-", padx=23, pady=ypadbutton, command=button_subtract)
button_multiply = Button(calframe, text="*", padx=22, pady=ypadbutton, command=button_multiply)
button_divide = Button(calframe, text="/", padx=22, pady=ypadbutton, command=button_divide)

inch_to_mm = Button(calframe, text="in. to mm", padx=8, pady=ypadbutton, command=Inch_to_mm)
mm_to_inch = Button(calframe, text="mm to in.", padx=8, pady=ypadbutton, command=mm_to_Inch)

##### Define Other Buttons
#Move Buttons
button_movefence = Button(fenceframe, text="Move To Depth", padx=0, pady=ypadbutton, command=move_fence)
button_moveblade = Button(heightframe, text="Move To Height", padx=1, pady=ypadbutton, command=move_blade)

#Die Shortcut Buttons - Height Frame
button_moveblade_0 = Button(h_shortcutframe, text="5/8 \nDie", padx=10, pady=ypadbutton, command=shortcut_h0)
button_moveblade_1 = Button(h_shortcutframe, text="1.0 \nDie", padx=10, pady=ypadbutton, command=shortcut_h1)
button_moveblade_2 = Button(h_shortcutframe, text="1.5 \nDie", padx=10, pady=ypadbutton, command=shortcut_h2)
button_moveblade_3 = Button(h_shortcutframe, text="2.0 \nDie", padx=10, pady=ypadbutton, command=shortcut_h3)

#Jog Shortcut Buttons - Height Frame
button_jogblade_4 = Button(h_shortcutframe, text="Jog \n+.100", padx=10, pady=ypadbutton, command=shortcut_h4)
button_jogblade_5 = Button(h_shortcutframe, text="Jog \n+.010", padx=10, pady=ypadbutton, command=shortcut_h5)
button_jogblade_6 = Button(h_shortcutframe, text="Jog \n+.001", padx=10, pady=ypadbutton, command=shortcut_h6)

button_jogblade_7 = Button(h_shortcutframe, text="Jog \n-.100", padx=13, pady=ypadbutton, command=shortcut_h7)
button_jogblade_8 = Button(h_shortcutframe, text="Jog \n-.010", padx=13, pady=ypadbutton, command=shortcut_h8)
button_jogblade_9 = Button(h_shortcutframe, text="Jog \n-.001", padx=13, pady=ypadbutton, command=shortcut_h9)

#Jog Shortcut Buttons - Depth Frame
button_jogheight_0 = Button(d_shortcutframe, text="Jog \n+.100", padx=10, pady=ypadbutton, command=shortcut_d0)
button_jogheight_1 = Button(d_shortcutframe, text="Jog \n+.010", padx=10, pady=ypadbutton, command=shortcut_d1)
button_jogheight_2 = Button(d_shortcutframe, text="Jog \n+.001", padx=10, pady=ypadbutton, command=shortcut_d2)

button_jogheight_3 = Button(d_shortcutframe, text="Jog \n-.100", padx=13, pady=ypadbutton, command=shortcut_d3)
button_jogheight_4 = Button(d_shortcutframe, text="Jog \n-.010", padx=13, pady=ypadbutton, command=shortcut_d4)
button_jogheight_5 = Button(d_shortcutframe, text="Jog \n-.001", padx=13, pady=ypadbutton, command=shortcut_d5)

#Grab Number Buttons
cal_to_fen_but = Button(fenceframe, text="Grab number", padx=0, pady=ypadbutton, command=move_cal_to_fence)
cal_to_height_but = Button(heightframe, text="Grab number", padx=1, pady=ypadbutton, command=move_cal_to_height)

#Clear Buttons
clear_fen_but = Button(fenceframe, text="Clear Commanded\nDepth", padx=1, pady=15, command=clear_fen)
clear_height_but = Button(heightframe, text="Clear Commanded\nHeight", padx=1, pady=15, command=clear_height)

#Define Home Buttons
home_all_but = Button(root, text="Home All", padx=30, pady=ypadbutton, command=home_all)
home_depth_but = Button(root, text="Home Depth", padx=15, pady=ypadbutton, command=home_depth)
home_height_but = Button(root, text="Home Height", padx=15, pady=ypadbutton, command=home_height)

##### Put the buttons on the screen
#Calculator Buttons
button_1.grid(row=3, column=0)
button_2.grid(row=3, column=1)
button_3.grid(row=3, column=2)

button_4.grid(row=2, column=0)
button_5.grid(row=2, column=1)
button_6.grid(row=2, column=2)

button_7.grid(row=1, column=0)
button_8.grid(row=1, column=1)
button_9.grid(row=1, column=2)

button_0.grid(row=4, column=1)
button_clear.grid(row=5, column=1, columnspan=2)
button_add.grid(row=4, column=3)
button_equal.grid(row=4, column=0)

button_subtract.grid(row=3, column=3)
button_multiply.grid(row=2, column=3)
button_divide.grid(row=1, column=3)
button_decimal.grid(row=4, column=2)
inch_to_mm.grid(row=6, column=2, columnspan=2)
mm_to_inch.grid(row=6, column=0, columnspan=2)

#Move Buttons
button_movefence.grid(row=1, column=0)
button_moveblade.grid(row=1, column=0)

#Die Shortcut Buttons - Height Frame
button_moveblade_0.grid(row=5, column=0)
button_moveblade_1.grid(row=6, column=0)
button_moveblade_2.grid(row=5, column=1)
button_moveblade_3.grid(row=6, column=1)

#Jog Shortcut Buttons - Height Frame
button_jogblade_4.grid(row=5, column=2)
button_jogblade_5.grid(row=5, column=3)
button_jogblade_6.grid(row=5, column=4)

button_jogblade_7.grid(row=6, column=2)
button_jogblade_8.grid(row=6, column=3)
button_jogblade_9.grid(row=6, column=4)

#Jog Shortcut Buttons - Depth Frame
button_jogheight_0.grid(row=5, column=2)
button_jogheight_1.grid(row=5, column=3)
button_jogheight_2.grid(row=5, column=4)

button_jogheight_3.grid(row=6, column=2)
button_jogheight_4.grid(row=6, column=3)
button_jogheight_5.grid(row=6, column=4)

#Grab Number Buttons
cal_to_fen_but.grid(row=1, column=1)
cal_to_height_but.grid(row=1, column=1)

#Clear Buttons
clear_fen_but.grid(row=2, column=0, columnspan=2)
clear_height_but.grid(row=2, column=0, columnspan=2)

#Homing Buttons
home_all_but.grid(row=2, column=0,)
home_depth_but.grid(row=2, column=1,)
home_height_but.grid(row=2, column=2,)

root.mainloop()

