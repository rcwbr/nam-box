"""Unit tests for Pedalboard CRUD endpoints using MockModHostClient.

These tests verify the API layer sends correct commands to mod-host by using
MockModHostClient to track what commands would be sent.
"""

import pytest

from fastapi import HTTPException
from mod_api.api import (
    list_pedalboards,
    get_current_pedalboard,
    create_pedalboard,
    get_pedalboard,
    delete_pedalboard,
    select_pedalboard,
    rename_pedalboard,
)
from mod_api.models import EffectInstance, Port

NAM_PLUGIN_URI = "http://github.com/mikeoliphant/neural-amp-modeler-lv2"


class TestPedalboardListingEndpoint:
    """Tests for GET /api/v1/pedalboards endpoint."""

    @pytest.mark.asyncio
    async def test_list_pedalboards_empty(self, mock_store):
        """Test listing pedalboards when none exist returns empty dict."""
        # Mock store has empty pedalboards initially
        mock_store._pedalboards = {}
        response = await list_pedalboards(store=mock_store)
        assert response == {}

    @pytest.mark.asyncio
    async def test_list_pedalboards_with_items(self, mock_store):
        """Test listing pedalboards returns all pedalboards as dict."""
        mock_store.create("Clean Tone", None)
        mock_store.create("Distorted", None)

        response = await list_pedalboards(store=mock_store)
        assert len(response) == 2
        # Response is a dict keyed by pedalboard ID
        assert "1" in response or 1 in response  # ID keyed
        assert "2" in response or 2 in response  # ID keyed


class TestPedalboardCurrentEndpoint:
    """Tests for GET /api/v1/pedalboards/current endpoint."""

    @pytest.mark.asyncio
    async def test_get_current_pedalboard_when_none(self, mock_store):
        """Test getting current pedalboard when none is selected returns None."""
        mock_store._current_id = None
        response = await get_current_pedalboard(store=mock_store)
        # Per spec: returns 204 No Content if no pedalboard is currently selected.
        # The endpoint returns None which FastAPI converts to 204 response.
        assert response is None

    @pytest.mark.asyncio
    async def test_get_current_pedalboard(self, mock_store):
        """Test getting current pedalboard returns the selected one."""
        pb = mock_store.create("My Board", None)
        # After create, pb is current, but need to check _pedalboards
        response = await get_current_pedalboard(store=mock_store)
        # Response is the Pedalboard model directly
        assert response.id == pb.id
        assert response.name == "My Board"


class TestPedalboardCreateEndpoint:
    """Tests for POST /api/v1/pedalboards endpoint."""

    @pytest.mark.asyncio
    async def test_create_pedalboard_missing_name(self, mock_store):
        """Test creating pedalboard without name returns 400 INVALID_REQUEST."""
        try:
            await create_pedalboard(store=mock_store, request={"duplicate_current": False})
            assert False, "Should have raised HTTPException"
        except HTTPException as e:
            assert e.status_code == 400
            assert e.detail["code"] == "INVALID_REQUEST"

    @pytest.mark.asyncio
    async def test_create_pedalboard_empty_name(self, mock_store):
        """Test creating pedalboard with empty name returns 400 INVALID_REQUEST."""
        try:
            await create_pedalboard(store=mock_store, request={"name": "", "duplicate_current": False})
            assert False, "Should have raised HTTPException"
        except HTTPException as e:
            assert e.status_code == 400
            assert e.detail["code"] == "INVALID_REQUEST"

    @pytest.mark.asyncio
    async def test_create_pedalboard_success(self, mock_store):
        """Test creating a pedalboard successfully."""
        response = await create_pedalboard(store=mock_store, request={"name": "Test Board", "duplicate_current": False})
        # Response is the Pedalboard model directly (FastAPI returns JSONResponse automatically)
        assert response.name == "Test Board"
        assert response.id == 1

    @pytest.mark.asyncio
    async def test_create_pedalboard_with_duplicate_current(self, mock_store):
        """Test creating pedalboard as duplicate of current."""
        # Create original pedalboard with effects
        original = mock_store.create("Original", None)
        original.effects[0] = EffectInstance(
            uri=NAM_PLUGIN_URI,
            name="NAM",
            ports=[
                Port(name="input", type="input"),
                Port(name="output", type="output")
            ],
            parameters={}
        )
        mock_store._pedalboards[original.id] = original

        response = await create_pedalboard(store=mock_store, request={"name": "Copy", "duplicate_current": True})
        # Response is the Pedalboard model directly
        assert response.name == "Copy"
        assert len(response.effects) == 1


