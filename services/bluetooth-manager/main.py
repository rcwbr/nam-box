from typing import Optional, Tuple

from dbus_fast.aio import MessageBus
from dbus_fast.constants import BusType
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

app = FastAPI(title="Bluetooth Manager API", debug=False)

@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    """Ensure all unhandled exceptions return JSON."""
    # Skip HTTPException - let FastAPI handle those normally
    if isinstance(exc, HTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail}
        )
    import traceback
    print(f"Unhandled exception: {exc}")
    traceback.print_exc()
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "error": str(exc)}
    )

BLUEZ_SERVICE = "org.bluez"
ADAPTER_INTERFACE = "org.bluez.Adapter1"
DEVICE_INTERFACE = "org.bluez.Device1"
OBJECT_MANAGER_INTERFACE = "org.freedesktop.DBus.ObjectManager"

# Common Bluetooth service UUIDs for device type identification
DEVICE_TYPE_UUIDS = {
    # Audio devices
    "0000110b-0000-1000-8000-00805f9b34fb": "Headset",
    "0000110d-0000-1000-8000-00805f9b34fb": "Headphones/A2DP",
    "0000110e-0000-1000-8000-00805f9b34fb": "Hands-Free",
    "0000111e-0000-1000-8000-00805f9b34fb": "HFP AG",
    # Input devices
    "00001124-0000-1000-8000-00805f9b34fb": "Human Interface Device (HID)",
    "00001812-0000-1000-8000-00805f9b34fb": "HID Service",
    # Health/fitness
    "0000180d-0000-1000-8000-00805f9b34fb": "Heart Rate",
    "0000180f-0000-1000-8000-00805f9b34fb": "Battery",
    # Generic
    "00001800-0000-1000-8000-00805f9b34fb": "Generic Access",
    "00001801-0000-1000-8000-00805f9b34fb": "Generic Attribute",
}

# Bluetooth SIG assigned company identifiers
MANUFACTURER_IDS = {
    76: "Apple",  # 0x004C
    117: "BlackBerry",  # 0x0075
    128: "Microsoft",  # 0x0080
    224: "Sony",  # 0x00E0
    512: "Samsung",  # 0x0200
    735: "Garmin",  # 0x02E3
    895: "Polar",  # 0x037F
    1037: "Bose",  # 0x040D
    1174: "JBL",  # 0x0496
    1520: "Google",  # 0x05F0
    2005: "Fitbit",  # 0x07D5
}


class BluetoothDevice(BaseModel):
    address: str
    name: str
    paired: bool
    connected: bool
    trusted: bool
    rssi: Optional[int] = None
    address_type: Optional[str] = None
    tx_power: Optional[int] = None
    uuids: list[str] = []
    manufacturer_data: dict = {}
    device_types: list[str] = []
    manufacturer: Optional[str] = None


class PairRequest(BaseModel):
    address: str
    pin: Optional[str] = None


