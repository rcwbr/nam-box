"""Unit tests for Connection endpoints.

These tests verify the API layer sends correct commands to mod-host by using
MockModHostClient to track what commands would be sent.
"""

import os
import pytest

from fastapi import HTTPException
from mod_api.models import EffectInstance, Connection, Port
from mod_api.api import list_ports, create_connection, remove_connection, list_connections

NAM_PLUGIN_URI = "http://github.com/mikeoliphant/neural-amp-modeler-lv2"


class TestPortsEndpoint:
    """Tests for GET /api/v1/pedalboards/{id}/ports endpoint."""

    @pytest.mark.asyncio
    async def test_list_ports_nonexistent_pedalboard(self, mock_store, mock_client):
        """Test listing ports on nonexistent pedalboard returns 404."""

        try:
            await list_ports(pedalboard_id=999, store=mock_store, client=mock_client)
            assert False, "Should have raised HTTPException"
        except HTTPException as e:
            assert e.status_code == 404
            assert e.detail == {"error": "Pedalboard not found", "code": "PEDALBOARD_NOT_FOUND"}

    @pytest.mark.asyncio
    async def test_list_ports_includes_system_ports(self, mock_store, mock_client):
        """Test listing ports includes system input/output ports."""

        # Configure system ports via environment variable
        os.environ["SYSTEM_PORTS"] = "system:capture_1,system:capture_2,system:playback_1,system:playback_2"

        pb = mock_store.create("Test PB", None)
        response = await list_ports(pedalboard_id=pb.id, store=mock_store, client=mock_client)
        expected_ports = [
            Port(name="capture_1", type="input", owner_type="system", effect_instance_id=None),
            Port(name="capture_2", type="input", owner_type="system", effect_instance_id=None),
            Port(name="playback_1", type="output", owner_type="system", effect_instance_id=None),
            Port(name="playback_2", type="output", owner_type="system", effect_instance_id=None),
        ]
        assert response == expected_ports

        # Clean up
        del os.environ["SYSTEM_PORTS"]

    @pytest.mark.asyncio
    async def test_list_ports_includes_effect_ports(self, mock_store, mock_client):
        """Test listing ports includes effect instance ports."""

        # Configure system ports via environment variable
        os.environ["SYSTEM_PORTS"] = "system:capture_1,system:playback_1"

        pb = mock_store.create("Test PB", None)
        effect = EffectInstance(
            uri=NAM_PLUGIN_URI,
            name="NAM",
            ports=[
                Port(name="input", type="input"),
                Port(name="output", type="output")
            ],
            parameters={}
        )
        pb.effects[0] = effect
        mock_store._pedalboards[pb.id] = pb

        response = await list_ports(pedalboard_id=pb.id, store=mock_store, client=mock_client)
        expected_ports = [
            Port(name="capture_1", type="input", owner_type="system", effect_instance_id=None),
            Port(name="playback_1", type="output", owner_type="system", effect_instance_id=None),
            Port(name="input", type="input", owner_type="effect", effect_instance_id=0),
            Port(name="output", type="output", owner_type="effect", effect_instance_id=0),
        ]
        assert response == expected_ports

        # Clean up
        del os.environ["SYSTEM_PORTS"]


class TestListConnectionsEndpoint:
    """Tests for GET /api/v1/pedalboards/{id}/connections endpoint."""

    @pytest.mark.asyncio
    async def test_list_connections_nonexistent_pedalboard(self, mock_store):
        """Test listing connections on nonexistent pedalboard returns 404."""

        try:
            await list_connections(pedalboard_id=999, store=mock_store)
            assert False, "Should have raised HTTPException"
        except HTTPException as e:
            assert e.status_code == 404
            assert e.detail == {"error": "Pedalboard not found", "code": "PEDALBOARD_NOT_FOUND"}

    @pytest.mark.asyncio
    async def test_list_connections_empty(self, mock_store):
        """Test listing connections on empty pedalboard returns empty dict."""

        pb = mock_store.create("Test PB", None)
        response = await list_connections(pedalboard_id=pb.id, store=mock_store)
        assert response == {}


