
class GMOS_BIAS(DataClassification):
    name="GMOS_BIAS"
    usage = ""
    parent = "GMOS_IMAGE"
    requirement = ISCLASS("GMOS") & PHU(OBSTYPE="BIAS")

newtypes.append(GMOS_BIAS())
