# ctrl_transfer( bmRequestType, bmRequest, wValue, wIndex, nBytes)
import struct
from struct import *
import usb.core
import usb.util
# import usb.control
import sys
 
Aillio = {
    'vendor':0x483,
    'product':0xa27e,
    'configuration':0x1,
    'interface':0x1,
    'debug':0x1,
    'write_endpoint':0x3,
    'read_endpoint':0x81,
    'commands':{
        'info_1':[0x30, 0x02],
        'info_2':[0x89, 0x01],
        'status_1': [0x30, 0x01],
        'status_2': [0x30, 0x03],
        'prs_button': [0x30, 0x01, 0x00, 0x00],
        'heater_increase': [0x34, 0x01, 0xaa, 0xaa],
        'heater_decrease': [0x34, 0x02, 0xaa, 0xaa],
        'fan_increase': [0x31, 0x01, 0xaa, 0xaa],
        'fan_decrease': [0x31, 0x02, 0xaa, 0xaa],
    },
    'state':{
        'off': 0x00,
        'preheating': 0x02,
        'charge': 0x04,
        'roasting': 0x06,
        'cooling': 0x08,
        'shutdown': 0x09,
        0: 'off',
        2: 'preheating',
        4: 'charge',
        6: 'roasting',
        8: 'cooling',
        9: 'shutdown',
    },
}



test_data_1 = '4c:20:07:00:ff:ff:ff:dd:00:00:00:00:84:79:04:00:20:18:01:00:01:f4:00:00:07:93:00:00:00:00:42:00:02:00:df:00'

# def register_device(): 
dev = usb.core.find(idVendor=Aillio['vendor'], idProduct=Aillio['product'])
if dev is None:
    raise ValueError('Device not found')
    # return dev

# detach roaster if it is currently held by another process (from https://github.com/pyusb/pyusb/issues/76#issuecomment-118460796)
# there is probably a cleaner way to do this, and this seems to fail occasionally. 
for cfg in dev:
  for intf in cfg:
    if dev.is_kernel_driver_active(intf.bInterfaceNumber):
      try:
        dev.detach_kernel_driver(intf.bInterfaceNumber)
      except usb.core.USBError as e:
        sys.exit("Could not detatch kernel driver from interface({0}): {1}".format(intf.bInterfaceNumber, str(e)))
 
# set the active configuration. With no arguments, the first
# configuration will be the active one
dev.set_configuration(configuration=0x1)
 
usb.util.claim_interface(dev, 0x1)

def send(command):
    dev.write(Aillio['write_endpoint'], command)

def receive(length=32):
    '''
    length is either 32 or 64 (or maybe 36?)
    '''
    received_data = dev.read(Aillio['read_endpoint'], length)

    return received_data

## Formatting conversion from binary: 
## Data Schema:
## Status_1 returns 64 bytes:
## 
## Status_2 returns 64 bytes:
## Serial_Number: 
# convert_struct = struct.Struct('6f*p')

def convert_data(received_data, data_type):
    # import pickle
    # unpickled_data = pickle.loads(received_data)
    # converted = unpickled_data
    if data_type == 'serial_number':
        converted = unpack('h', received_data[0:2])[0]
    elif data_type == 'firmware':
        converted = unpack('h', received_data[24:26])[0]
    elif data_type == 'batches':
        converted = unpack('>I', received_data[27:31])[0]
    elif data_type == 'bean_temp':
        converted = round(unpack('f', received_data[0:4])[0], 1)
    elif data_type == 'roaster_status':
        converted = {
            'bean_temp': round(unpack('f', received_data[0:4])[0], 1),
            'bt_ror': round(unpack('f', received_data[4:8])[0], 1),
            'delta_t': round(unpack('f', received_data[8:12])[0], 1),
            'ext_t': round(unpack('f', received_data[16:20])[0], 1),
            'roast_minutes': received_data[24],
            'roast_seconds': received_data[25],
            'fan_level': received_data[26],
            'heater_level': received_data[27],
            'drum_speed_level': received_data[28],
            'roaster_state': Aillio['state'][received_data[29]],
            'ir_bt': round(unpack('f', received_data[32:36])[0], 1),
            'pcb_temp': round(unpack('f', received_data[36:40])[0], 1),
            'fan_speed': unpack('h', received_data[44:46])[0],
            'voltage': unpack('h', received_data[48:50])[0],
            'coil_fan_1_rpm': round(unpack('i', received_data[52:56])[0], 1),
            'coil_fan_2_rpm': round(unpack('i', received_data[96:100])[0], 1),
            'preheat_temp': unpack('h', received_data[40:42])[0],
        }
    return converted

send(Aillio['commands']['info_1'])
reply = receive()
# print(f"Info_1: {reply}")
print(f"Serial_number: {convert_data(reply, 'serial_number')}")
print(f"Firmware_version: {convert_data(reply, 'firmware')}")

send(Aillio['commands']['info_2'])
reply = receive(36)
# print(f"Info_2: {reply}")
print(f"Batches: {convert_data(reply, 'batches')}")

send(Aillio['commands']['status_1'])
reply1 = receive(64)
send(Aillio['commands']['status_2'])
reply2 = receive(64)
reply = reply1 + reply2 

# print(f"Reply1: {reply1[0]}")
# print(b'Reply1')
# print(f"Reply2: {reply2[0]}")
# print(f"Convert Reply1: {convert_struct.unpack(reply1)}")
# print(f"Convert Reply2: {convert_struct.unpack(reply2)}")


print(convert_data(reply, 'roaster_status'))