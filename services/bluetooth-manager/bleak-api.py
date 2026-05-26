"""
Bluetooth LE REST API using FastAPI and Bleak

This API exposes key bleak operations through REST endpoints:
- Scan/Discovery: POST /scan
- Find device: POST /find
- Connect: POST /connect
- Disconnect: POST /disconnect/{address}
- Services: GET /services/{address}
- Read/Write characteristics: GET/POST /characteristics/{address}/{uuid}
- Notifications: POST /notifications/{address}/{uuid}/start|stop
- Status: GET /status/{address}
"""

from typing import Optional

from bleak import BleakClient, BleakScanner, BLEDevice
from bleak.uuids import uuidstr_to_str
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

app = FastAPI(title="Bluetooth LE API", debug=False)


# @app.exception_handler(Exception)
# async def generic_exception_handler(request: Request, exc: Exception):
#     """Ensure all unhandled exceptions return JSON."""
#     if isinstance(exc, HTTPException):
#         return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})
#     import traceback

#     print(f"Unhandled exception: {exc}")
#     traceback.print_exc()
#     return JSONResponse(
#         status_code=500, content={"detail": "Internal server error", "error": str(exc)}
#     )


class DeviceInfo(BaseModel):
    """Information about a Bluetooth device from discovery."""

    address: str
    name: Optional[str] = None
    rssi: Optional[int] = None
    tx_power: Optional[int] = None
    service_uuids: list[str] = []
    service_data: dict = {}
    manufacturer_data: dict = {}
    service_names: list[str] = []


class ScanRequest(BaseModel):
    """Request parameters for device discovery."""

    timeout: float = 5.0
    service_uuids: Optional[list[str]] = None


class ConnectRequest(BaseModel):
    """Request parameters for connecting to a device."""

    address: str
    timeout: float = 30.0


# class WriteRequest(BaseModel):
#     """Request parameters for writing to a characteristic."""

#     data: str
#     response: bool = True


