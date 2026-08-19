"""Integration tests for Pedalboard API endpoints using testcontainers mod-host fixture."""

import httpx


# NAM plugin URI for testing
NAM_PLUGIN_URI = "http://github.com/mikeoliphant/neural-amp-modeler-lv2"
TEST_MODEL_PATH = "/opt/nam/models/test.nam"


class TestPedalboardListingIntegration:
    """Integration tests for GET /api/v1/pedalboards endpoint."""

    def test_list_pedalboards_empty(self, mod_api_server):
        """Test listing pedalboards when none exist returns empty dict."""
        response = httpx.get(f"{mod_api_server}/pedalboards")
        assert response.status_code == 200
        assert response.json() == {}

    def test_list_pedalboards_after_creation(self, mod_api_server):
        """Test listing pedalboards after creating one."""
        # Create a pedalboard first
        response = httpx.post(
            f"{mod_api_server}/pedalboards",
            json={"name": "Test Board", "duplicate_current": False}
        )
        assert response.status_code == 201

        response = httpx.get(f"{mod_api_server}/pedalboards")
        assert response.status_code == 200
        pedalboards = response.json()
        assert len(pedalboards) == 1
        pb_data = list(pedalboards.values())[0]
        assert pb_data == {
            "name": "Test Board",
            "id": 1,
            "effects": {},
            "file": "test-board.json",
            "connections": {}
        }


class TestPedalboardCreateIntegration:
    """Integration tests for POST /api/v1/pedalboards endpoint."""

    def test_create_pedalboard_missing_name(self, mod_api_server):
        """Test creating pedalboard without name returns 400 INVALID_REQUEST."""
        response = httpx.post(
            f"{mod_api_server}/pedalboards",
            json={"duplicate_current": False}
        )
        assert response.status_code == 400
        assert response.json()["detail"]["code"] == "INVALID_REQUEST"

    
    def test_create_pedalboard_success(self, mod_api_server):
        """Test creating a pedalboard successfully."""
        response = httpx.post(
            f"{mod_api_server}/pedalboards",
            json={"name": "Clean Tone", "duplicate_current": False}
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Clean Tone"
        assert data["id"] >= 1


class TestPedalboardDeleteIntegration:
    """Integration tests for DELETE /api/v1/pedalboards/{id} endpoint."""

    def test_delete_nonexistent_pedalboard(self, mod_api_server):
        """Test deleting a nonexistent pedalboard returns 404."""
        response = httpx.delete(f"{mod_api_server}/pedalboards/9999")
        assert response.status_code == 404
        assert response.json()["detail"]["code"] == "PEDALBOARD_NOT_FOUND"


class TestPedalboardSelectIntegration:
    """Integration tests for PUT /api/v1/pedalboards/{id}/select endpoint."""

    def test_select_nonexistent_pedalboard(self, mod_api_server):
        """Test selecting nonexistent pedalboard returns 404."""
        response = httpx.put(f"{mod_api_server}/pedalboards/9999/select")
        assert response.status_code == 404
        assert response.json()["detail"]["code"] == "PEDALBOARD_NOT_FOUND"


class TestPedalboardRenameIntegration:
    """Integration tests for PUT /api/v1/pedalboards/{id}/rename endpoint."""

    def test_rename_missing_name(self, mod_api_server):
        """Test renaming without name returns 400."""
        response = httpx.put(
            f"{mod_api_server}/pedalboards/1/rename",
            json={}
        )
        assert response.status_code == 400
        assert response.json()["detail"]["code"] == "INVALID_REQUEST"


class TestEffectsListingIntegration:
    """Integration tests for GET /api/v1/effects endpoints."""

    def test_list_effects(self, mod_api_server):
        """Test listing available effects."""
        response = httpx.get(f"{mod_api_server}/effects")
        assert response.status_code == 200
        effects = response.json()
        assert len(effects) >= 1
        # NAM plugin should be available
        nam_effects = [e for e in effects if "neural-amp-modeler" in e["uri"]]
        assert len(nam_effects) >= 1


class TestEffectInstancesIntegration:
    """Integration tests for effect instance management."""

    def test_add_effect_to_pedalboard(self, mod_api_server):
        """Test adding an effect to a pedalboard via API."""
        # First create a pedalboard
        response = httpx.post(
            f"{mod_api_server}/pedalboards",
            json={"name": "Test Pedalboard", "duplicate_current": False}
        )
        assert response.status_code == 201
        pedalboard = response.json()

        # Add effect
        response = httpx.post(
            f"{mod_api_server}/pedalboards/{pedalboard['id']}/effects",
            json={"effect_uri": NAM_PLUGIN_URI, "name": "NAM"}
        )
        assert response.status_code == 201
        effect = response.json()
        assert effect["uri"] == NAM_PLUGIN_URI
        assert effect["id"] >= 0


class TestConnectionsIntegration:
    """Integration tests for connection management."""

    def test_create_connection(self, mod_api_server):
        """Test creating an audio connection via API."""
        # Setup: create pedalboard and add effect
        response = httpx.post(
            f"{mod_api_server}/pedalboards",
            json={"name": "Connection Test", "duplicate_current": False}
        )
        assert response.status_code == 201
        pb = response.json()

        # Add effect
        response = httpx.post(
            f"{mod_api_server}/pedalboards/{pb['id']}/effects",
            json={"effect_uri": NAM_PLUGIN_URI}
        )
        assert response.status_code == 201
        effect = response.json()

        # Create connection
        response = httpx.post(
            f"{mod_api_server}/pedalboards/{pb['id']}/connections",
            json={
                "input_port_id": "system:capture_1",
                "output_port_id": f"effect_{effect['id']}:input"
            }
        )
        assert response.status_code == 201
        assert "id" in response.json()


class TestParametersIntegration:
    """Integration tests for parameter management."""

    def test_set_parameter_on_effect(self, mod_api_server):
        """Test setting a parameter value on an effect instance."""
        # Setup: create pedalboard, add effect
        response = httpx.post(
            f"{mod_api_server}/pedalboards",
            json={"name": "Param Test", "duplicate_current": False}
        )
        pb = response.json()

        response = httpx.post(
            f"{mod_api_server}/pedalboards/{pb['id']}/effects",
            json={"effect_uri": NAM_PLUGIN_URI}
        )
        assert response.status_code == 201
        effect = response.json()

        # Set model parameter (parameter name is the URI fragment "model")
        response = httpx.put(
            f"{mod_api_server}/pedalboards/{pb['id']}/effects/{effect['id']}/parameters/model",
            json={"value": TEST_MODEL_PATH}
        )
        assert response.status_code == 200

    def test_set_parameter_out_of_range(self, mod_api_server):
        """Test setting a parameter outside min/max returns 400."""
        # Setup: create pedalboard, add effect
        response = httpx.post(
            f"{mod_api_server}/pedalboards",
            json={"name": "Range Test", "duplicate_current": False}
        )
        pb = response.json()

        response = httpx.post(
            f"{mod_api_server}/pedalboards/{pb['id']}/effects",
            json={"effect_uri": NAM_PLUGIN_URI}
        )
        assert response.status_code == 201
        effect = response.json()

        # Set quality_scale to value > 1.0 (max is 1.0)
        response = httpx.put(
            f"{mod_api_server}/pedalboards/{pb['id']}/effects/{effect['id']}/parameters/quality_scale",
            json={"value": 2.0}
        )
        assert response.status_code == 400
        assert response.json()["detail"]["code"] == "INVALID_PARAMETER"