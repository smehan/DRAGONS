# this is added to the reduction object dictionary, but only one
# reduction object per astro data type.
# NOTE: primitives are the member functions of a Reduction Object.

localPrimitiveIndex = {
    # "GEMINI": ("primitives_GEMINI.py", "GEMINIPrimitives"),
    "GMOS": ("primitives_GMOS.py", "GMOSPrimitives"),
    "GMOS_IMAGE": ("primitives_GMOS_IMAGE.py", "GMOS_IMAGEPrimitives"),
    "GMOS_SPECT": ("primitives_GMOS_SPECT.py", "GMOS_SPECTPrimitives")
    }
