# Bluetooth Manager Troubleshooting Guide

## Overview
After converting from dbus-fast to bleak, the API uses `BleakScanner.discover()` for device discovery and `BleakClient` for pairing/connecting. The code correctly iterates over `devices.values()` since bleak returns a dict when `return_adv=True` is set.

## Potential Issues

### 1. No Bluetooth Devices in Range
**Symptom**: Discovery returns `{"status": "discovery started", "devices_found": 0}`

**Check**:
- Ensure Bluetooth devices are powered on and in discoverable mode
- Devices should be within ~10 meters of the Bluetooth adapter
- Some devices only advertise when actively connecting (e.g., headphones in pairing mode)

**Debug**:
```bash
# Run discovery on the host machine to verify adapter works
bluetoothctl scan on
```

### 2. Bluetooth Adapter Not Available
**Symptom**: Discovery fails with D-Bus connection error

**Check**:
- The `bluetooth-host` container needs access to a real Bluetooth adapter
- The container uses `network_mode: host` to access system hardware directly

**Verify**:
```bash
# Check if hci0 adapter exists
hciconfig -a
```

### 3. D-Bus Socket Not Properly Shared
**Symptom**: No error but discovery returns empty or devices not found

**Check**: The `bluetooth-dbus` named volume is mounted in both containers:
- `bluetooth-host`: `/var/run/dbus` ← creates the socket
- `bluetooth-manager`: `/var/run/dbus` ← connects via `DBUS_SYSTEM_BUS_ADDRESS`

**Verify**:
```bash
# Check socket exists in container
docker exec <bluetooth-host> ls -la /var/run/dbus/
docker exec <bluetooth-manager> ls -la /var/run/dbus/

# Check environment variable
docker exec <bluetooth-manager> env | grep DBUS
```

### 4. Container Startup Timing
**Symptom**: Intermittent failures, works after restart

**Check**: The `depends_on: condition: service_started` ensures bluetooth-host starts first, but the BlueZ daemon may need additional time.

**Solution**: Consider adding a health check or startup delay to bluetooth-host.

### 5. Device Pairing/Connection Timeouts
**Symptom**: `connect/pair` endpoints timeout or fail

**Check**:
- Classic Bluetooth audio devices (A2DP/HFP) may not fully support bleak's GATT-based approach
- Some devices require specific PIN entries or passkey confirmation

## Debug Commands

```bash
# Get debug info
curl -X POST https://nam-box.local/api/bluetooth-manager/discovery/start
curl https://nam-box.local/api/bluetooth-manager/debug

# Check container logs
docker logs nam-box-bluetooth-host
docker logs nam-box-bluetooth-manager
```

## Known Limitations

### Mock Bluetooth API (Development)
The `bluetooth-mock` service provides a simulated REST API that mimics the `bleak-api.py` endpoints. This allows development and testing without real Bluetooth hardware:

**Mock Service Endpoints:**
- `POST /scan` - Returns simulated devices (headphones, watch, sensor)
- `POST /connect` - Simulates connection without hardware
- `GET /services/{address}` - Returns mock GATT services
- `POST /characteristics/{address}/{uuid}` - Simulates read/write operations
- All other endpoints follow the same pattern with simulated responses

To use the mock in development, update your docker-compose to reference the mock service instead of bluetooth-host.