"""OpenAL Soft output through cyal. Playback is added in step 3 of the plan. For now this opens and checks the device."""
import cyal


def open_device():
    """Opens the default OpenAL device and a current context. Raises if the library isn't OpenAL Soft."""
    device = cyal.Device()
    if 'OpenAL Soft' not in device.name:
        raise RuntimeError('OpenAL Soft is required, found: %s' % device.name)
    context = cyal.Context(device, make_current=True)
    return device, context