class TestCreateConnectionEndpoint:
    """Tests for POST /api/v1/pedalboards/{id}/connections endpoint."""

    @pytest.mark.asyncio
    async def test_create_connection_sends_connect_command(self, mock_client, mock_store):
        """Test creating a connection sends correct connect command to mod-host."""

        # Configure system ports via environment variable
        os.environ["SYSTEM_PORTS"] = "system:capture_1,system:playback_1"

        pb = mock_store.create("Test PB", None)

        # Add an effect to the pedalboard so effect ports are recognized
        effect = EffectInstance(
            uri=NAM_PLUGIN_URI,
            name="NAM",
            ports=[Port(name="output", type="output")],
            parameters={}
        )
        pb.effects[0] = effect
        mock_store._pedalboards[pb.id] = pb

        request = {
            "input_port_id": "system:capture_1",
            "output_port_id": "effect_0:output"
        }
        response = await create_connection(
            pedalboard_id=pb.id,
            request=request,
            store=mock_store,
            client=mock_client
        )

        # Response is Connection model directly (per spec returns with connection ID)
        assert response == Connection(id=1, input_port_id="system:capture_1", output_port_id="effect_0:output")
        # Verify commands were sent (enumerate to validate ports, then connect)
        assert mock_client.commands_sent == ['enumerate', 'connect "system:capture_1" "effect_0:output"']

        # Clean up
        del os.environ["SYSTEM_PORTS"]

    @pytest.mark.asyncio
    async def test_create_connection_missing_ports(self, mock_client, mock_store):
        """Test creating connection without port IDs returns 400."""

        # Configure system ports via environment variable
        os.environ["SYSTEM_PORTS"] = "system:capture_1,system:playback_1"

        pb = mock_store.create("Test PB", None)
        try:
            await create_connection(
                pedalboard_id=pb.id,
                request={},
                store=mock_store,
                client=mock_client
            )
            assert False, "Should have raised HTTPException"
        except HTTPException as e:
            assert e.status_code == 400
            assert e.detail == {"error": "Port IDs required", "code": "INVALID_REQUEST"}

        # Clean up
        del os.environ["SYSTEM_PORTS"]

    @pytest.mark.asyncio
    async def test_create_connection_creates_pedalboard_connection(self, mock_client, mock_store):
        """Test creating connection adds to pedalboard's connections list."""

        # Configure system ports via environment variable
        os.environ["SYSTEM_PORTS"] = "system:capture_1,system:playback_1"

        pb = mock_store.create("Test PB", None)
        initial_count = len(pb.connections)

        # Add an effect to the pedalboard
        effect = EffectInstance(
            uri=NAM_PLUGIN_URI,
            name="NAM",
            ports=[Port(name="output", type="output")],
            parameters={}
        )
        pb.effects[0] = effect
        mock_store._pedalboards[pb.id] = pb

        request = {
            "input_port_id": "system:capture_1",
            "output_port_id": "effect_0:output"
        }
        response = await create_connection(
            pedalboard_id=pb.id,
            request=request,
            store=mock_store,
            client=mock_client
        )

        assert response == Connection(id=1, input_port_id="system:capture_1", output_port_id="effect_0:output")
        assert pb.connections == {1: Connection(id=1, input_port_id="system:capture_1", output_port_id="effect_0:output")}

        # Clean up
        del os.environ["SYSTEM_PORTS"]

    @pytest.mark.asyncio
    async def test_create_connection_nonexistent_port(self, mock_client, mock_store):
        """Test creating connection with nonexistent port returns 404 PORT_NOT_FOUND."""

        # Configure system ports via environment variable
        os.environ["SYSTEM_PORTS"] = "system:capture_1,system:playback_1"

        pb = mock_store.create("Test PB", None)

        # Try to create connection with port that doesn't exist
        request = {
            "input_port_id": "system:nonexistent",
            "output_port_id": "system:playback_1"
        }
        try:
            await create_connection(
                pedalboard_id=pb.id,
                request=request,
                store=mock_store,
                client=mock_client
            )
            assert False, "Should have raised HTTPException"
        except HTTPException as e:
            assert e.status_code == 404
            assert e.detail == {"error": "Port not found", "code": "PORT_NOT_FOUND"}

        # Clean up
        del os.environ["SYSTEM_PORTS"]

    @pytest.mark.asyncio
    async def test_create_connection_failed_status(self, mock_client, mock_store):
        """Test creating connection with mod-host failure returns 500 CONNECTION_ERROR."""
        from mock_client import MockModHostClient

        # Configure system ports via environment variable
        os.environ["SYSTEM_PORTS"] = "system:capture_1,system:playback_1"

        # Configure connect to fail
        mock_client.set_response('connect *', MockModHostClient.ERR_JACK_PORT_CONNECTION)

        pb = mock_store.create("Test PB", None)

        request = {
            "input_port_id": "system:capture_1",
            "output_port_id": "system:playback_1"
        }
        try:
            await create_connection(
                pedalboard_id=pb.id,
                request=request,
                store=mock_store,
                client=mock_client
            )
            assert False, "Should have raised HTTPException"
        except HTTPException as e:
            assert e.status_code == 500
            assert e.detail == {"error": "Failed to connect ports (code: -205)", "code": "CONNECTION_ERROR"}

        # Clean up
        del os.environ["SYSTEM_PORTS"]


class TestDeleteConnectionEndpoint:
    """Tests for DELETE /api/v1/pedalboards/{id}/connections/{connection_id}."""

    @pytest.mark.asyncio
    async def test_delete_connection_nonexistent(self, mock_client, mock_store):
        """Test deleting nonexistent connection returns 404 CONNECTION_NOT_FOUND."""

        # First create a pedalboard
        pb = mock_store.create("Test", None)

        try:
            await remove_connection(
                pedalboard_id=pb.id,
                connection_id=999,
                store=mock_store,
                client=mock_client
            )
            assert False, "Should have raised HTTPException"
        except HTTPException as e:
            assert e.status_code == 404
            assert e.detail == {"error": "Connection not found", "code": "CONNECTION_NOT_FOUND"}

    @pytest.mark.asyncio
    async def test_delete_connection_sends_disconnect(self, mock_client, mock_store):
        """Test deleting connection sends disconnect command to mod-host."""

        pb = mock_store.create("Test", None)
        # Add a connection
        conn = Connection(input_port_id="system:capture_1", output_port_id="effect_0:output")
        pb.connections[1] = conn
        mock_store._pedalboards[pb.id] = pb

        response = await remove_connection(
            pedalboard_id=pb.id,
            connection_id=1,
            store=mock_store,
            client=mock_client
        )
        # Response is None (204 No Content)
        assert response is None
        # Verify disconnect command was sent
        assert mock_client.commands_sent == ['disconnect "system:capture_1" "effect_0:output"']

    @pytest.mark.asyncio
    async def test_delete_connection_nonexistent_pedalboard(self, mock_client, mock_store):
        """Test deleting connection on nonexistent pedalboard returns 404 PEDALBOARD_NOT_FOUND."""

        try:
            await remove_connection(
                pedalboard_id=999,
                connection_id=1,
                store=mock_store,
                client=mock_client
            )
            assert False, "Should have raised HTTPException"
        except HTTPException as e:
            assert e.status_code == 404
            assert e.detail == {"error": "Pedalboard not found", "code": "PEDALBOARD_NOT_FOUND"}