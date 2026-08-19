"""Unit tests for Parameter endpoints.

These tests verify the API layer sends correct commands to mod-host by using
MockModHostClient to track what commands would be sent.
"""

import pytest

from fastapi import HTTPException
from mod_api.models import EffectInstance, Port
from mod_api.models.parameter import NumberParameter, FilenameParameter

NAM_PLUGIN_URI = "http://github.com/mikeoliphant/neural-amp-modeler-lv2"
NAM_MODEL_URI = "http://github.com/mikeoliphant/neural-amp-modeler-lv2#model"


class TestGetParameterEndpoint:
    """Tests for GET /api/v1/pedalboards/{id}/effects/{effect_id}/parameters endpoints."""

    @pytest.mark.asyncio
    async def test_get_parameters_nonexistent_effect(self, mock_store, mock_registry):
        """Test getting parameters from nonexistent effect instance returns 404."""
        from mod_api.api import get_parameters

        pb = mock_store.create("Test PB", None)

        try:
            await get_parameters(
                pedalboard_id=pb.id,
                effect_id=999,
                store=mock_store
            )
            assert False, "Should have raised HTTPException"
        except HTTPException as e:
            assert e.status_code == 404
            assert e.detail["code"] == "EFFECT_INSTANCE_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_get_parameters_success(self, mock_store):
        """Test getting parameters returns dict of parameter objects directly."""
        from mod_api.api import get_parameters

        pb = mock_store.create("Test PB", None)
        effect = EffectInstance(
            uri=NAM_PLUGIN_URI,
            name="NAM",
            ports=[Port(name="input", type="input"), Port(name="output", type="output")],
            parameters={
                "input_level": NumberParameter(
                    name="input_level",
                    type="number",
                    value=0.75,
                    min=0.0,
                    max=1.0,
                    default=0.5
                )
            }
        )
        pb.effects[0] = effect
        mock_store._pedalboards[pb.id] = pb

        response = await get_parameters(
            pedalboard_id=pb.id,
            effect_id=0,
            store=mock_store
        )
        # Response is a direct dict of parameter name -> Parameter object
        assert "input_level" in response
        assert response["input_level"].name == "input_level"
        assert response["input_level"].value == 0.75

    @pytest.mark.asyncio
    async def test_get_parameter_nonexistent(self, mock_store):
        """Test getting parameter from nonexistent effect instance returns 404."""
        from mod_api.api import get_parameter

        pb = mock_store.create("Test PB", None)

        try:
            await get_parameter(
                pedalboard_id=pb.id,
                effect_id=999,
                param_name="input_level",
                store=mock_store
            )
            assert False, "Should have raised HTTPException"
        except HTTPException as e:
            assert e.status_code == 404
            assert e.detail["code"] == "EFFECT_INSTANCE_NOT_FOUND"


class TestSetParameterEndpoint:
    """Tests for PUT /api/v1/pedalboards/{id}/effects/{effect_id}/parameters/{param_name}."""

    @pytest.mark.asyncio
    async def test_set_parameter_missing_value(self, mock_client, mock_store, mock_registry):
        """Test setting parameter without value returns 400 INVALID_REQUEST."""
        from mod_api.api import set_parameter

        pb = mock_store.create("Test PB", None)
        effect = EffectInstance(
            uri=NAM_PLUGIN_URI,
            name="NAM",
            ports=[Port(name="input", type="input"), Port(name="output", type="output")],
            parameters={
                "input_level": NumberParameter(
                    name="input_level",
                    type="number",
                    value=0.5,
                    min=0.0,
                    max=1.0,
                    default=0.5
                )
            }
        )
        pb.effects[0] = effect
        mock_store._pedalboards[pb.id] = pb

        try:
            await set_parameter(
                pedalboard_id=pb.id,
                effect_id=0,
                param_name="input_level",
                request={},
                store=mock_store,
                client=mock_client
            )
            assert False, "Should have raised HTTPException"
        except HTTPException as e:
            assert e.status_code == 400
            assert e.detail["code"] == "INVALID_REQUEST"