class BluetoothManager:
    def __init__(self):
        self.bus: Optional[MessageBus] = None
        self.adapter_path = "/org/bluez/hci0"

    async def connect(self):
        self.bus = await MessageBus(bus_type=BusType.SYSTEM).connect()
        introspection = await self.bus.introspect(BLUEZ_SERVICE, self.adapter_path)
        self.adapter = self.bus.get_proxy_object(
            BLUEZ_SERVICE, self.adapter_path, introspection
        )
        self.adapter_interface = self.adapter.get_interface(ADAPTER_INTERFACE)

    async def get_devices(self) -> list[BluetoothDevice]:
        if not self.bus:
            raise HTTPException(status_code=503, detail="Not connected to D-Bus")

        introspection = await self.bus.introspect(BLUEZ_SERVICE, "/")
        object_manager = self.bus.get_proxy_object(
            BLUEZ_SERVICE, "/", introspection
        ).get_interface(OBJECT_MANAGER_INTERFACE)

        objects = await object_manager.call_get_managed_objects()

        devices = []
        for path, interfaces in objects.items():
            if DEVICE_INTERFACE in interfaces:
                try:
                    device_props = interfaces[DEVICE_INTERFACE]
                    # Use Alias as fallback when Name is not set (during discovery)
                    name = self._get_property(device_props, "Name")
                    if not name:
                        name = self._get_property(device_props, "Alias", "Unknown")
                    uuids = self._get_property(device_props, "UUIDs", [])
                    if uuids is None:
                        uuids = []
                    # UUIDs may be variants - convert to strings
                    uuids = [str(u) if hasattr(u, "value") else str(u) for u in uuids]
                    manufacturer_data = self._get_property(device_props, "ManufacturerData", {})
                    if manufacturer_data is None:
                        manufacturer_data = {}
                    # Convert bytes in manufacturer data to hex strings for JSON serialization
                    processed_manufacturer_data = {}
                    for k, v in manufacturer_data.items():
                        if hasattr(v, "value"):
                            val = v.value
                        else:
                            val = v
                        if isinstance(val, bytes):
                            processed_manufacturer_data[str(k)] = val.hex()
                        else:
                            processed_manufacturer_data[str(k)] = val
                    # Identify device types and manufacturer
                    device_types, manufacturer = self._identify_device_info(uuids, processed_manufacturer_data)
                    devices.append(BluetoothDevice(
                        address=self._get_property(device_props, "Address", "unknown"),
                        name=name,
                        paired=self._get_property(device_props, "Paired", False),
                        connected=self._get_property(device_props, "Connected", False),
                        trusted=self._get_property(device_props, "Trusted", False),
                        rssi=self._get_property(device_props, "RSSI"),
                        address_type=self._get_property(device_props, "AddressType"),
                        tx_power=self._get_property(device_props, "TxPower"),
                        uuids=uuids,
                        manufacturer_data=processed_manufacturer_data,
                        device_types=device_types,
                        manufacturer=manufacturer,
                    ))
                except Exception as e:
                    print(f"Error processing device {path}: {e}")
                    continue

        return devices

    def _get_property(self, props: dict, key: str, default=None):
        """Extract property value, handling variant types."""
        val = props.get(key, default)
        if val is None:
            return default
        if hasattr(val, "value"):
            return val.value
        return val

    def _identify_device_info(self, uuids: list[str], manufacturer_data: dict) -> Tuple[list[str], Optional[str]]:
        """Identify device types and manufacturer from service UUIDs and manufacturer data."""
        device_types = []
        manufacturer = None

        # Get manufacturer from first key in manufacturer_data
        if manufacturer_data:
            for mid in manufacturer_data.keys():
                mid_int = int(mid)
                # Handle signed int16 (negative values)
                if mid_int < 0:
                    mid_int = mid_int + 65536
                manufacturer = MANUFACTURER_IDS.get(mid_int, f"Unknown (ID: {mid_int})")
                break

        # Identify from UUIDs
        for uuid in uuids:
            if uuid.lower() in DEVICE_TYPE_UUIDS:
                device_types.append(DEVICE_TYPE_UUIDS[uuid.lower()])

        # Apple manufacturer data parsing (ID 0x004C = 76)
        if "76" in manufacturer_data:
            apple_data_hex = manufacturer_data.get("76")
            if apple_data_hex:
                device_types.extend(self._parse_apple_nearby_info(apple_data_hex))

        return list(set(device_types)), manufacturer

    def _parse_apple_nearby_info(self, data_hex: str) -> list[str]:
        """Parse Apple Nearby accessory type from manufacturer data."""
        device_types = []
        try:
            data = bytes.fromhex(data_hex)
            if len(data) >= 3:
                nearby_type = data[2] if len(data) > 2 else 0
                nearby_types = {
                    0x00: "AirPods",
                    0x01: "AirPods Pro",
                    0x02: "AirPods Max",
                    0x05: "Apple Watch",
                    0x07: "Apple Watch Series 3",
                    0x09: "Apple Watch Series 4",
                    0x0A: "Apple Watch Series 5+",
                    0x0C: "Apple Watch SE",
                    0x10: "MacBook",
                    0x11: "MacBook Pro",
                    0x12: "MacBook Air",
                    0x13: "iMac",
                    0x14: "Mac mini",
                    0x15: "Mac Studio",
                    0x20: "iPad",
                    0x21: "iPad Pro",
                    0x22: "iPad Air",
                    0x23: "iPad mini",
                    0x40: "iPhone",
                    0x41: "iPhone Pro",
                    0x42: "iPhone Pro Max",
                    0x43: "iPhone mini",
                    0x50: "Apple Pencil",
                }
                if nearby_type in nearby_types:
                    device_types.append(nearby_types[nearby_type])
        except (ValueError, IndexError):
            pass
        return device_types

    async def get_debug_info(self) -> dict:
        """Debug endpoint to see raw D-Bus data."""
        if not self.bus:
            raise HTTPException(status_code=503, detail="Not connected to D-Bus")

        introspection = await self.bus.introspect(BLUEZ_SERVICE, "/")
        object_manager = self.bus.get_proxy_object(
            BLUEZ_SERVICE, "/", introspection
        ).get_interface(OBJECT_MANAGER_INTERFACE)

        objects = await object_manager.call_get_managed_objects()

        first_device = None
        for path, interfaces in objects.items():
            if DEVICE_INTERFACE in interfaces:
                first_device = {
                    "path": path,
                    "properties": {k: str(v) if hasattr(v, "value") else v for k, v in interfaces[DEVICE_INTERFACE].items()},
                }
                break

        return {
            "total_objects": len(objects),
            "paths": list(objects.keys()),
            "interfaces_per_path": {p: list(i.keys()) for p, i in objects.items()},
            "first_device_raw": first_device,
        }

    async def start_discovery(self) -> dict:
        if not self.bus:
            raise HTTPException(status_code=503, detail="Not connected to D-Bus")
        try:
            await self.adapter_interface.call_start_discovery()
            return {"status": "discovery started"}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Discovery failed: {str(e)}")

    async def stop_discovery(self) -> dict:
        if not self.bus:
            raise HTTPException(status_code=503, detail="Not connected to D-Bus")
        try:
            await self.adapter_interface.call_stop_discovery()
            return {"status": "discovery stopped"}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Stop discovery failed: {str(e)}")

    async def get_device_path(self, address: str) -> str:
        """Find device D-Bus path by address."""
        introspection = await self.bus.introspect(BLUEZ_SERVICE, "/")
        object_manager = self.bus.get_proxy_object(
            BLUEZ_SERVICE, "/", introspection
        ).get_interface(OBJECT_MANAGER_INTERFACE)
        objects = await object_manager.call_get_managed_objects()

        for path, interfaces in objects.items():
            if DEVICE_INTERFACE in interfaces:
                device_addr = self._get_property(interfaces[DEVICE_INTERFACE], "Address")
                if device_addr and device_addr.lower() == address.lower():
                    return path
        return None

    async def pair_device(self, address: str) -> dict:
        if not self.bus:
            raise HTTPException(status_code=503, detail="Not connected to D-Bus")

        device_path = await self.get_device_path(address)
        if not device_path:
            raise HTTPException(status_code=404, detail=f"Device {address} not found")

        try:
            device_introspection = await self.bus.introspect(BLUEZ_SERVICE, device_path)
            device_obj = self.bus.get_proxy_object(BLUEZ_SERVICE, device_path, device_introspection)
            device = device_obj.get_interface(DEVICE_INTERFACE)
            await device.call_pair()
            return {"address": address, "status": "pairing initiated"}
        except HTTPException:
            raise
        except Exception as e:
            import traceback
            print(f"Pairing error for {address} at {device_path}: {e}")
            traceback.print_exc()
            raise HTTPException(status_code=500, detail=f"Pairing failed: {str(e)}")

    async def connect_device(self, address: str) -> dict:
        if not self.bus:
            raise HTTPException(status_code=503, detail="Not connected to D-Bus")

        device_path = await self.get_device_path(address)
        if not device_path:
            raise HTTPException(status_code=404, detail=f"Device {address} not found")

        device_introspection = await self.bus.introspect(BLUEZ_SERVICE, device_path)
        device = self.bus.get_proxy_object(
            BLUEZ_SERVICE, device_path, device_introspection
        ).get_interface(DEVICE_INTERFACE)

        try:
            await device.call_connect()
            return {"address": address, "status": "connected"}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Connection failed: {str(e)}")


manager = BluetoothManager()


@app.on_event("startup")
async def startup_event():
    await manager.connect()


@app.get("/devices", response_model=list[BluetoothDevice])
async def list_devices():
    return await manager.get_devices()


@app.get("/debug")
async def debug_info():
    return await manager.get_debug_info()


@app.post("/discovery/start")
async def start_discovery():
    return await manager.start_discovery()


@app.post("/discovery/stop")
async def stop_discovery():
    return await manager.stop_discovery()


@app.post("/pair")
async def pair_device(request: PairRequest):
    return await manager.pair_device(request.address)


@app.post("/connect/{address}")
async def connect_device(address: str):
    return await manager.connect_device(address)