class BluetoothManager:
    """Manages Bluetooth operations using Bleak."""

    def __init__(self):
        self._connected_clients: dict[str, BleakClient] = {}
        self._discovered_devices: dict[str, DeviceInfo] = {}

    async def scan(
        self, timeout: float = 5.0, service_uuids: Optional[list[str]] = None
    ) -> list[DeviceInfo]:
        """Scan for BLE devices using BleakScanner.discover()."""
        print(f"Starting discovery with timeout={timeout}s, services={service_uuids}")

        devices_data = await BleakScanner.discover(
            timeout=timeout, return_adv=True, service_uuids=service_uuids
        )

        devices = []
        for device, adv_data in devices_data.values():
            address = device.address.lower()
            manufacturer_data = {}
            if adv_data.manufacturer_data:
                for k, v in adv_data.manufacturer_data.items():
                    manufacturer_data[str(k)] = v.hex()

            service_data = {}
            if adv_data.service_data:
                for k, v in adv_data.service_data.items():
                    service_data[k] = v.hex()

            service_names: list[str] = []
            discovered_uuids: list[str] = []
            if adv_data.service_uuids:
                for uuid in adv_data.service_uuids:
                    uuid_str = str(uuid)
                    discovered_uuids.append(uuid_str)
                    name = uuidstr_to_str(uuid_str)
                    if name and name != "Unknown":
                        service_names.append(name)

            device_types = []
            if "76" in manufacturer_data:
                device_types.extend(
                    self._parse_apple_nearby_info(manufacturer_data["76"])
                )

            device_info = DeviceInfo(
                address=address,
                name=device.name or adv_data.local_name,
                rssi=adv_data.rssi,
                tx_power=adv_data.tx_power,
                service_uuids=discovered_uuids,
                service_data=service_data,
                manufacturer_data=manufacturer_data,
                service_names=service_names + device_types,
            )
            self._discovered_devices[address] = device_info
            devices.append(device_info)

        print(f"Discovery returned {len(devices)} devices")
        return devices

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

    async def find_device(
        self, address: Optional[str] = None, name: Optional[str] = None
    ) -> Optional[DeviceInfo]:
        """Find a device by address or name.

        Uses BleakScanner.find_device_by_address() or find_device_by_name().
        """
        if address:
            device = await BleakScanner.find_device_by_address(address)
        elif name:
            device = await BleakScanner.find_device_by_name(name)
        else:
            raise HTTPException(
                status_code=400, detail="Either address or name must be provided"
            )

        if device is None:
            return None

        return DeviceInfo(
            address=device.address.lower(),
            name=device.name,
            rssi=None,
            service_names=[],
        )

    async def connect(
        self, address: str, timeout: float = 30.0
    ) -> dict:
        """Connect to a device using BleakClient.connect().

        Automatically attempts pairing if connection fails due to authentication
        requirements (common for encrypted characteristics).
        """
        address = address.lower()

        if address in self._connected_clients:
            client = self._connected_clients[address]
            if client.is_connected:
                return {"address": address, "status": "already connected"}
            else:
                del self._connected_clients[address]

        client = None
        try:
            device = await BleakScanner.find_device_by_address(address)
            client = BleakClient(device, pair=False, timeout=timeout)
            await client.connect()
            self._connected_clients[address] = client
            return {"address": address, "status": "connected", "paired": False}
        except Exception as e:
            client = BleakClient(device, pair=True, timeout=timeout)
            await client.connect()
            self._connected_clients[address] = client
            return {"address": address, "status": "connected", "paired": True}

    async def disconnect(self, address: str) -> dict:
        """Disconnect from a device using BleakClient.disconnect().

        Based on examples/service_explorer.py cleanup pattern.
        """
        address = address.lower()

        if address not in self._connected_clients:
            return {"address": address, "status": "not connected"}

        client = self._connected_clients[address]
        try:
            await client.disconnect()
        except Exception:
            pass
        del self._connected_clients[address]
        return {"address": address, "status": "disconnected"}

    # async def get_services(self, address: str) -> dict:
    #     """Get services for a connected device.

    #     Uses BleakClient.services to enumerate GATT services.
    #     Based on examples/service_explorer.py.
    #     """
    #     address = address.lower()

    #     if address not in self._connected_clients:
    #         raise HTTPException(status_code=404, detail="Device not connected")

    #     client = self._connected_clients[address]
    #     services = []
    #     for service in client.services:
    #         characteristics = []
    #         for char in service.characteristics:
    #             characteristics.append(
    #                 {
    #                     "uuid": str(char.uuid),
    #                     "properties": list(char.properties),
    #                     "description": str(char),
    #                 }
    #             )
    #         services.append(
    #             {
    #                 "uuid": str(service.uuid),
    #                 "description": str(service),
    #                 "characteristics": characteristics,
    #             }
    #         )

    #     return {
    #         "address": address,
    #         "name": client.name,
    #         "services": services,
    #     }

    # async def read_characteristic(self, address: str, uuid: str) -> dict:
    #     """Read from a characteristic using BleakClient.read_gatt_char().

    #     Based on examples/service_explorer.py read pattern.
    #     """
    #     address = address.lower()

    #     if address not in self._connected_clients:
    #         raise HTTPException(status_code=404, detail="Device not connected")

    #     client = self._connected_clients[address]
    #     try:
    #         value = await client.read_gatt_char(uuid)
    #         return {
    #             "address": address,
    #             "characteristic": uuid,
    #             "value": value.hex() if isinstance(value, bytes) else str(value),
    #         }
    #     except Exception as e:
    #         raise HTTPException(status_code=500, detail=f"Read failed: {str(e)}")

    # async def write_characteristic(
    #     self, address: str, uuid: str, data: str, response: bool = True
    # ) -> dict:
    #     """Write to a characteristic using BleakClient.write_gatt_char().

    #     Based on examples/uart_service.py write pattern.
    #     """
    #     address = address.lower()

    #     if address not in self._connected_clients:
    #         raise HTTPException(status_code=404, detail="Device not connected")

    #     client = self._connected_clients[address]
    #     try:
    #         await client.write_gatt_char(uuid, bytes.fromhex(data), response=response)
    #         return {
    #             "address": address,
    #             "characteristic": uuid,
    #             "status": "written",
    #         }
    #     except Exception as e:
    #         raise HTTPException(status_code=500, detail=f"Write failed: {str(e)}")

    # async def start_notifications(
    #     self, address: str, uuid: str, callback_url: Optional[str] = None
    # ) -> dict:
    #     """Start notifications on a characteristic.

    #     Uses BleakClient.start_notify().
    #     Based on examples/uart_service.py and examples/two_devices.py.
    #     """
    #     address = address.lower()

    #     if address not in self._connected_clients:
    #         raise HTTPException(status_code=404, detail="Device not connected")

    #     client = self._connected_clients[address]

    #     def notification_handler(characteristic, data):
    #         print(f"Notification from {address} - {uuid}: {data.hex()}")

    #     try:
    #         await client.start_notify(uuid, notification_handler)
    #         return {
    #             "address": address,
    #             "characteristic": uuid,
    #             "status": "notifications started",
    #         }
    #     except Exception as e:
    #         raise HTTPException(
    #             status_code=500, detail=f"Failed to start notifications: {str(e)}"
    #         )

    # async def stop_notifications(self, address: str, uuid: str) -> dict:
    #     """Stop notifications on a characteristic using BleakClient.stop_notify().

    #     Based on examples/uart_service.py.
    #     """
    #     address = address.lower()

    #     if address not in self._connected_clients:
    #         raise HTTPException(status_code=404, detail="Device not connected")

    #     client = self._connected_clients[address]
    #     try:
    #         await client.stop_notify(uuid)
    #         return {
    #             "address": address,
    #             "characteristic": uuid,
    #             "status": "notifications stopped",
    #         }
    #     except Exception as e:
    #         raise HTTPException(
    #             status_code=500, detail=f"Failed to stop notifications: {str(e)}"
    #         )

    # async def get_status(self, address: str) -> dict:
    #     """Get connection status for a device."""
    #     address = address.lower()

    #     if address in self._connected_clients:
    #         client = self._connected_clients[address]
    #         try:
    #             return {
    #                 "address": address,
    #                 "connected": client.is_connected,
    #                 "name": client.name,
    #                 "mtu": client.mtu_size,
    #             }
    #         except Exception:
    #             return {"address": address, "connected": False}
    #     return {"address": address, "connected": False}

    # async def get_debug_info(self) -> dict:
    #     """Get debug information about the manager state."""
    #     return {
    #         "discovered_devices_count": len(self._discovered_devices),
    #         "connected_devices": [
    #             {"address": addr, "connected": client.is_connected}
    #             for addr, client in self._connected_clients.items()
    #         ],
    #     }


