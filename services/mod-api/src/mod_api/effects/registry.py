"""Registry of available LV2 effects."""

import os
from pathlib import Path
from typing import Optional

from rdflib import Graph, Namespace, URIRef, Literal
from rdflib.namespace import RDF, RDFS

from ..models import EffectInfo, NumberParameterType, FilenameParameterType, Port


# LV2 namespace
LV2 = Namespace("http://lv2plug.in/ns/lv2core#")
DOAP = Namespace("http://usefulinc.com/ns/doap#")


class EffectsRegistry:
    """Registry of available LV2 effects.

    Maintains a catalog of effect types that can be instantiated on pedalboards.
    Discovers effects by parsing LV2 plugin manifests from the LV2_PATH.

    Attributes:
        _effects: Dictionary mapping URIs to EffectInfo objects.
    """

    def __init__(self) -> None:
        """Initialize the effects registry.

        Sets up an empty effects catalog that will be populated on discover().
        """
        self._effects: dict[str, EffectInfo] = {}

    def discover(self) -> list[EffectInfo]:
        """Discover available LV2 effects.

        Scans the LV2_PATH environment variable (or default /usr/lib/lv2) to find
        available plugin manifests and parses them into EffectInfo objects.

        Returns:
            List of EffectInfo objects for all available effects.
        """
        self._effects = {}

        for plugin_dir in self._scan_lv2_path():
            effect_info = self._parse_plugin_manifest(plugin_dir)
            if effect_info:
                self._effects[effect_info.uri] = effect_info

        return list(self._effects.values())

    def get(self, uri: str) -> Optional[EffectInfo]:
        """Get effect info by URI.

        Args:
            uri: The full URI of the effect to retrieve.

        Returns:
            EffectInfo if found in the registry, None otherwise.
        """
        return self._effects.get(uri)

    def get_all(self) -> list[EffectInfo]:
        """Get all available effects.

        Returns:
            List of all EffectInfo objects in the registry.
        """
        return list(self._effects.values())

    def _parse_plugin_manifest(self, plugin_dir: str) -> Optional[EffectInfo]:
        """Parse an LV2 plugin directory.

        Extracts plugin URI, name, port definitions, and parameters from an
        LV2 plugin directory containing manifest.ttl and plugin.ttl files.

        Args:
            plugin_dir: Path to the plugin directory.

        Returns:
            EffectInfo if parsing succeeds, None otherwise.
        """
        plugin_path = Path(plugin_dir)
        manifest_ttl = plugin_path / "manifest.ttl"
        # LV2 convention: plugin.ttl is named after directory (e.g., neural_amp_modeler.lv2 -> neural_amp_modeler.ttl)
        plugin_ttl_name = plugin_path.name
        if plugin_ttl_name.endswith(".lv2"):
            plugin_ttl_name = plugin_ttl_name[:-4]
        plugin_ttl = plugin_path / f"{plugin_ttl_name}.ttl"

        # Read manifest.ttl for URI
        if not manifest_ttl.exists():
            return None

        graph = Graph()
        graph.parse(manifest_ttl, format="turtle")

        # Find the plugin URI
        plugin_uri = None
        for subject in graph.subjects(RDF.type, LV2.Plugin):
            plugin_uri = str(subject)
            break

        # Fallback: try to find any URI that looks like a plugin
        if not plugin_uri:
            for subject in graph.subjects(predicate=None, object=None):
                uri_str = str(subject)
                if "#" in uri_str or "/" in uri_str:
                    plugin_uri = uri_str
                    break

        if not plugin_uri:
            return None

        # Parse the plugin.ttl for full details
        name = None
        ports = []
        parameters = {}

        if plugin_ttl.exists():
            graph.parse(plugin_ttl, format="turtle")

            # Find the plugin name - try doap:name first, then lv2:name, then rdfs:label
            for plugin_subject in graph.subjects(RDF.type, LV2.Plugin):
                for plugin_name in graph.objects(plugin_subject, DOAP.name):
                    name = str(plugin_name)
                    break
                if not name:
                    for plugin_name in graph.objects(plugin_subject, LV2.name):
                        name = str(plugin_name)
                        break
                if not name:
                    for plugin_name in graph.objects(plugin_subject, RDFS.label):
                        name = str(plugin_name)
                        break
                break

            # Extract ports from lv2:port blank nodes
            for port_node in graph.objects(subject=URIRef(plugin_uri), predicate=LV2.port):
                port_info = self._parse_port_node(graph, port_node)
                if port_info:
                    if port_info["type"] == "input":
                        ports.append(Port(name=port_info["name"], type="input"))
                    elif port_info["type"] == "output":
                        ports.append(Port(name=port_info["name"], type="output"))
                    elif port_info["type"] == "parameter":
                        parameters[port_info["name"]] = port_info["parameter"]

            # Also check for Parameters defined as separate subjects (like NAM's model param)
            for param_subject in graph.subjects(RDF.type, LV2.Parameter):
                param_info = self._parse_parameter_subject(graph, param_subject)
                if param_info:
                    parameters[param_info["name"]] = param_info["parameter"]

        if not name:
            name = plugin_uri.split("/")[-1]

        return EffectInfo(
            uri=plugin_uri,
            name=name,
            ports=ports,
            parameters=parameters
        )

    def _parse_port_node(self, graph: Graph, port_node) -> Optional[dict]:
        """Parse a port blank node for port info.

        Returns a dict with 'name', 'type', and optionally 'parameter' keys.
        """
        # Get port name
        name = None
        for symbol in graph.objects(port_node, LV2.symbol):
            name = str(symbol)
            break
        if not name:
            for lv2_name in graph.objects(port_node, LV2.name):
                name = str(lv2_name)
                break

        if not name:
            return None

        # Check for AudioPort - these are input/output ports
        types = [str(t) for t in graph.objects(port_node, RDF.type)]

        # Check if any type URI contains these class names
        has_audio = any("AudioPort" in t for t in types)
        has_input = any("InputPort" in t for t in types)
        has_output = any("OutputPort" in t for t in types)
        has_control = any("ControlPort" in t for t in types)
        has_atom = any("AtomPort" in t for t in types)

        if has_audio and has_input:
            return {"name": name, "type": "input"}
        if has_audio and has_output:
            return {"name": name, "type": "output"}

        # Check for ControlPort - these are parameters (skip AtomPort for now)
        if has_control and not has_atom:
            return {
                "name": name,
                "type": "parameter",
                "parameter": self._create_parameter_from_port(graph, port_node, name)
            }

        return None

    def _create_parameter_from_port(self, graph: Graph, port_node, name: str):
        """Create a ParameterType from a ControlPort node."""
        # Check for range property to determine type
        for range_val in graph.objects(port_node, RDFS.range):
            range_type = str(range_val)
            if "Path" in range_type or "String" in range_type:
                return FilenameParameterType(name=name, default="")

        # Default to numeric parameter
        min_val = 0.0
        max_val = 1.0
        default_val = 0.5

        for minimum in graph.objects(port_node, LV2.minimum):
            min_val = float(minimum)
            break

        for maximum in graph.objects(port_node, LV2.maximum):
            max_val = float(maximum)
            break

        for default in graph.objects(port_node, LV2.default):
            default_val = float(default)
            break

        return NumberParameterType(
            name=name,
            min=min_val,
            max=max_val,
            default=default_val
        )

    def _parse_parameter_subject(self, graph: Graph, param_subject) -> Optional[dict]:
        """Parse a standalone Parameter subject.

        Uses the URI fragment (e.g., "model") as the parameter name for compatibility
        with LV2 Patch protocol, rather than the rdfs:label which may contain spaces.

        Returns a dict with 'name' and 'parameter' keys.
        """
        # Get parameter name from URI fragment (e.g., "model" from #model)
        # This is needed for patch_set which requires the actual URI fragment
        subject_uri = str(param_subject)
        if "#" in subject_uri:
            name = subject_uri.split("#")[-1]
        else:
            name = subject_uri.split("/")[-1]

        if not name:
            return None

        # Check for range property
        for range_val in graph.objects(param_subject, RDFS.range):
            range_type = str(range_val)
            if "Path" in range_type:
                return {"name": name, "parameter": FilenameParameterType(name=name, default="")}

        # Default to numeric
        return {"name": name, "parameter": NumberParameterType(name=name, min=0.0, max=1.0, default=0.5)}

    def _scan_lv2_path(self) -> list[str]:
        """Scan the LV2_PATH for plugin directories.

        Scans standard locations: /usr/lib/lv2, /usr/local/lib/lv2, and LV2_PATH env var.

        Returns:
            List of plugin directory paths.
        """
        plugin_dirs = []

        for lv2_path in ["/usr/lib/lv2", "/usr/local/lib/lv2", os.environ.get("LV2_PATH", "")]:
            if lv2_path and os.path.exists(lv2_path):
                for d in os.listdir(lv2_path):
                    plugin_dir = os.path.join(lv2_path, d)
                    if os.path.isdir(plugin_dir):
                        manifest = os.path.join(plugin_dir, "manifest.ttl")
                        if os.path.exists(manifest):
                            plugin_dirs.append(plugin_dir)

        return plugin_dirs