class TestSetNumberParameterEndpoint:
    """Tests for setting number parameters via mod-host."""

    @pytest.mark.asyncio
    async def test_set_number_parameter_sends_param_set(self, mock_client, mock_store, mock_registry):
        """Test setting a number parameter sends param_set command."""
        from mod_api.api import set_parameter

        pb = mock_store.create("Test PB", None)
        # Add an effect with a parameter already set
        effect = EffectInstance(
            uri=NAM_PLUGIN_URI,
            name="NAM",
            ports=[Port(name="input", type="input"), Port(name="output", type="output")],
            parameters={
                "input_level": NumberParameter(
                    name="input_level",
                    type="number",
                    value=0.5,
                    min=0.0,
                    max=1.0,
                    default=0.5
                )
            }
        )
        pb.effects[0] = effect
        mock_store._pedalboards[pb.id] = pb

        # Set input_level to 0.75
        response = await set_parameter(
            pedalboard_id=pb.id,
            effect_id=0,
            param_name="input_level",
            request={"value": 0.75},
            store=mock_store,
            client=mock_client
        )

        # Response is None (204 No Content is not returned, but 200 OK with no body)
        # Actually per spec: PUT returns 200 OK
        assert response is None
        # Verify exact param_set command was called
        assert mock_client.commands_sent == ["param_set 0 input_level 0.75"]


