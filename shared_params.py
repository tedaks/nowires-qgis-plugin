from qgis.core import (
    QgsProcessingParameterEnum,
    QgsProcessingParameterFile,
    QgsProcessingParameterNumber,
)

from .antenna import ANTENNA_PRESET_OPTIONS
from .clutter import CLUTTER_MODEL_OPTIONS, CLUTTER_OVERRIDE_OPTIONS
from .constants import K_FACTOR_PRESETS_OPTIONS
from .radio import ITM_MIN_N0, ITM_MAX_N0, ITM_MIN_SIGMA

_DBL = QgsProcessingParameterNumber.Double


def add_advanced_param(algorithm, attr, label, default, min_val=None, max_val=None):
    kwargs = {"type": _DBL, "defaultValue": default}
    if min_val is not None:
        kwargs["minValue"] = min_val
    if max_val is not None:
        kwargs["maxValue"] = max_val
    param = QgsProcessingParameterNumber(attr, label, **kwargs)
    param.setFlags(param.flags() | QgsProcessingParameterNumber.FlagAdvanced)
    algorithm.addParameter(param)


def add_clutter_params(algorithm, attr_getter=None):
    ag = attr_getter or (lambda name: getattr(algorithm, name))
    algorithm.addParameter(QgsProcessingParameterEnum(
        ag("CLUTTER_MODEL"), "Clutter correction",
        options=CLUTTER_MODEL_OPTIONS, defaultValue=0))
    algorithm.addParameter(QgsProcessingParameterFile(
        ag("CLUTTER_RASTER"), "Land-cover raster (auto-downloaded if blank)",
        extension="tif", optional=True))
    algorithm.addParameter(QgsProcessingParameterEnum(
        ag("TX_CLUTTER_OVERRIDE"), "TX clutter override",
        options=CLUTTER_OVERRIDE_OPTIONS, defaultValue=0))
    algorithm.addParameter(QgsProcessingParameterEnum(
        ag("RX_CLUTTER_OVERRIDE"), "RX clutter override",
        options=CLUTTER_OVERRIDE_OPTIONS, defaultValue=0))


def add_link_budget_params(algorithm, attr_getter=None, prefix=""):
    ag = attr_getter or (lambda name: getattr(algorithm, name))
    p = f"{prefix} " if prefix else ""
    algorithm.addParameter(QgsProcessingParameterNumber(
        ag("TX_POWER"), f"{p}TX power (dBm)",
        type=_DBL, defaultValue=43.0))
    algorithm.addParameter(QgsProcessingParameterNumber(
        ag("TX_GAIN"), f"{p}TX antenna gain (dBi)",
        type=_DBL, defaultValue=8.0))
    algorithm.addParameter(QgsProcessingParameterNumber(
        ag("RX_GAIN"), f"{p}RX antenna gain (dBi)",
        type=_DBL, defaultValue=2.0))
    algorithm.addParameter(QgsProcessingParameterNumber(
        ag("CABLE_LOSS"), f"{p}Cable loss (dB)",
        type=_DBL, defaultValue=2.0, minValue=0.0))
    algorithm.addParameter(QgsProcessingParameterNumber(
        ag("RX_SENSITIVITY"), f"{p}RX sensitivity (dBm)",
        type=_DBL, defaultValue=-100.0))


def add_advanced_itm_params(algorithm, attr_getter=None, include_k_factor=True, prefix=""):
    ag = attr_getter or (lambda name: getattr(algorithm, name))
    label_prefix = f"{prefix} " if prefix else ""
    if include_k_factor:
        algorithm.addParameter(QgsProcessingParameterEnum(
            ag("K_FACTOR_PRESET"), f"{label_prefix}Earth radius factor preset (k)",
            options=K_FACTOR_PRESETS_OPTIONS, defaultValue=2))
        add_advanced_param(algorithm, ag("K_FACTOR"),
            f"{label_prefix}Custom Earth radius factor (k)",
            4.0 / 3.0, min_val=0.1)
    add_advanced_param(algorithm, ag("N0"),
        f"{label_prefix}Surface refractivity N0 (N-units)", 301.0,
        min_val=ITM_MIN_N0, max_val=ITM_MAX_N0)
    add_advanced_param(algorithm, ag("EPSILON"),
        f"{label_prefix}Earth permittivity (epsilon)", 15.0, min_val=1.0)
    add_advanced_param(algorithm, ag("SIGMA"),
        f"{label_prefix}Earth conductivity (sigma, S/m)", 0.005,
        min_val=ITM_MIN_SIGMA)