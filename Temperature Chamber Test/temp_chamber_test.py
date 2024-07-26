import pyvisa

# Create a resource manager
rm = pyvisa.ResourceManager()

# List available resources
resources = rm.list_resources()
print('Available resources:', resources)