class TestSetModelParameterEndpoint:
    """Tests for setting model parameters via patch_set."""

    @pytest.mark.asyncio
    async def test_set_model_parameter_sends_patch_set(self, mock_client, mock_store, mock_registry):
        """Test setting model parameter uses patch_set command."""
        from mod_api.api import set_parameter

        pb = mock_store.create("Test PB", None)

        # Add an effect with a model parameter already set
        effect = EffectInstance(
            uri=NAM_PLUGIN_URI,
            name="NAM",
            ports=[Port(name="input", type="input"), Port(name="output", type="output")],
            parameters={
                "model": FilenameParameter(
                    name="model",
                    type="filename",
                    value="",
                    default=""
                )
            }
        )
        pb.effects[0] = effect
        mock_store._pedalboards[pb.id] = pb

        # Set model to a file path
        model_path = "/opt/nam/models/test.nam"
        response = await set_parameter(
            pedalboard_id=pb.id,
            effect_id=0,
            param_name="model",
            request={"value": model_path},
            store=mock_store,
            client=mock_client
        )

        assert response is None
        # Verify exact patch_set command was called
        expected_cmd = f'patch_set 0 {NAM_MODEL_URI} {model_path}'
        assert mock_client.commands_sent == [expected_cmd]

    @pytest.mark.asyncio
    async def test_set_parameter_nonexistent_param(self, mock_client, mock_store, mock_registry):
        """Test setting nonexistent parameter returns 404 PARAMETER_NOT_FOUND."""
        from mod_api.api import set_parameter

        pb = mock_store.create("Test PB", None)
        effect = EffectInstance(
            uri=NAM_PLUGIN_URI,
            name="NAM",
            ports=[Port(name="input", type="input"), Port(name="output", type="output")],
            parameters={}  # No parameters set yet
        )
        pb.effects[0] = effect
        mock_store._pedalboards[pb.id] = pb

        try:
            await set_parameter(
                pedalboard_id=pb.id,
                effect_id=0,
                param_name="nonexistent_param",
                request={"value": 0.5},
                store=mock_store,
                client=mock_client
            )
            assert False, "Should have raised HTTPException"
        except HTTPException as e:
            assert e.status_code == 404
            assert e.detail["code"] == "PARAMETER_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_set_number_parameter_out_of_range(self, mock_client, mock_store, mock_registry):
        """Test setting number parameter outside min/max returns 400."""
        from mod_api.api import set_parameter

        pb = mock_store.create("Test PB", None)
        effect = EffectInstance(
            uri=NAM_PLUGIN_URI,
            name="NAM",
            ports=[Port(name="input", type="input"), Port(name="output", type="output")],
            parameters={
                "input_level": NumberParameter(
                    name="input_level",
                    type="number",
                    value=0.5,
                    min=0.0,
                    max=1.0,
                    default=0.5
                )
            }
        )
        pb.effects[0] = effect
        mock_store._pedalboards[pb.id] = pb

        try:
            await set_parameter(
                pedalboard_id=pb.id,
                effect_id=0,
                param_name="input_level",
                request={"value": 2.0},  # max is 1.0
                store=mock_store,
                client=mock_client
            )
            assert False, "Should have raised HTTPException"
        except HTTPException as e:
            assert e.status_code == 400
            assert e.detail["code"] == "INVALID_PARAMETER"

    @pytest.mark.asyncio
    async def test_set_number_parameter_at_boundary(self, mock_client, mock_store, mock_registry):
        """Test setting number parameter at min/max boundary works."""
        from mod_api.api import set_parameter

        pb = mock_store.create("Test PB", None)
        effect = EffectInstance(
            uri=NAM_PLUGIN_URI,
            name="NAM",
            ports=[Port(name="input", type="input"), Port(name="output", type="output")],
            parameters={
                "input_level": NumberParameter(
                    name="input_level",
                    type="number",
                    value=0.5,
                    min=0.0,
                    max=1.0,
                    default=0.5
                )
            }
        )
        pb.effects[0] = effect
        mock_store._pedalboards[pb.id] = pb

        # Test at min boundary
        response = await set_parameter(
            pedalboard_id=pb.id,
            effect_id=0,
            param_name="input_level",
            request={"value": 0.0},
            store=mock_store,
            client=mock_client
        )
        assert response is None

        # Test at max boundary
        response = await set_parameter(
            pedalboard_id=pb.id,
            effect_id=0,
            param_name="input_level",
            request={"value": 1.0},
            store=mock_store,
            client=mock_client
        )
        assert response is None

    @pytest.mark.asyncio
    async def test_get_parameter_success(self, mock_store):
        """Test getting parameter returns full details."""
        from mod_api.api import get_parameter

        pb = mock_store.create("Test PB", None)
        effect = EffectInstance(
            uri=NAM_PLUGIN_URI,
            name="NAM",
            ports=[Port(name="input", type="input"), Port(name="output", type="output")],
            parameters={
                "input_level": NumberParameter(
                    name="input_level",
                    type="number",
                    value=0.5,
                    min=0.0,
                    max=1.0,
                    default=0.5
                )
            }
        )
        pb.effects[0] = effect
        mock_store._pedalboards[pb.id] = pb

        response = await get_parameter(
            pedalboard_id=pb.id,
            effect_id=0,
            param_name="input_level",
            store=mock_store
        )
        # Response is Parameter object directly
        assert response.name == "input_level"
        assert response.value == 0.5
        assert response.min == 0.0
        assert response.max == 1.0

    @pytest.mark.asyncio
    async def test_set_parameter_failed_status(self, mock_client, mock_store, mock_registry):
        """Test setting parameter with mod-host failure returns 500 PARAMETER_ERROR."""
        from mod_api.api import set_parameter
        from mock_client import MockModHostClient

        pb = mock_store.create("Test PB", None)
        effect = EffectInstance(
            uri=NAM_PLUGIN_URI,
            name="NAM",
            ports=[Port(name="input", type="input"), Port(name="output", type="output")],
            parameters={
                "input_level": NumberParameter(
                    name="input_level",
                    type="number",
                    value=0.5,
                    min=0.0,
                    max=1.0,
                    default=0.5
                )
            }
        )
        pb.effects[0] = effect
        mock_store._pedalboards[pb.id] = pb

        # Configure mock to fail the param_set command (use -1 for generic error)
        mock_client.set_response('param_set *', -1)

        try:
            await set_parameter(
                pedalboard_id=pb.id,
                effect_id=0,
                param_name="input_level",
                request={"value": 0.75},
                store=mock_store,
                client=mock_client
            )
            assert False, "Should have raised HTTPException"
        except HTTPException as e:
            assert e.status_code == 500
            assert e.detail["code"] == "PARAMETER_ERROR"

    @pytest.mark.asyncio
    async def test_get_parameter_nonexistent_on_effect(self, mock_store):
        """Test getting parameter from effect that exists but parameter doesn't returns 404 PARAMETER_NOT_FOUND."""
        from mod_api.api import get_parameter

        pb = mock_store.create("Test PB", None)
        effect = EffectInstance(
            uri=NAM_PLUGIN_URI,
            name="NAM",
            ports=[Port(name="input", type="input"), Port(name="output", type="output")],
            parameters={}  # No parameters
        )
        pb.effects[0] = effect
        mock_store._pedalboards[pb.id] = pb

        try:
            await get_parameter(
                pedalboard_id=pb.id,
                effect_id=0,
                param_name="nonexistent",
                store=mock_store
            )
            assert False, "Should have raised HTTPException"
        except HTTPException as e:
            assert e.status_code == 404
            assert e.detail["code"] == "PARAMETER_NOT_FOUND"