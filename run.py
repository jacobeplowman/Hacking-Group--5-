from machine import Pin, I2C
from ssd1306 import SSD1306_I2C
import utime
import machine, neopixel, utime
from pitches import *
import json


def get_background(n):
    """
    measure background temperature
    """
    temp_list = []
    for i in range(n):
        # get latest data from sensor    
        reading = analog_value.read_u16()
        temp = maptemp(reading)
        temp_list.append(temp)
        history["avg"].append(sum(temp_list[-6:])/len(temp_list[-6:]))
        avg_temp = moving_avg(temp)
        
        # OLED display
        if not i%5:
            oled.fill(0)
            oled.show()
            oled.text(f"Temp: {history['avg'][-1]:.1f}",0,0)
            oled.text("Heating: Off",0,10)
            oled.text(f"Target: {target}",0,20)
            oled.text("Speed: 0",0,30)
            oled.text("Msr BG Temp",0,40)
            oled.show()
        utime.sleep(0.2)
    return sum(temp_list)/n

def maprange(a, b, s):
    """
    map a value S from range A to range B
    """
    (a1, a2), (b1, b2) = a, b
    return  b1 + ((s - a1) * (b2 - b1) / (a2 - a1))

def maptemp(brightness):
    return maprange((MIN_BRIGHTNESS, MAX_BRIGHTNESS), (20, 100), brightness)

def motor(speed):
    # switch off
    if speed == 0:
        M1B.duty_u16(0)
    elif speed >= 0 and speed <= 1:
        duty = int(maprange((0, 1), (350, 65535), speed))
        M1B.duty_u16(duty)
    # slow
    elif speed == 2:
        M1B.duty_u16(20000)
    # medium
    elif speed == 3:
        M1B.duty_u16(40000)
    # fast
    elif speed == 4:
        M1B.duty_u16(65535)

def display(msg):
    oled.fill(0)
    oled.show()
    oled.text(f"Temp: {msg["Temp"]:.1f}",0,0)
    if msg["Heating"]==True:
        oled.text("Heating: On",0,10)
    else:
        oled.text("Heating: Off",0,10)
    oled.text(f"Target: {msg["Target"]}",0,20)
    if isinstance(msg["Speed"], int):
        oled.text(f"Speed: {msg["Speed"]}",0,30)
    else:
        oled.text(f"Speed: {msg["Speed"]:.2f}",0,30)
    if finished:
        oled.text("Finished",0,40)
    else:
        oled.text(f"Remaining: {msg["Est"]}s",0,40)
    oled.show()
    
def alarm():
    """
    Melody Mario
    """
    # mario notes
    mario = [E7, E7, 0, E7, 0, C7, E7, 0, G7, 0, 0, 0, G6, 0, 0, 0, C7, 0, 0, G6, 0, 0, E6, 0, 0, A6, 0, B6, 0, AS6, A6, 0, G6, E7, 0, G7, A7, 0, F7, G7, 0, E7, 0,C7, D7, B6, 0, 0, C7, 0, 0, G6, 0, 0, E6, 0, 0, A6, 0, B6, 0, AS6, A6, 0, G6, E7, 0, G7, A7, 0, F7, G7, 0, E7, 0,C7, D7, B6, 0, 0]
    for i in mario:
        if i == 0:
            buzzer.duty_u16(0)            # 0% duty cycle
        else:
            buzzer.freq(i)                # set frequency (notes)
            buzzer.duty_u16(19660)        # 30% duty cycle
        utime.sleep(0.15)

def exp_weighted_moving_avg(beta):
    """
    Exponentially weighted moving average
    """
    # initialize moving average V
    v = 0
    def new_average(t):
        nonlocal v
        v = beta * v + (1-beta) * t
        return v / (1-beta**t)
    return new_average

# buzzer
buzzer = machine.PWM(machine.Pin(22))

# LED light pico
np = neopixel.NeoPixel(machine.Pin(18), 2)

