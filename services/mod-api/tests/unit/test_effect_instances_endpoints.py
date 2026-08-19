"""Unit tests for Effect instance endpoints (add/remove).

These tests verify the API layer sends correct commands to mod-host by using
MockModHostClient to track what commands would be sent.
"""

import pytest

from fastapi import HTTPException
from fastapi.responses import JSONResponse
from mod_api.models import EffectInstance, Connection, Port

NAM_PLUGIN_URI = "http://github.com/mikeoliphant/neural-amp-modeler-lv2"
NAM_MODEL_URI = "http://github.com/mikeoliphant/neural-amp-modeler-lv2#model"


class TestAddEffectEndpoint:
    """Tests for POST /api/v1/pedalboards/{id}/effects endpoint."""

    @pytest.mark.asyncio
    async def test_add_effect_sends_add_plugin_command(self, mock_client, mock_store, mock_registry):
        """Test adding an effect sends correct add command to mod-host."""
        from mod_api.api import create_effect_instance

        # Create a pedalboard first
        pb = mock_store.create("Test PB", None)

        request = {"effect_uri": NAM_PLUGIN_URI, "name": "NAM"}
        response = await create_effect_instance(
            pedalboard_id=pb.id,
            request=request,
            store=mock_store,
            registry=mock_registry,
            client=mock_client
        )

        # Response is the EffectInstance model directly
        assert response.uri == NAM_PLUGIN_URI
        # Verify add command was sent with correct instance ID
        # Note: instance_id is max(pb.effects.keys()) + 1, starting at 1 for empty pedalboard
        assert len(mock_client.commands_sent) >= 1
        assert "add" in mock_client.commands_sent[0]

    @pytest.mark.asyncio
    async def test_add_effect_initializes_parameters(self, mock_client, mock_store, mock_registry):
        """Test adding an effect initializes parameters with default values."""
        from mod_api.api import create_effect_instance

        # Create a pedalboard first
        pb = mock_store.create("Test PB", None)

        request = {"effect_uri": NAM_PLUGIN_URI, "name": "NAM"}
        response = await create_effect_instance(
            pedalboard_id=pb.id,
            request=request,
            store=mock_store,
            registry=mock_registry,
            client=mock_client
        )

        assert response.uri == NAM_PLUGIN_URI
        # Verify add command was sent
        add_cmd = f'add "{NAM_PLUGIN_URI}" 1'
        assert add_cmd in mock_client.commands_sent
        # Parameters should be initialized with default values from registry
        assert "model" in response.parameters
        assert "input_level" in response.parameters
        assert "output_level" in response.parameters
        # Default values should be set
        assert response.parameters["input_level"].value == 0.5


class TestRemoveEffectEndpoint:
    """Tests for DELETE /api/v1/pedalboards/{id}/effects/{effect_id}."""

    @pytest.mark.asyncio
    async def test_remove_effect_sends_remove_command(self, mock_client, mock_store):
        """Test removing effect sends remove command to mod-host."""
        from mod_api.api import remove_effect_instance

        pedalboard = mock_store.create("Test PB", None)
        # Add an effect to the pedalboard
        effect = EffectInstance(
            id=0,
            uri=NAM_PLUGIN_URI,
            name="NAM",
            ports=[Port(name="input", type="input"), Port(name="output", type="output")],
            parameters={}
        )
        pedalboard.effects[0] = effect

        response = await remove_effect_instance(
            pedalboard_id=pedalboard.id,
            effect_id=0,
            store=mock_store,
            client=mock_client
        )

        # Response is None (204 No Content)
        assert response is None
        # Verify exact remove command was sent
        assert mock_client.commands_sent == ["remove 0"]

    @pytest.mark.asyncio
    async def test_remove_effect_removes_connections(self, mock_client, mock_store):
        """Test removing effect also removes its connections."""
        from mod_api.api import remove_effect_instance

        pedalboard = mock_store.create("Test PB", None)
        effect = EffectInstance(
            id=0,
            uri=NAM_PLUGIN_URI,
            name="NAM",
            ports=[Port(name="input", type="input"), Port(name="output", type="output")],
            parameters={}
        )
        pedalboard.effects[0] = effect
        pedalboard.connections[1] = Connection(input_port_id="effect_0:output", output_port_id="system:playback_1")

        await remove_effect_instance(
            pedalboard_id=pedalboard.id,
            effect_id=0,
            store=mock_store,
            client=mock_client
        )

        # Connections involving the effect should be removed
        assert len(pedalboard.connections) == 0

    @pytest.mark.asyncio
    async def test_add_effect_nonexistent_pedalboard(self, mock_client, mock_store, mock_registry):
        """Test adding effect to nonexistent pedalboard returns 404."""
        from mod_api.api import create_effect_instance

        try:
            await create_effect_instance(
                pedalboard_id=999,
                request={"effect_uri": NAM_PLUGIN_URI},
                store=mock_store,
                registry=mock_registry,
                client=mock_client
            )
            assert False, "Should have raised HTTPException"
        except HTTPException as e:
            assert e.status_code == 404
            assert e.detail["code"] == "PEDALBOARD_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_add_effect_nonexistent_effect_uri(self, mock_client, mock_store, mock_registry):
        """Test adding nonexistent effect returns 404."""
        from mod_api.api import create_effect_instance

        # Configure registry to return None for this test
        mock_registry.get.return_value = None

        pb = mock_store.create("Test PB", None)
        try:
            await create_effect_instance(
                pedalboard_id=pb.id,
                request={"effect_uri": "http://nonexistent"},
                store=mock_store,
                registry=mock_registry,
                client=mock_client
            )
            assert False, "Should have raised HTTPException"
        except HTTPException as e:
            assert e.status_code == 404
            assert e.detail["code"] == "EFFECT_NOT_AVAILABLE"

    @pytest.mark.asyncio
    async def test_add_effect_missing_effect_uri(self, mock_client, mock_store, mock_registry):
        """Test adding effect without effect_uri returns 400."""
        from mod_api.api import create_effect_instance

        pb = mock_store.create("Test PB", None)
        try:
            await create_effect_instance(
                pedalboard_id=pb.id,
                request={},
                store=mock_store,
                registry=mock_registry,
                client=mock_client
            )
            assert False, "Should have raised HTTPException"
        except HTTPException as e:
            assert e.status_code == 404  # EFFECT_NOT_AVAILABLE (effect_uri missing means effect not found)
            assert e.detail["code"] == "EFFECT_NOT_AVAILABLE"

    @pytest.mark.asyncio
    async def test_add_effect_plugin_failure(self, mock_client, mock_store, mock_registry):
        """Test adding effect with mod-host failure returns 500 PLUGIN_ERROR."""
        from mod_api.api import create_effect_instance
        from mock_client import MockModHostClient

        pb = mock_store.create("Test PB", None)

        # Configure mock to fail the add command
        mock_client.set_response('add *', MockModHostClient.ERR_LV2_INSTANTIATION)

        try:
            await create_effect_instance(
                pedalboard_id=pb.id,
                request={"effect_uri": NAM_PLUGIN_URI},
                store=mock_store,
                registry=mock_registry,
                client=mock_client
            )
            assert False, "Should have raised HTTPException"
        except HTTPException as e:
            assert e.status_code == 500
            assert e.detail["code"] == "PLUGIN_ERROR"