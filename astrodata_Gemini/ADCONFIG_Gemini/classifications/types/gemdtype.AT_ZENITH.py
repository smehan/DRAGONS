
class AT_ZENITH(AZEL_TARGET):
    name="AT_ZENITH"
    usage = "Data taken at Zenith in the AZEL_TOPO co-ordinate system"
    
    parent = "AZEL_TARGET"
    requirement = PHU(FRAME='AZEL_TOPO') & PHU(ELEVATIO='90.*')

newtypes.append(AT_ZENITH())
