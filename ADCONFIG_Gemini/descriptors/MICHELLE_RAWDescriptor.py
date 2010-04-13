from astrodata import Lookups
from astrodata import Descriptors
import re
import math

import astrodata
from astrodata.Calculator import Calculator

import GemCalcUtil 
from StandardMICHELLEKeyDict import stdkeyDictMICHELLE

class MICHELLE_RAWDescriptorCalc(Calculator):

    def airmass(self, dataset, **args):
        """
        Return the airmass value for MICHELLE
        @param dataset: the data set
        @type dataset: AstroData
        @rtype: float
        @return: the mean airmass for the observation
        """
        try:
            hdu = dataset.hdulist
            retairmassfloat = hdu[0].header[stdkeyDictMICHELLE["key_michelle_airmass"]]
        
        except KeyError:
            return None
        
        return float(retairmassfloat)
    
    def camera(self, dataset, **args):
        """
        Return the camera value for MICHELLE
        @param dataset: the data set
        @type dataset: AstroData
        @rtype: string
        @return: the camera used to acquire the data
        """
        try:
            hdu = dataset.hdulist
            retcamerastring = hdu[0].header[stdkeyDictMICHELLE["key_michelle_camera"]]
        
        except KeyError:
            return None
        
        return str(retcamerastring)
    
    def cwave(self, dataset, **args):
        """
        Return the cwave value for MICHELLE
        @param dataset: the data set
        @type dataset: AstroData
        @rtype: float
        @return: the central wavelength (nanometers)
        """
        try:
            hdu = dataset.hdulist
            retcwavefloat = hdu[0].header[stdkeyDictMICHELLE["key_michelle_cwave"]]
        
        except KeyError:
            return None
        
        return float(retcwavefloat)
    
    def datasec(self, dataset, **args):
        """
        Return the datasec value for MICHELLE
        @param dataset: the data set
        @type dataset: AstroData
        @rtype: string
        @return: the data section
        """
        retdatasecstring = None
        
        return str(retdatasecstring)
    
    def detsec(self, dataset, **args):
        """
        Return the detsec value for MICHELLE
        @param dataset: the data set
        @type dataset: AstroData
        @rtype: string
        @return: the detector section
        """
        retdetsecstring = None
        
        return str(retdetsecstring)
    
    def disperser(self, dataset, stripID=False, pretty=False, **args):
        """
        Return the disperser value for MICHELLE
        @param dataset: the data set
        @type dataset: AstroData
        @rtype: string
        @return: the disperser / grating used to acquire the data
        """
        # The Michelle components don't have component IDs so we just ignore the stripID and pretty options
        try:
            hdu = dataset.hdulist
            retdisperserstring = hdu[0].header[stdkeyDictMICHELLE["key_michelle_disperser"]]
        
        except KeyError:
            return None
        
        return str(retdisperserstring)
    
    def exptime(self, dataset, **args):
        """
        Return the exptime value for MICHELLE
        @param dataset: the data set
        @type dataset: AstroData
        @rtype: float
        @return: the total exposure time of the observation (seconds)
        """
        try:
            hdu = dataset.hdulist
            exposure = float(hdu[0].header[stdkeyDictMICHELLE["key_michelle_exposure"]])
            numexpos = float (hdu[0].header[stdkeyDictMICHELLE["key_michelle_numexpos"]])
            numext = float(hdu[0].header[stdkeyDictMICHELLE["key_michelle_numext"]])

            retexptimefloat = exposure * numexpos * numext
        
        except KeyError:
            return None
        
        return float(retexptimefloat)
    
    def filterid(self, dataset, **args):
        """
        Return the filterid value for MICHELLE
        @param dataset: the data set
        @type dataset: AstroData
        @rtype: string
        @return: the unique filter ID number string
        """
        retfilteridstring = None
        
        return str(retfilteridstring)
    
    def filtername(self, dataset, stripID=False, pretty=False, **args):
        """
        Return the filtername value for MICHELLE
        @param dataset: the data set
        @type dataset: AstroData
        @rtype: string
        @return: the unique filter identifier string
        """
        # The Michelle filters don't have ID strings, so we just ignore the stripID and pretty options
        try:
            hdu = dataset.hdulist
            filter = hdu[0].header[stdkeyDictMICHELLE["key_michelle_filter"]]
            
            if filter == "NBlock":
                retfilternamestring = "blank"
            else:
                retfilternamestring = filter
            
        except KeyError:
            return None
        
        return str(retfilternamestring)
    
    def fpmask(self, dataset, **args):
        """
        Return the fpmask value for MICHELLE
        @param dataset: the data set
        @type dataset: AstroData
        @rtype: string
        @return: the focal plane mask used to acquire the data
        """
        try:
            hdu = dataset.hdulist
            retfpmaskstring = hdu[0].header[stdkeyDictMICHELLE["key_michelle_fpmask"]]
        
        except KeyError:
            return None
                        
        return str(retfpmaskstring)
    
    def gain(self, dataset, **args):
        """
        Return the gain value for MICHELLE
        @param dataset: the data set
        @type dataset: AstroData
        @rtype: float
        @returns: the gain (electrons/ADU)
        """
        try:
            hdu = dataset.hdulist
            retgainfloat = hdu[0].header[stdkeyDictMICHELLE["key_michelle_gain"]]
        
        except KeyError:
            return None
        
        return float(retgainfloat)
    
    def instrument(self, dataset, **args):
        """
        Return the instrument value for MICHELLE
        @param dataset: the data set
        @type dataset: AstroData
        @rtype: string
        @return: the instrument used to acquire the data
        """
        try:
            hdu = dataset.hdulist
            retinstrumentstring = hdu[0].header[stdkeyDictMICHELLE["key_michelle_instrument"]]
        
        except KeyError:
            return None
                        
        return str(retinstrumentstring)
    
    def mdfrow(self, dataset, **args):
        """
        Return the mdfrow value for MICHELLE
        @param dataset: the data set
        @type dataset: AstroData
        @rtype: integer
        @return: the corresponding reference row in the MDF
        """
        retmdfrowint = None
        
        return retmdfrowint
    
    def nonlinear(self, dataset, **args):
        """
        Return the nonlinear value for MICHELLE
        @param dataset: the data set
        @type dataset: AstroData
        @rtype: integer
        @returns: the non-linear level in the raw images (ADU)
        """
        retnonlinearint = None
        
        return retnonlinearint
    
    def nsciext(self, dataset, **args):
        """
        Return the nsciext value for MICHELLE
        @param dataset: the data set
        @type dataset: AstroData
        @rtype: integer
        @return: the number of science extensions
        """
        try:
            hdu = dataset.hdulist
            retnsciextint = hdu[0].header[stdkeyDictMICHELLE["key_michelle_nsciext"]]

        except KeyError:
            return None
        
        return int(retnsciextint)
    
    def object(self, dataset, **args):
        """
        Return the object value for MICHELLE
        @param dataset: the data set
        @type dataset: AstroData
        @rtype: string
        @return: the name of the object acquired
        """
        try:
            hdu = dataset.hdulist
            retobjectstring = hdu[0].header[stdkeyDictMICHELLE["key_michelle_object"]]
        
        except KeyError:
            return None
                        
        return str(retobjectstring)
    
    def obsmode(self, dataset, **args):
        """
        Return the obsmode value for MICHELLE
        @param dataset: the data set
        @type dataset: AstroData
        @rtype: string
        @returns: the observing mode
        """
        try:
            hdu = dataset.hdulist
            retobsmodestring = hdu[0].header[stdkeyDictMICHELLE["key_michelle_obsmode"]]
        
        except KeyError:
            return None
        
        return str(retobsmodestring)
    
    def pixscale(self, dataset, **args):
        """
        Return the pixscale value for MICHELLE
        @param dataset: the data set
        @type dataset: AstroData
        @rtype: float
        @returns: the pixel scale (arcsec/pixel)
        """
        try:
            hdu = dataset.hdulist
            retpixscalefloat = hdu[0].header[stdkeyDictMICHELLE["key_michelle_pixscale"]]
        
        except KeyError:
            return None
        
        return float(retpixscalefloat)
    
    def pupilmask(self, dataset, **args):
        """
        Return the pupilmask value for MICHELLE
        @param dataset: the data set
        @type dataset: AstroData
        @rtype: string
        @returns: the pupil mask used to acquire data
        """
        retpupilmaskstring = None
        
        return str(retpupilmaskstring)
    
    def rdnoise(self, dataset, **args):
        """
        Return the rdnoise value for MICHELLE
        @param dataset: the data set
        @type dataset: AstroData
        @rtype: float
        @returns: the estimated readout noise
        """
        retrdnoisefloat = None
        
        return retrdnoisefloat
    
    def satlevel(self, dataset, **args):
        """
        Return the satlevel value for MICHELLE
        @param dataset: the data set
        @type dataset: AstroData
        @rtype: integer
        @returns: the saturation level in the raw images (ADU)
        """
        retsaturationint = None
        
        return retsaturationint
    
    def utdate(self, dataset, **args):
        """
        Return the utdate value for MICHELLE
        @param dataset: the data set
        @type dataset: AstroData
        @rtype: string
        @returns: the UT date of the observation (YYYY-MM-DD)
        """
        try:
            hdu = dataset.hdulist
            retutdatestring = hdu[0].header[stdkeyDictMICHELLE["key_michelle_utdate"]]
        
        except KeyError:
            return None
        
        return str(retutdatestring)
    
    def uttime(self, dataset, **args):
        """
        Return the uttime value for MICHELLE
        @param dataset: the data set
        @type dataset: AstroData
        @rtype: string
        @returns: the UT at the start of the observation (HH:MM:SS.S)
        """
        try:
            hdu = dataset.hdulist
            retuttimestring = hdu[0].header[stdkeyDictMICHELLE["key_michelle_uttime"]]
        
        except KeyError:
            return None
        
        return str(retuttimestring)
    
    def wdelta(self, dataset, **args):
        """
        Return the wdelta value for MICHELLE
        @param dataset: the data set
        @type dataset: AstroData
        @rtype: float
        @returns: the dispersion (angstroms/pixel)
        """
        try:
            hdu = dataset.hdulist
            retwdeltafloat = hdu[0].header[stdkeyDictMICHELLE["key_michelle_wdelta"]]
        
        except KeyError:
            return None
        
        return float(retwdeltafloat)
    
    def wrefpix(self, dataset, **args):
        """
        Return the wrefpix value for MICHELLE
        @param dataset: the data set
        @type dataset: AstroData
        @rtype: float
        @returns: the reference pixel of the central wavelength
        """
        retwrefpixfloat = None
        
        return retwrefpixfloat
    
    def xccdbin(self, dataset, **args):
        """
        Return the xccdbin value for MICHELLE
        @param dataset: the data set
        @type dataset: AstroData
        @rtype: integer
        @returns: the binning of the detector x-axis
        """
        retxccdbinint = None
        
        return retxccdbinint
    
    def yccdbin(self, dataset, **args):
        """
        Return the yccdbin value for MICHELLE
        @param dataset: the data set
        @type dataset: AstroData
        @rtype: integer
        @returns: the binning of the detector y-axis
        """
        retyccdbinint = None
        
        return retyccdbinint