manager = BluetoothManager()


@app.get("/devices", response_model=list[DeviceInfo])
async def list_devices():
    """List all discovered devices."""
    return list(manager._discovered_devices.values())


@app.post("/scan", response_model=list[DeviceInfo])
async def scan_devices(request: Optional[ScanRequest] = None):
    """Scan for BLE devices.

    Uses BleakScanner.discover().
    Based on examples/discover.py.
    """
    timeout = request.timeout if request else 5.0
    service_uuids = request.service_uuids if request else None
    return await manager.scan(timeout=timeout, service_uuids=service_uuids)


@app.post("/find", response_model=Optional[DeviceInfo])
async def find_device(address: Optional[str] = None, name: Optional[str] = None):
    """Find a device by address or name.

    Uses BleakScanner.find_device_by_address() or find_device_by_name().
    Based on examples/service_explorer.py and examples/disconnect_callback.py.
    """
    return await manager.find_device(address=address, name=name)


@app.post("/connect")
async def connect_device(request: ConnectRequest):
    """Connect to a device.

    Automatically pairs if authentication is required.
    Based on examples/service_explorer.py and examples/disconnect_callback.py.
    """
    return await manager.connect(
        address=request.address, timeout=request.timeout
    )


# @app.post("/disconnect/{address}")
# async def disconnect_device(address: str):
#     """Disconnect from a device.

#     Uses BleakClient.disconnect().
#     """
#     return await manager.disconnect(address)


# @app.get("/services/{address}")
# async def get_services(address: str):
#     """Get services, characteristics, and descriptors for a connected device.

#     Uses BleakClient.services to enumerate GATT services.
#     Based on examples/service_explorer.py.
#     """
#     return await manager.get_services(address)


# @app.get("/characteristics/{address}/{uuid}")
# async def read_characteristic(address: str, uuid: str):
#     """Read from a characteristic.

#     Uses BleakClient.read_gatt_char().
#     Based on examples/service_explorer.py.
#     """
#     return await manager.read_characteristic(address, uuid)


# @app.post("/characteristics/{address}/{uuid}")
# async def write_characteristic(address: str, uuid: str, request: WriteRequest):
#     """Write to a characteristic.

#     Uses BleakClient.write_gatt_char().
#     Based on examples/uart_service.py.
#     """
#     return await manager.write_characteristic(
#         address, uuid, request.data, request.response
#     )


# @app.post("/notifications/{address}/{uuid}/start")
# async def start_notifications(address: str, uuid: str):
#     """Start notifications on a characteristic.

#     Uses BleakClient.start_notify().
#     Based on examples/uart_service.py and examples/two_devices.py.
#     """
#     return await manager.start_notifications(address, uuid)


# @app.post("/notifications/{address}/{uuid}/stop")
# async def stop_notifications(address: str, uuid: str):
#     """Stop notifications on a characteristic.

#     Uses BleakClient.stop_notify().
#     Based on examples/uart_service.py.
#     """
#     return await manager.stop_notifications(address, uuid)


# @app.get("/status/{address}")
# async def get_status(address: str):
#     """Get connection status for a device."""
#     return await manager.get_status(address)


@app.get("/debug")
async def debug_info():
    """Get debug information about the Bluetooth manager state."""
    return await manager.get_debug_info()