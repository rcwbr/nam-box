# Bluetooth Manager API

A FastAPI service for managing Bluetooth devices via BlueZ D-Bus interface.

## Endpoints

### GET /devices
List discovered Bluetooth devices.

**Response:**
```json
[
  {
    "address": "4C:61:5D:CC:27:12",
    "name": "4C-61-5D-CC-27-12",
    "paired": false,
    "connected": false,
    "trusted": false,
    "rssi": -64,
    "address_type": "random",
    "tx_power": 0,
    "uuids": [],
    "manufacturer_data": {
      "76": "100536..."
    }
  }
]
```

Note: During discovery, `name` defaults to the Alias property (which is typically the MAC address with dashes). The actual device name becomes available after connecting or after name resolution completes.

`address_type` of "random" indicates the device uses privacy-enabled resolvable private addresses (common for modern devices like phones, mice). "public" indicates a fixed MAC address.

**UUID-based Device Identification:**
The `uuids` field can be used to identify device types:
- `0000110d-...` - Headphones/A2DP (audio devices)
- `00001124-...` - Human Interface Device (mice, keyboards)
- `0000180d-...` - Heart Rate (fitness devices)
- `0000180f-...` - Battery service

Note: UUIDs are typically empty during discovery and populate after connecting to the device.

**Common Manufacturer IDs:**
- 76: Apple (iPhone, AirPods, etc.)
- 15: Broadcom
- 101: Nokia
- 117: Samsung
- 210: Huawei

### POST /discovery/start
Start Bluetooth device discovery (inquiry scan).

**Response:**
```json
{"status": "discovery started"}
```

### POST /discovery/stop
Stop Bluetooth device discovery.

**Response:**
```json
{"status": "discovery stopped"}
```

### POST /pair
Initiate pairing with a device.

**Request Body:**
```json
{"address": "72:5E:1A:9E:B1:DB"}
```

**Response:**
```json
{"address": "72:5E:1A:9E:B1:DB", "status": "pairing initiated"}
```

### POST /connect/{address}
Connect to a paired device.

**Response:**
```json
{"address": "72:5E:1A:9E:B1:DB", "status": "connected"}
```

### GET /debug
Debug endpoint showing raw D-Bus data and first device's properties.

## Device Properties

- `address`: MAC address of the device
- `name`: Device name (defaults to Alias property during discovery, typically MAC address with dashes)
- `paired`: Whether device is paired
- `connected`: Whether device is currently connected
- `trusted`: Whether device is marked as trusted
- `rssi`: Signal strength in dBm (available during discovery)
- `address_type`: "public" or "random" - indicates if device uses privacy-enabled addressing
- `tx_power`: Transmitted power level at the device (0 if not available)
- `uuids`: List of service UUIDs advertised by the device (typically empty during discovery until connected)
- `manufacturer_data`: Dictionary of manufacturer IDs to data (e.g., `{76: "1005..."}` for Apple devices). This allows vendor identification without connecting.

## Architecture

### Container Setup

The service runs in a Docker container with access to the host's D-Bus socket:

```yaml
services:
  bluetooth-manager:
    image: ghcr.io/rcwbr/nam-box-bluetooth-manager:local
    ports:
      - "8000:8000"
    volumes:
      - bluetooth-dbus:/var/run/dbus
    environment:
      - DBUS_SYSTEM_BUS_ADDRESS=unix:path=/var/run/dbus/system_bus_socket
    depends_on:
      bluetooth-host:
        condition: service_started
```

### D-Bus Integration

The manager communicates with BlueZ via the system D-Bus using `dbus_fast`:

1. **Startup Connection**: On startup, connects to `BusType.SYSTEM` and introspects `/org/bluez/hci0` to get the Adapter1 interface

2. **service → bluetooth-host → BlueZ Flow**:
   - `bluetooth-manager` container accesses `/var/run/dbus/system_bus_socket`
   - This socket is mounted from `bluetooth-host` container
   - `bluetooth-host` runs on the host network with NET_ADMIN capability
   - BlueZ daemon on the host receives D-Bus method calls

3. **D-Bus Interfaces Used**:
   - `org.bluez.Adapter1` - Adapter control (StartDiscovery, StopDiscovery)
   - `org.bluez.Device1` - Device operations (Pair, Connect)
   - `org.freedesktop.DBus.ObjectManager` - Query managed objects

4. **Device Discovery Flow**:
   ```
   StartDiscovery → BlueZ performs inquiry → Devices appear in GetManagedObjects → StopDiscovery
   ```

## Troubleshooting

### Device shows name "Unknown"
This is normal during discovery. BlueZ resolves names asynchronously. The name becomes available after:
1. Connecting to the device
2. Waiting for name resolution timeout (typically 10-30 seconds)
3. Using `Alias` property instead of `Name`

### Empty device list
1. Start discovery first: `POST /discovery/start`
2. Wait ~10 seconds for devices to appear
3. Stop discovery when done: `POST /discovery/stop`