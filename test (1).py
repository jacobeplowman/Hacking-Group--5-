import utime
import machine


def get_background(n):
    """
    measure background brightness
    """
    brightness_list = []
    for i in range(n):
        # get latest data from sensor    
        reading = analog_value.read_u16()
        brightness_list.append(reading)
        utime.sleep(0.2)
    return sum(brightness_list)/n

# light sensor
analog_value = machine.ADC(27)

# measuring background brightness
print("measuring")
background = get_background(15)
print(f"background brightness: {background}")