# light sensor
analog_value = machine.ADC(27)

# OLED
i2c=I2C(0,sda=Pin(0), scl=Pin(1), freq=100000)
oled = SSD1306_I2C(128, 64, i2c)

# Setup DC Motor pins
M1A = machine.PWM(machine.Pin(4))
M1B = machine.PWM(machine.Pin(5))
M1A.freq(50)
M1B.freq(50)

# environment constant
MIN_BRIGHTNESS = 4000
MAX_BRIGHTNESS = 40000

# config
interval = 0.2
heating_intensity = 2.0
cooling_coef = 0.03
beta = 0.83
gamma1 = 0.97
gamma2 = 1.01

# initialization
time = 0.0
finished = False
alarmed = False
b = 0
heating = True
moving_avg = exp_weighted_moving_avg(beta)
speed_dict = {2: "slow", 3: "medium", 4: "fast"}
history = {"avg": []}

# user setting
m = input("Select input mode, console(c) or file(f):")
if m == "c":
    target = int(input("Target temperature:"))
    speed = float(input("stirrer's speed: "))
    remaining = float(input("Duration: "))
elif m == "f":
    file_name = input("file path:")
    with open(file_name, 'r') as f:
        # importing settings from json file
        setting = json.load(f)
    target = setting["target"]
    speed = float(setting["speed"])
    remaining = setting["remaining"]

print(f"Target temperature = {target}℃")
if speed in map(float, speed_dict.keys()):
    speed = int(speed)
    print(f"Speed = {speed_dict[speed]}")
else:
    assert(speed>=0 and speed <= 1), "Must input a number between 0 and 1"
    print(f"Speed = {round(speed*100)}%")
est = int(remaining) + 1  # EST is an integer
print(f"Duration = {remaining} seconds")

# measuring background temperature
background = get_background(15)
avg_temp = background
print(f"background temperature: {background}℃")

# running
while True:
    # control motor
    if not finished:
        motor(speed)
    else:
        speed = 0
        motor(speed)

    # heating or cooling simulation
    if not finished and heating:
        # switch on heating indicator
        np[1] = (10, 0, 0)
        b = b + heating_intensity - cooling_coef*(avg_temp-background)
    else:
        # switch off heating indicator
        np[1] = (0, 0, 0)
        b = b - cooling_coef*(avg_temp-background)
        if b < 0:
            b = 0
    np[0] = (round(b), round(b), round(b))
    np.write()
    
    # get latest data from sensor    
    reading = analog_value.read_u16()
    temp = maptemp(reading)
    avg_temp = moving_avg(temp)
    
    # add it to HISTORY
    history["avg"].append(avg_temp)
    
    # temperature controller
    if avg_temp < (target*gamma1):
        heating = True
    elif avg_temp > (target*gamma2):
        heating = False
        
    # refresh OLED display every second
    if int(remaining)+1 < est:
        est = int(remaining) + 1
        msg = {"Temp": avg_temp,
               "Target": target,
               "Speed": speed,
               "Finished": finished,
               "Heating": heating,
               "Est": est}
        display(msg)
        print(f"{avg_temp:.1f}℃")

        
    # alarm when finishing
    if finished and not alarmed:
        alarm()
        alarmed = True
    
    # determine if finished or not
    if not finished and not est:
        finished = True
    
    # auto-exit
    if finished:
        latest = history["avg"][-5:]
        mean = sum(latest) / len(latest)
        var = sum((x-mean)**2 for x in latest)/len(latest)
        std = var ** 0.5
        # check if the cooling curve is flat
        if std < 0.3 and mean-background < 0.05*(target-background):
            break
        
    # delay
    utime.sleep(interval)
    remaining = remaining - interval

# save data to file
with open("history.json", 'w') as f:
    json.dump(history, f)

# turn off OLED and neopixel
oled.fill(0)
oled.show()
np[0] = (0, 0, 0)
np.write()
print("End")