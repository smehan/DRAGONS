# This parameter file contains the parameters related to the primitives located
# in the primitives_preprocess.py file, in alphabetical order.
from gempy.library import config
from . import parameters_stack
from astrodata import AstroData

def replace_valueCheck(value):
    """validate applyDQPlane.replace_value"""
    return (value in ('mean', 'median') or isinstance(value, float))

class addObjectMaskToDQConfig(config.Config):
    suffix = config.Field("Filename suffix", str, "_objectMaskAdded", optional=True)

class ADUToElectronsConfig(config.Config):
    suffix = config.Field("Filename suffix", str, "_ADUToElectrons", optional=True)

class applyDQPlaneConfig(config.Config):
    suffix = config.Field("Filename suffix", str, "_dqPlaneApplied", optional=True)
    replace_flags = config.RangeField("DQ bitmask for pixels to replace", int, 65535, min=0)
    replace_value = config.Field("Replacement value [mean|median|<value>]",
                                 (str, float), "median", check=replace_valueCheck)

class associateSkyConfig(config.Config):
    suffix = config.Field("Filename suffix", str, "_skyAssociated", optional=True)
    time = config.RangeField("Maximum association time (seconds)", float, 600., min=0)
    distance = config.RangeField("Minimum association distance (arcsec)", float, 3., min=0)
    min_skies = config.RangeField("Minimum number of sky frames to associate",
                             int, 3, min=0, optional=True)
    max_skies = config.RangeField("Maximum number of sky frames to associate",
                             int, None, min=1, optional=True)
    use_all = config.Field("Use all frames as skies?", bool, False)

class correctBackgroundToReferenceConfig(config.Config):
    suffix = config.Field("Filename suffix", str, "_backgroundCorrected", optional=True)
    separate_ext = config.Field("Treat each extension separately?", bool, True)
    remove_background = config.Field("Remove background level?", bool, False)

class darkCorrectConfig(config.Config):
    suffix = config.Field("Filename suffix", str, "_darkCorrected", optional=True)
    dark = config.ListField("Dark frame", (str, AstroData), None, optional=True, single=True)
    do_dark = config.Field("Perform dark subtraction?", bool, True)

class dilateObjectMaskConfig(config.Config):
    suffix = config.Field("Filename suffix", str, "_objmaskDilated", optional=True)
    dilation = config.RangeField("Dilation radius (pixels)", float, 1., min=0)
    repeat = config.Field("Allow dilation of already-dilated image?", bool, False)

class flatCorrectConfig(config.Config):
    suffix = config.Field("Filename suffix", str, "_flatCorrected", optional=True)
    flat = config.ListField("Flatfield frame", (str, AstroData), None, optional=True, single=True)
    do_flat = config.Field("Perform flatfield correction?", bool, True)

class nonlinearityCorrectConfig(config.Config):
    suffix = config.Field("Filename suffix", str, "_nonlinearityCorrected", optional=True)

class normalizeFlatConfig(config.Config):
    suffix = config.Field("Filename suffix", str, "_normalized", optional=True)
    scale = config.ChoiceField("Statistic for scaling", str,
                               allowed = {"mean": "Scale by mean",
                                          "median": "Scale by median"},
                               default="median")
    separate_ext = config.Field("Scale extensions separately?", bool, False)

class separateSkyConfig(config.Config):
    suffix = config.Field("Filename suffix", str, "_skySeparated", optional=True)
    ref_obj = config.Field("Manually-assigned object files", str, None, optional=True)
    ref_sky = config.Field("Manually-assigned sky files", str, None, optional=True)
    frac_FOV = config.RangeField("Field of view scaling for coaddition", float, 0.9, min=0.5, max=1)

class makeSkyConfig(associateSkyConfig, separateSkyConfig):
    pass

class subtractSkyConfig(config.Config):
    suffix = config.Field("Filename suffix", str, "_skySubtracted", optional=True)
    reset_sky = config.Field("Replace lost sky counts?", bool, False)
    scale_sky = config.Field("Scale sky frame to science frame?", bool, True)
    offset_sky = config.Field("Apply offset to sky frame to match science frame?", bool, False)
    sky = config.ListField("Sky frame to subtract", (str, AstroData), None, optional=True, single=True)

class skyCorrectConfig(parameters_stack.stackSkyFramesConfig, subtractSkyConfig):
    def setDefaults(self):
        self.suffix = "_skyCorrected"

class subtractSkyBackgroundConfig(config.Config):
    suffix = config.Field("Filename suffix", str, "_skyBackgroundSubtracted", optional=True)

class thresholdFlatfieldConfig(config.Config):
    suffix = config.Field("Filename suffix", str, "_thresholdFlatfielded", optional=True)
    upper = config.RangeField("Upper limit of valid pixels", float, 10., min=1)
    lower = config.RangeField("Lower limit of valid pixels", float, 0.01, max=1)
