from qgis.core import (
    QgsProcessingParameterBoolean,
    QgsProcessingParameterEnum,
    QgsProcessingParameterFile,
    QgsProcessingParameterNumber,
)

from .clutter import CLUTTER_MODEL_OPTIONS, CLUTTER_OVERRIDE_OPTIONS
from .constants import K_FACTOR_PRESETS_OPTIONS
from .defaults import (
    DEFAULT_BEL_ELEVATION_ANGLE_DEG,
    DEFAULT_CABLE_LOSS_DB,
    DEFAULT_CLUTTER_PERCENTILE,
    DEFAULT_EPSILON,
    DEFAULT_K_FACTOR,
    DEFAULT_N0,
    DEFAULT_RX_GAIN_DBI,
    DEFAULT_RX_SENSITIVITY_DBM,
    DEFAULT_SIGMA,
    DEFAULT_STREET_WIDTH_M,
    DEFAULT_TX_GAIN_DBI,
    DEFAULT_TX_POWER_DBM,
)
from .radio import ITM_MIN_N0, ITM_MAX_N0, ITM_MIN_SIGMA

_DBL = QgsProcessingParameterNumber.Type.Double

BEL_BUILDING_TYPE_OPTIONS = ["Traditional", "Thermally-efficient"]


def add_advanced_param(algorithm, attr, label, default, min_val=None, max_val=None):
    kwargs = {"type": _DBL, "defaultValue": default}
    if min_val is not None:
        kwargs["minValue"] = min_val
    if max_val is not None:
        kwargs["maxValue"] = max_val
    param = QgsProcessingParameterNumber(attr, label, **kwargs)
    param.setFlags(param.flags() | QgsProcessingParameterNumber.Flag.FlagAdvanced)
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
    algorithm.addParameter(QgsProcessingParameterNumber(
        ag("CCH_OVERRIDE"),
        "Canopy/clutter height override (m, 0 = auto)",
        type=QgsProcessingParameterNumber.Type.Double,
        defaultValue=0.0, minValue=0.0, optional=True,
    ))
    algorithm.addParameter(QgsProcessingParameterNumber(
        ag("CLUTTER_PERCENTILE"),
        "Clutter loss percentile (0.01–99.99)",
        type=QgsProcessingParameterNumber.Type.Double,
        defaultValue=DEFAULT_CLUTTER_PERCENTILE,
        minValue=0.01, maxValue=99.99, optional=True,
    ))
    algorithm.addParameter(QgsProcessingParameterNumber(
        ag("STREET_WIDTH"),
        "Street width for P.2108 §3.1 (m)",
        type=QgsProcessingParameterNumber.Type.Double,
        defaultValue=DEFAULT_STREET_WIDTH_M,
        minValue=5.0, maxValue=100.0, optional=True,
    ))
    algorithm.addParameter(QgsProcessingParameterBoolean(
        ag("BEL_ENABLED"),
        "Building entry loss (P.2109)",
        defaultValue=False, optional=True,
    ))
    algorithm.addParameter(QgsProcessingParameterEnum(
        ag("BEL_BUILDING_TYPE"),
        "Building type (P.2109)",
        options=BEL_BUILDING_TYPE_OPTIONS, defaultValue=0))
    algorithm.addParameter(QgsProcessingParameterNumber(
        ag("BEL_ELEVATION_ANGLE"),
        "Building entry elevation angle (degrees)",
        type=QgsProcessingParameterNumber.Type.Double,
        defaultValue=DEFAULT_BEL_ELEVATION_ANGLE_DEG,
        minValue=0.0, maxValue=90.0, optional=True,
    ))


def add_link_budget_params(algorithm, attr_getter=None, prefix=""):
    ag = attr_getter or (lambda name: getattr(algorithm, name))
    p = f"{prefix} " if prefix else ""
    algorithm.addParameter(QgsProcessingParameterNumber(
        ag("TX_POWER"), f"{p}TX power (dBm)",
        type=_DBL, defaultValue=DEFAULT_TX_POWER_DBM))
    algorithm.addParameter(QgsProcessingParameterNumber(
        ag("TX_GAIN"), f"{p}TX antenna gain (dBi)",
        type=_DBL, defaultValue=DEFAULT_TX_GAIN_DBI))
    algorithm.addParameter(QgsProcessingParameterNumber(
        ag("RX_GAIN"), f"{p}RX antenna gain (dBi)",
        type=_DBL, defaultValue=DEFAULT_RX_GAIN_DBI))
    algorithm.addParameter(QgsProcessingParameterNumber(
        ag("CABLE_LOSS"), f"{p}Cable loss (dB)",
        type=_DBL, defaultValue=DEFAULT_CABLE_LOSS_DB, minValue=0.0))
    algorithm.addParameter(QgsProcessingParameterNumber(
        ag("RX_SENSITIVITY"), f"{p}RX sensitivity (dBm)",
        type=_DBL, defaultValue=DEFAULT_RX_SENSITIVITY_DBM))


def add_advanced_itm_params(algorithm, attr_getter=None, include_k_factor=True, prefix=""):
    ag = attr_getter or (lambda name: getattr(algorithm, name))
    label_prefix = f"{prefix} " if prefix else ""
    if include_k_factor:
        algorithm.addParameter(QgsProcessingParameterEnum(
            ag("K_FACTOR_PRESET"), f"{label_prefix}Earth radius factor preset (k)",
            options=K_FACTOR_PRESETS_OPTIONS, defaultValue=2))
        add_advanced_param(algorithm, ag("K_FACTOR"),
            f"{label_prefix}Custom Earth radius factor (k)",
            DEFAULT_K_FACTOR, min_val=0.1)
    add_advanced_param(algorithm, ag("N0"),
        f"{label_prefix}Surface refractivity N0 (N-units)", DEFAULT_N0,
        min_val=ITM_MIN_N0, max_val=ITM_MAX_N0)
    add_advanced_param(algorithm, ag("EPSILON"),
        f"{label_prefix}Earth permittivity (epsilon)", DEFAULT_EPSILON, min_val=1.0)
    add_advanced_param(algorithm, ag("SIGMA"),
        f"{label_prefix}Earth conductivity (sigma, S/m)", DEFAULT_SIGMA,
        min_val=ITM_MIN_SIGMA)