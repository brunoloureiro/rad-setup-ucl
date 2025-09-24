from attrs import (
	frozen,
)

@frozen
class PowerStats:
	powered: bool
	voltage: float
	current: float
	constant_current: bool
	constant_voltage: bool
	voltage_protection: bool
	current_protection: bool
	power_protection: bool
	temperature_protection: bool
	remote_control_active: bool

	@classmethod
	def from_dict(cls, data):
		remote_control_active = data['remote']
		powered = data['on']
		constant_current = data['CC']
		constant_voltage = not data['CC']
		voltage_protection = data['OVP']
		current_protection = data['OCP']
		power_protection = data['OPP']
		temperature_protection = data['OTP']
		voltage = data['v']
		current = data['i']

		return cls(
			powered = powered,
			voltage = voltage,
			current = current,
			constant_current = constant_current,
			constant_voltage = constant_voltage,
			voltage_protection = voltage_protection,
			current_protection = current_protection,
			power_protection = power_protection,
			temperature_protection = temperature_protection,
			remote_control_active = remote_control_active,
		)