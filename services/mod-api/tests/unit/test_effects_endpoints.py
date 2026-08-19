"""Unit tests for Effects endpoints.

These tests verify the API layer sends correct commands to mod-host by using
MockModHostClient to track what commands would be sent.
"""

import pytest

from fastapi import HTTPException
from fastapi.responses import JSONResponse
from mod_api.models import Port, EffectInstance

NAM_PLUGIN_URI = "http://github.com/mikeoliphant/neural-amp-modeler-lv2"


class TestEffectsListingEndpoint:
    """Tests for GET /api/v1/effects endpoints."""

    @pytest.mark.asyncio
    async def test_list_effects(self, mock_registry):
        """Test listing all available effects."""
        from mod_api.api import list_effects

        response = await list_effects(registry=mock_registry)
        # Response is a list of EffectInfo objects
        assert len(response) >= 1
        # Check the first effect has required fields
        effect = response[0]
        assert effect.uri == NAM_PLUGIN_URI
        assert effect.name == "Neural Amp Modeler"

    @pytest.mark.asyncio
    async def test_get_effect_nonexistent_uri(self, mock_registry):
        """Test getting an effect that doesn't exist returns 404."""
        from mod_api.api import get_effect

        # Reset registry mock to return None for this test
        mock_registry.get.return_value = None
        try:
            await get_effect(uri="http://nonexistent/effect", registry=mock_registry)
            assert False, "Should have raised HTTPException"
        except HTTPException as e:
            assert e.status_code == 404
            assert e.detail["code"] == "EFFECT_NOT_AVAILABLE"


class TestEffectInstancesEndpoint:
    """Tests for effect instance management endpoints."""

    @pytest.mark.asyncio
    async def test_list_effects_on_pedalboard_nonexistent(self, mock_store):
        """Test listing effects on nonexistent pedalboard returns 404."""
        from mod_api.api import list_effect_instances

        try:
            await list_effect_instances(pedalboard_id=999, store=mock_store)
            assert False, "Should have raised HTTPException"
        except HTTPException as e:
            assert e.status_code == 404
            assert e.detail["code"] == "PEDALBOARD_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_list_effects_on_pedalboard_success(self, mock_store):
        """Test listing effects on a pedalboard returns dict mapping id -> EffectInstance."""
        from mod_api.api import list_effect_instances

        pb = mock_store.create("Board with Effects", None)
        # Add effects to the pedalboard
        pb.effects[0] = EffectInstance(
            uri=NAM_PLUGIN_URI,
            name="NAM",
            ports=[
                Port(name="input", type="input"),
                Port(name="output", type="output")
            ],
            parameters={}
        )
        mock_store._pedalboards[pb.id] = pb

        response = await list_effect_instances(pedalboard_id=pb.id, store=mock_store)
        # Response is a dict mapping instance IDs to EffectInstance objects
        assert len(response) == 1
        assert 0 in response
        assert response[0].uri == NAM_PLUGIN_URI

    @pytest.mark.asyncio
    async def test_list_effects_empty_pedalboard(self, mock_store):
        """Test listing effects on empty pedalboard returns empty dict."""
        from mod_api.api import list_effect_instances

        pb = mock_store.create("Empty Board", None)
        response = await list_effect_instances(pedalboard_id=pb.id, store=mock_store)
        assert response == {}

    @pytest.mark.asyncio
    async def test_get_effect_success(self, mock_registry):
        """Test getting an existing effect returns full details."""
        from mod_api.api import get_effect

        response = await get_effect(uri=NAM_PLUGIN_URI, registry=mock_registry)
        # Response is EffectInfo directly
        assert response.uri == NAM_PLUGIN_URI
        assert response.name == "Neural Amp Modeler"
        assert response.ports is not None
        assert response.parameters is not None