"""
Mock Bluetooth LE REST API using FastAPI

This API simulates key BLE operations through REST endpoints, providing
fake device data for development environments without real Bluetooth hardware.
"""

from typing import Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(title="Mock Bluetooth LE API", debug=False)


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


class WriteRequest(BaseModel):
    """Request parameters for writing to a characteristic."""

    data: str
    response: bool = True


class MockBluetoothManager:
    """Mock manager that simulates Bluetooth operations."""

    def __init__(self):
        self._connected_devices: dict[str, dict] = {}
        self._discovered_devices: dict[str, DeviceInfo] = {}
        self._simulation_counter = 0

    def _generate_mock_devices(self) -> list[DeviceInfo]:
        """Generate mock BLE devices for simulation."""
        mock_devices = []

        # Simulate realistic BLE devices matching real API format
        device_templates = [
            {
                "address": "00:0a:45:19:8a:92",
                "name": "LE_ATH-M50xBT2",
                "rssi": -60,
                "tx_power": None,
                "service_uuids": ["0000fe03-0000-1000-8000-00805f9b34fb"],
                "service_data": {},
                "manufacturer_data": {"1560": "01000d"},
                "service_names": ["Vendor specific"],
            },
            {
                "address": "50:4c:78:4e:04:d1",
                "name": None,
                "rssi": -61,
                "tx_power": -7,
                "service_uuids": ["0000fe2c-0000-1000-8000-00805f9b34fb"],
                "service_data": {"0000fe2c-0000-1000-8000-00805f9b34fb": "66e913"},
                "manufacturer_data": {},
                "service_names": ["Google Inc."],
            },
            {
                "address": "7a:28:d7:da:fd:05",
                "name": None,
                "rssi": -64,
                "tx_power": None,
                "service_uuids": [],
                "service_data": {},
                "manufacturer_data": {"76": "0719011b202b998f110005e74b0eef6dd25d2ab5b975e90880f847"},
                "service_names": ["AirPods Pro"],
            },
            {
                "address": "ed:18:b4:41:51:07",
                "name": None,
                "rssi": -68,
                "tx_power": None,
                "service_uuids": [],
                "service_data": {},
                "manufacturer_data": {"76": "12026401071106ab75f62724154c0d924c86ca73b55797"},
                "service_names": [],
            },
            {
                "address": "4f:3f:46:97:f5:2d",
                "name": None,
                "rssi": -45,
                "tx_power": None,
                "service_uuids": [],
                "service_data": {},
                "manufacturer_data": {"76": "0908132dc0a802aa1b58160800f2b162e49ee5e2"},
                "service_names": ["iMac"],
            },
            {
                "address": "4c:61:5d:cc:27:12",
                "name": None,
                "rssi": -58,
                "tx_power": None,
                "service_uuids": [],
                "service_data": {},
                "manufacturer_data": {"76": "100603190eafec08"},
                "service_names": [],
            },
            {
                "address": "4c:93:8e:aa:40:73",
                "name": None,
                "rssi": -63,
                "tx_power": 0,
                "service_uuids": [],
                "service_data": {},
                "manufacturer_data": {"76": "10052a983a114f"},
                "service_names": [],
            },
            {
                "address": "7c:17:f5:20:17:5f",
                "name": None,
                "rssi": -50,
                "tx_power": None,
                "service_uuids": [],
                "service_data": {},
                "manufacturer_data": {"76": "0c0e006ef304d2aa55257dc16926b3ad10064e1d7c53d858"},
                "service_names": ["AirPods"],
            },
            {
                "address": "41:b3:98:2e:e2:39",
                "name": None,
                "rssi": -35,
                "tx_power": 0,
                "service_uuids": [],
                "service_data": {},
                "manufacturer_data": {"76": "0100000000000000000000000080000000"},
                "service_names": ["AirPods"],
            },
            {
                "address": "43:3e:d0:17:52:bf",
                "name": None,
                "rssi": -58,
                "tx_power": 0,
                "service_uuids": [],
                "service_data": {},
                "manufacturer_data": {"76": "10077e1fcdd45c89e8"},
                "service_names": [],
            },
            {
                "address": "ce:57:21:6d:c4:c6",
                "name": None,
                "rssi": -77,
                "tx_power": None,
                "service_uuids": [],
                "service_data": {},
                "manufacturer_data": {"76": "12020001"},
                "service_names": ["AirPods"],
            },
            {
                "address": "c4:c1:5a:4f:54:0c",
                "name": "N01K9",
                "rssi": -86,
                "tx_power": None,
                "service_uuids": ["0000feaf-0000-1000-8000-00805f9b34fb"],
                "service_data": {},
                "manufacturer_data": {},
                "service_names": ["Nest Labs Inc."],
            },
        ]

        for template in device_templates:
            device = DeviceInfo(
                address=template["address"].lower(),
                name=template["name"],
                rssi=template["rssi"],
                tx_power=template["tx_power"],
                service_uuids=template["service_uuids"],
                service_data=template["service_data"],
                manufacturer_data=template["manufacturer_data"],
                service_names=template["service_names"],
            )
            mock_devices.append(device)
            self._discovered_devices[device.address] = device

        return mock_devices

    async def scan(
        self, timeout: float = 5.0, service_uuids: Optional[list[str]] = None
    ) -> list[DeviceInfo]:
        """Simulate scanning for BLE devices."""
        self._simulation_counter += 1
        # Simulate scan delay
        await self._async_sleep(0.1)
        devices = self._generate_mock_devices()

        # Filter by service_uuids if provided
        if service_uuids:
            devices = [
                d
                for d in devices
                if any(s in d.service_uuids for s in service_uuids)
            ]

        return devices

    async def _async_sleep(self, seconds: float):
        """Simple async sleep for simulation."""
        import asyncio

        await asyncio.sleep(seconds)

    async def find_device(
        self, address: Optional[str] = None, name: Optional[str] = None
    ) -> Optional[DeviceInfo]:
        """Find a device by address or name."""
        if address:
            address = address.lower()
            return self._discovered_devices.get(address)
        elif name:
            for device in self._discovered_devices.values():
                if device.name and name.lower() in device.name.lower():
                    return device
        return None

    async def connect(
        self, address: str, timeout: float = 30.0
    ) -> dict:
        """Simulate connecting to a device."""
        address = address.lower()

        if address in self._connected_devices:
            if self._connected_devices[address]["connected"]:
                return {"address": address, "status": "already connected"}
            else:
                del self._connected_devices[address]

        # Simulate connection delay
        await self._async_sleep(0.2)

        self._connected_devices[address] = {
            "connected": True,
            "name": f"Mock Device {address[-2:].upper()}",
            "paired": False,
            "mtu": 23,
        }
        return {"address": address, "status": "connected", "paired": False}

    async def disconnect(self, address: str) -> dict:
        """Simulate disconnecting from a device."""
        address = address.lower()

        if address not in self._connected_devices:
            return {"address": address, "status": "not connected"}

        del self._connected_devices[address]
        return {"address": address, "status": "disconnected"}

    async def get_services(self, address: str) -> dict:
        """Simulate getting services for a connected device."""
        address = address.lower()

        if address not in self._connected_devices:
            raise HTTPException(status_code=404, detail="Device not connected")

        device_info = self._connected_devices[address]

        # Return mock services
        services = [
            {
                "uuid": "00001800-0000-1000-8000-00805f9b34fb",
                "description": "Generic Access",
                "characteristics": [
                    {
                        "uuid": "00002a00-0000-1000-8000-00805f9b34fb",
                        "properties": ["read"],
                        "description": "Device Name",
                    },
                    {
                        "uuid": "00002a01-0000-1000-8000-00805f9b34fb",
                        "properties": ["read"],
                        "description": "Appearance",
                    },
                ],
            },
            {
                "uuid": "00001801-0000-1000-8000-00805f9b34fb",
                "description": "Generic Attribute",
                "characteristics": [
                    {
                        "uuid": "00002a05-0000-1000-8000-00805f9b34fb",
                        "properties": ["read", "indicate"],
                        "description": "Service Changed",
                    }
                ],
            },
        ]

        return {
            "address": address,
            "name": device_info["name"],
            "services": services,
        }

    async def read_characteristic(self, address: str, uuid: str) -> dict:
        """Simulate reading from a characteristic."""
        address = address.lower()

        if address not in self._connected_devices:
            raise HTTPException(status_code=404, detail="Device not connected")

        # Simulate different responses based on UUID
        mock_values = {
            "00002a00-0000-1000-8000-00805f9b34fb": "TW9jayBEZXZpY2Ug",  # "Mock Device" in base64-like hex
            "00002a01-0000-1000-8000-00805f9b34fb": "AQ==",  # Appearance value
        }

        value = mock_values.get(uuid, "AQ==")

        return {
            "address": address,
            "characteristic": uuid,
            "value": value,
        }

    async def write_characteristic(
        self, address: str, uuid: str, data: str, response: bool = True
    ) -> dict:
        """Simulate writing to a characteristic."""
        address = address.lower()

        if address not in self._connected_devices:
            raise HTTPException(status_code=404, detail="Device not connected")

        return {
            "address": address,
            "characteristic": uuid,
            "status": "written",
        }

    async def start_notifications(
        self, address: str, uuid: str, callback_url: Optional[str] = None
    ) -> dict:
        """Simulate starting notifications."""
        address = address.lower()

        if address not in self._connected_devices:
            raise HTTPException(status_code=404, detail="Device not connected")

        return {
            "address": address,
            "characteristic": uuid,
            "status": "notifications started",
        }

    async def stop_notifications(self, address: str, uuid: str) -> dict:
        """Simulate stopping notifications."""
        address = address.lower()

        if address not in self._connected_devices:
            raise HTTPException(status_code=404, detail="Device not connected")

        return {
            "address": address,
            "characteristic": uuid,
            "status": "notifications stopped",
        }

    async def get_status(self, address: str) -> dict:
        """Get simulated connection status."""
        address = address.lower()

        if address in self._connected_devices:
            device = self._connected_devices[address]
            return {
                "address": address,
                "connected": device["connected"],
                "name": device["name"],
                "mtu": device.get("mtu", 23),
            }
        return {"address": address, "connected": False}

    async def get_debug_info(self) -> dict:
        """Get simulated debug information."""
        return {
            "discovered_devices_count": len(self._discovered_devices),
            "connected_devices": [
                {"address": addr, "connected": info["connected"]}
                for addr, info in self._connected_devices.items()
            ],
            "simulation_counter": self._simulation_counter,
        }


