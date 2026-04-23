# -*- coding: utf-8 -*-
"""Shared helpers for NoWires 3D scene support."""

from qgis.core import Qgis, QgsProject, QgsRasterDemTerrainProvider


SCENE_MODE_LOCAL = "local"
SCENE_MODE_GLOBE = "globe"
PROJECT_SCOPE = "NoWires"
COVERAGE_LAYER_KEY = "last_coverage_layer_id"
DEM_LAYER_KEY = "last_dem_layer_id"
CONTOUR_LAYER_KEY = "last_contour_layer_id"
VIEW_NAME_PREFIX = "NoWires 3D View"


def remember_nowires_3d_layers(
    project, dem_layer=None, coverage_layer=None, contour_layer=None
):
    """Store the latest NoWires layers used for opening a 3D scene."""
    entries = {
        DEM_LAYER_KEY: dem_layer.id() if dem_layer else "",
        COVERAGE_LAYER_KEY: coverage_layer.id() if coverage_layer else "",
        CONTOUR_LAYER_KEY: contour_layer.id() if contour_layer else "",
    }
    for key, value in entries.items():
        if value:
            project.writeEntry(PROJECT_SCOPE, key, value)


def resolve_nowires_3d_layers(project):
    """Resolve the latest stored NoWires layer ids back to project layers."""
    layer_ids = {}
    for key in (DEM_LAYER_KEY, COVERAGE_LAYER_KEY, CONTOUR_LAYER_KEY):
        layer_id, ok = project.readEntry(PROJECT_SCOPE, key, "")
        layer_ids[key] = layer_id if ok else ""
    return {
        "dem_layer": project.mapLayer(layer_ids[DEM_LAYER_KEY]),
        "coverage_layer": project.mapLayer(layer_ids[COVERAGE_LAYER_KEY]),
        "contour_layer": project.mapLayer(layer_ids[CONTOUR_LAYER_KEY]),
    }


def _set_layer_visible(project, layer):
    """Ensure a layer is visible in the project layer tree when present."""
    if layer is None:
        return
    node = project.layerTreeRoot().findLayer(layer.id())
    if node is not None:
        node.setItemVisibilityChecked(True)


def configure_contours_for_3d(layer, elevation_field="ELEV"):
    """Apply terrain-aware elevation settings to contour output."""
    props = layer.elevationProperties()
    props.setClamping(Qgis.AltitudeClamping.Terrain)
    props.setBinding(Qgis.AltitudeBinding.Vertex)
    if hasattr(props, "setZOffsetExpression"):
        props.setZOffsetExpression('coalesce("{field}", 0)'.format(field=elevation_field))
    return layer


def _next_3d_view_name(iface):
    """Generate a unique 3D view name for the current QGIS session."""
    existing = []
    if hasattr(iface, "mapCanvases3D"):
        existing = iface.mapCanvases3D() or []
    return "{} {}".format(VIEW_NAME_PREFIX, len(existing) + 1)


def open_nowires_3d_view(iface, scene_mode=SCENE_MODE_LOCAL):
    """Create a new QGIS 3D map canvas using the latest NoWires layers."""
    project = QgsProject.instance()
    layers = resolve_nowires_3d_layers(project)
    dem_layer = layers["dem_layer"]
    coverage_layer = layers["coverage_layer"]
    contour_layer = layers["contour_layer"]

    if dem_layer is None:
        iface.messageBar().pushWarning(
            "NoWires",
            "No DEM layer found for 3D. Run Coverage Analysis or Contour Lines first.",
        )
        return None

    if contour_layer is not None:
        configure_contours_for_3d(contour_layer, elevation_field="ELEV")
        _set_layer_visible(project, contour_layer)
    if coverage_layer is not None:
        _set_layer_visible(project, coverage_layer)
    _set_layer_visible(project, dem_layer)

    scene = (
        Qgis.SceneMode.Globe
        if scene_mode == SCENE_MODE_GLOBE
        else Qgis.SceneMode.Local
    )
    canvas = iface.createNewMapCanvas3D(_next_3d_view_name(iface), scene)

    if hasattr(project, "elevationProperties"):
        elevation_props = project.elevationProperties()
        if elevation_props is not None and hasattr(elevation_props, "setTerrainProvider"):
            provider = QgsRasterDemTerrainProvider()
            provider.setLayer(dem_layer)
            elevation_props.setTerrainProvider(provider)

            settings = canvas.mapSettings()
            if hasattr(settings, "configureTerrainFromProject"):
                extent = (
                    iface.mapCanvas().fullExtent()
                    if hasattr(iface, "mapCanvas") and iface.mapCanvas() is not None
                    else dem_layer.extent()
                )
                settings.configureTerrainFromProject(elevation_props, extent)

    canvas.resetView()
    return canvas