class TestPedalboardGetEndpoint:
    """Tests for GET /api/v1/pedalboards/{id} endpoint."""

    @pytest.mark.asyncio
    async def test_get_pedalboard_nonexistent(self, mock_store):
        """Test getting nonexistent pedalboard returns 404 PEDALBOARD_NOT_FOUND."""
        try:
            await get_pedalboard(pedalboard_id=999, store=mock_store)
            assert False, "Should have raised HTTPException"
        except HTTPException as e:
            assert e.status_code == 404
            assert e.detail["code"] == "PEDALBOARD_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_get_pedalboard_success(self, mock_store):
        """Test getting an existing pedalboard returns full details."""
        pb = mock_store.create("Test Board", None)
        response = await get_pedalboard(pedalboard_id=pb.id, store=mock_store)
        # Response is a Pedalboard model directly
        assert response.id == pb.id
        assert response.name == "Test Board"

    @pytest.mark.asyncio
    async def test_get_pedalboard_includes_effects(self, mock_store):
        """Test getting pedalboard includes its effects."""
        pb = mock_store.create("Board with Effects", None)
        # Manually add an effect to the pedalboard
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

        response = await get_pedalboard(pedalboard_id=pb.id, store=mock_store)
        assert len(response.effects) == 1
        # The effect is keyed by its instance ID (0) in the effects dict
        assert 0 in response.effects
        assert response.effects[0].uri == NAM_PLUGIN_URI


class TestPedalboardDeleteEndpoint:
    """Tests for DELETE /api/v1/pedalboards/{id} endpoint."""

    @pytest.mark.asyncio
    async def test_delete_pedalboard_nonexistent(self, mock_store):
        """Test deleting nonexistent pedalboard returns 404 PEDALBOARD_NOT_FOUND."""
        try:
            await delete_pedalboard(pedalboard_id=999, store=mock_store)
            assert False, "Should have raised HTTPException"
        except HTTPException as e:
            assert e.status_code == 404
            assert e.detail["code"] == "PEDALBOARD_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_delete_pedalboard_clears_current(self, mock_store):
        """Test deleting current pedalboard clears current selection."""
        # Create a pedalboard (becomes current via mock_create)
        pb1 = mock_store.create("Current Board", None)
        assert mock_store._current_id == pb1.id

        response = await delete_pedalboard(pedalboard_id=pb1.id, store=mock_store)
        # Response is None (204 No Content)
        assert response is None
        # Verify current is cleared
        assert mock_store._current_id is None


class TestPedalboardSelectEndpoint:
    """Tests for PUT /api/v1/pedalboards/{id}/select endpoint."""

    @pytest.mark.asyncio
    async def test_select_pedalboard_nonexistent(self, mock_store):
        """Test selecting nonexistent pedalboard returns 404 PEDALBOARD_NOT_FOUND."""
        try:
            await select_pedalboard(pedalboard_id=999, store=mock_store)
            assert False, "Should have raised HTTPException"
        except HTTPException as e:
            assert e.status_code == 404
            assert e.detail["code"] == "PEDALBOARD_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_select_pedalboard_success(self, mock_store):
        """Test selecting pedalboard sets it as current."""
        # Create first pedalboard (will be current)
        pb1 = mock_store.create("Board 1", None)
        # Create second pedalboard (becomes current)
        pb2 = mock_store.create("Board 2", None)

        response = await select_pedalboard(pedalboard_id=pb1.id, store=mock_store)
        # Response is None (per spec: 200 OK with no body content)
        assert response is None
        # Verify it was set as current
        assert mock_store._current_id == pb1.id


class TestPedalboardRenameEndpoint:
    """Tests for PUT /api/v1/pedalboards/{id}/rename endpoint."""

    @pytest.mark.asyncio
    async def test_rename_pedalboard_missing_name(self, mock_store):
        """Test renaming without name returns 400 INVALID_REQUEST."""
        try:
            await rename_pedalboard(pedalboard_id=1, request={}, store=mock_store)
            assert False, "Should have raised HTTPException"
        except HTTPException as e:
            assert e.status_code == 400
            assert e.detail["code"] == "INVALID_REQUEST"

    @pytest.mark.asyncio
    async def test_rename_pedalboard_empty_name(self, mock_store):
        """Test renaming with empty name returns 400 INVALID_REQUEST."""
        pb = mock_store.create("Original Name", None)
        try:
            await rename_pedalboard(pedalboard_id=pb.id, request={"name": ""}, store=mock_store)
            assert False, "Should have raised HTTPException"
        except HTTPException as e:
            assert e.status_code == 400
            assert e.detail["code"] == "INVALID_REQUEST"

    @pytest.mark.asyncio
    async def test_rename_pedalboard_nonexistent(self, mock_store):
        """Test renaming nonexistent pedalboard returns 404 PEDALBOARD_NOT_FOUND."""
        try:
            await rename_pedalboard(pedalboard_id=999, request={"name": "New Name"}, store=mock_store)
            assert False, "Should have raised HTTPException"
        except HTTPException as e:
            assert e.status_code == 404
            assert e.detail["code"] == "PEDALBOARD_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_rename_pedalboard_success(self, mock_store):
        """Test renaming pedalboard succeeds and updates file name."""
        pb = mock_store.create("Old Name", None)
        response = await rename_pedalboard(pedalboard_id=pb.id, request={"name": "New Name"}, store=mock_store)
        # Response is the Pedalboard model directly (per spec returns the updated pedalboard)
        # Note: FastAPI returns 200 OK automatically with the body
        assert response.name == "New Name"
        assert response.file == "new-name.json"