manager = MockBluetoothManager()


@app.get("/devices", response_model=list[DeviceInfo])
async def list_devices():
    """List all discovered devices."""
    return list(manager._discovered_devices.values())


@app.post("/scan", response_model=list[DeviceInfo])
async def scan_devices(request: Optional[ScanRequest] = None):
    """Scan for BLE devices (simulated)."""
    timeout = request.timeout if request else 5.0
    service_uuids = request.service_uuids if request else None
    return await manager.scan(timeout=timeout, service_uuids=service_uuids)


@app.post("/find", response_model=Optional[DeviceInfo])
async def find_device(address: Optional[str] = None, name: Optional[str] = None):
    """Find a device by address or name (simulated)."""
    return await manager.find_device(address=address, name=name)


@app.post("/connect")
async def connect_device(request: ConnectRequest):
    """Connect to a device (simulated)."""
    return await manager.connect(
        address=request.address, timeout=request.timeout
    )


@app.post("/disconnect/{address}")
async def disconnect_device(address: str):
    """Disconnect from a device (simulated)."""
    return await manager.disconnect(address)


@app.get("/services/{address}")
async def get_services(address: str):
    """Get services for a connected device (simulated)."""
    return await manager.get_services(address)


@app.get("/characteristics/{address}/{uuid}")
async def read_characteristic(address: str, uuid: str):
    """Read from a characteristic (simulated)."""
    return await manager.read_characteristic(address, uuid)


@app.post("/characteristics/{address}/{uuid}")
async def write_characteristic(address: str, uuid: str, request: WriteRequest):
    """Write to a characteristic (simulated)."""
    return await manager.write_characteristic(
        address, uuid, request.data, request.response
    )


@app.post("/notifications/{address}/{uuid}/start")
async def start_notifications(address: str, uuid: str):
    """Start notifications on a characteristic (simulated)."""
    return await manager.start_notifications(address, uuid)


@app.post("/notifications/{address}/{uuid}/stop")
async def stop_notifications(address: str, uuid: str):
    """Stop notifications on a characteristic (simulated)."""
    return await manager.stop_notifications(address, uuid)


@app.get("/status/{address}")
async def get_status(address: str):
    """Get connection status for a device (simulated)."""
    return await manager.get_status(address)


@app.get("/debug")
async def debug_info():
    """Get debug information about the mock Bluetooth manager state."""
    return await manager.get_debug_info()