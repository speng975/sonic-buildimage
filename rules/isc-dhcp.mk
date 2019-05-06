# isc-dhcp packages

ISC_DHCP_VERSION = 4.3.5-3.1

export ISC_DHCP_VERSION

ISC_DHCP_COMMON = isc-dhcp-common_$(ISC_DHCP_VERSION)_amd64.deb
$(ISC_DHCP_COMMON)_SRC_PATH = $(SRC_PATH)/isc-dhcp
SONIC_MAKE_DEBS += $(ISC_DHCP_COMMON)

ISC_DHCP_RELAY = isc-dhcp-relay_$(ISC_DHCP_VERSION)_amd64.deb
$(eval $(call add_derived_package,$(ISC_DHCP_COMMON),$(ISC_DHCP_RELAY)))

SONIC_STRETCH_DEBS += $(ISC_DHCP_COMMON) $(ISC_DHCP_RELAY)
