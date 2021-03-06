# sfputil.py
#
# Platform-specific SFP transceiver interface for SONiC
#

try:
    import struct
    import sys
    import getopt
    import time
    from sonic_sfp.sfputilbase import SfpUtilBase
    from os import *
    from mmap import *

except ImportError as e:
    raise ImportError("%s - required module not found" % str(e))


class SfpUtil(SfpUtilBase):
    """Platform-specific SfpUtil class"""

    PORT_START = 0
    PORT_END = 63
    PORTS_IN_BLOCK = 32

    BASE_RES_PATH = "/sys/bus/pci/devices/0000:04:00.0/resource0"

    _port_to_eeprom_mapping = {}

    _global_port_pres_dict = {}

    @property
    def port_start(self):
        return self.PORT_START

    @property
    def port_end(self):
        return self.PORT_END

    @property
    def qsfp_ports(self):
        return range(0, self.PORTS_IN_BLOCK + 1)

    @property
    def port_to_eeprom_mapping(self):
        return self._port_to_eeprom_mapping

    def pci_mem_read(self, mm, offset):
        mm.seek(offset)
        read_data_stream=mm.read(4)
        reg_val=struct.unpack('I',read_data_stream)
        mem_val = str(reg_val)[1:-2]
        # print "reg_val read:%x"%reg_val
        return mem_val

    def pci_mem_write(self, mm, offset, data):
        mm.seek(offset)
        # print "data to write:%x"%data
        mm.write(struct.pack('I',data))

    def pci_set_value(self, resource, val, offset):
        fd = open(resource, O_RDWR)
        mm = mmap(fd, 0)
        val = self.pci_mem_write(mm, offset, val)
        mm.close()
        close(fd)
        return val

    def pci_get_value(self, resource, offset):
        fd = open(resource, O_RDWR)
        mm = mmap(fd, 0)
        val = self.pci_mem_read(mm, offset)
        mm.close()
        close(fd)
        return val
	
    def init_global_port_presence(self):
        for port_num in range(self.port_start, (self.port_end + 1)):
            presence = self.get_presence(port_num)
            if(presence):
                self._global_port_pres_dict[port_num] = '1'
            else:
                self._global_port_pres_dict[port_num] = '0'
 
    def __init__(self):
        eeprom_path = "/sys/class/i2c-adapter/i2c-{0}/{0}-0050/eeprom"

        for x in range(0, self.port_end + 1):
            port_num  = x + 2
            self.port_to_eeprom_mapping[x] = eeprom_path.format(
                        port_num)
            port_num = 0
        self.init_global_port_presence()
        
        SfpUtilBase.__init__(self)

    def get_presence(self, port_num):
        # Check for invalid port_num
        if port_num < self.port_start or port_num > self.port_end:
            return False

        # Port offset starts with 0x4004
	port_offset = 16388 + ((port_num) * 16)

	status = self.pci_get_value(self.BASE_RES_PATH, port_offset)
	reg_value = int(status)
        
        # Absence of status throws error
        if (reg_value == "" ):
            return False

        # Mask off 4th bit for presence
        mask = (1 << 4)

        # ModPrsL is active low
        if reg_value & mask == 0:
            return True

        return False

    def get_low_power_mode(self, port_num):

        # Check for invalid port_num
        if port_num < self.port_start or port_num > self.port_end:
            return False

	# Port offset starts with 0x4000
	port_offset = 16384 + ((port_num) * 16)

	status = self.pci_get_value(self.BASE_RES_PATH, port_offset)
	reg_value = int(status)

        # Absence of status throws error
        if (reg_value == "" ):
            return False

        # Mask off 4th bit for presence
        mask = (1 << 6)

        # LPMode is active high
        if reg_value & mask == 0:
            return False

        return True

    def set_low_power_mode(self, port_num, lpmode):

        # Check for invalid port_num
        if port_num < self.port_start or port_num > self.port_end:
            return False

	# Port offset starts with 0x4000
	port_offset = 16384 + ((port_num) * 16)

	status = self.pci_get_value(self.BASE_RES_PATH, port_offset)
	reg_value = int(status)

        # Absence of status throws error
        if (reg_value == "" ):
            return False

        # Mask off 4th bit for presence
        mask = (1 << 6)
		
	# LPMode is active high; set or clear the bit accordingly
        if lpmode is True:
            reg_value = reg_value | mask
        else:
            reg_value = reg_value & ~mask

        # Convert our register value back to a hex string and write back
	status = self.pci_set_value(self.BASE_RES_PATH, reg_value, port_offset)

        return True

    def reset(self, port_num):

	# Check for invalid port_num
        if port_num < self.port_start or port_num > self.port_end:
            return False

	# Port offset starts with 0x4000
	port_offset = 16384 + ((port_num) * 16)

	status = self.pci_get_value(self.BASE_RES_PATH, port_offset)
	reg_value = int(status)

        # Absence of status throws error
        if (reg_value == "" ):
            return False

        # Mask off 4th bit for presence
        mask = (1 << 6)

        # ResetL is active low
        reg_value = reg_value & ~mask

	# Convert our register value back to a hex string and write back
	status = self.pci_set_value(self.BASE_RES_PATH, reg_value, port_offset)

        # Sleep 1 second to allow it to settle
        time.sleep(1)

        reg_value = reg_value | mask

	# Convert our register value back to a hex string and write back
	status = self.pci_set_value(self.BASE_RES_PATH, reg_value, port_offset)

        return True

    def get_transceiver_change_event(self):
        port_dict = {}
        while True:
            for port_num in range(self.port_start, (self.port_end + 1)):
                presence = self.get_presence(port_num)
                if(presence and self._global_port_pres_dict[port_num] == '0'):
                    self._global_port_pres_dict[port_num] = '1'
                    port_dict[port_num] = '1'
                elif(not presence and
                     self._global_port_pres_dict[port_num] == '1'):
                    self._global_port_pres_dict[port_num] = '0'
                    port_dict[port_num] = '0'

                if(len(port_dict) > 0):
                    return True, port_dict

            time.sleep(0.5)
