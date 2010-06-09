#Author: Kyle Mede, June 2010
#from Reductionobjects import Reductionobject
from primitives_GEMINI import GEMINIPrimitives
# All GEMINI IRAF task wrappers.
import time
from astrodata.adutils import filesystem
from astrodata import IDFactory
from astrodata import Descriptors
from astrodata.data import AstroData

from pyraf.iraf import tables, stsdas, images
from pyraf.iraf import gemini
import pyraf
import iqtool
from iqtool.iq import getiq
from gempy.instruments.gmos import *



import pyfits
import numdisplay
import string

yes = pyraf.iraf.yes
no = pyraf.iraf.no

# NOTE, the sys.stdout stuff is to shut up gemini and gmos startup... some primitives
# don't execute pyraf code and so do not need to print this interactive 
# package init display (it shows something akin to the dir(gmos)
import sys, StringIO, os
SAVEOUT = sys.stdout
capture = StringIO.StringIO()
sys.stdout = capture
gemini()
gemini.gmos()
sys.stdout = SAVEOUT

class GMOS_SPECTException:
    """ This is the general exception the classes and functions in the
    Structures.py module raise.
    """
    def __init__(self, msg="Exception Raised in Recipe System"):
        """This constructor takes a message to print to the user."""
        self.message = msg
    def __str__(self):
        """This str conversion member returns the message given by the user (or the default message)
        when the exception is not caught."""
        return self.message


class GMOS_SPECTPrimitives(GEMINIPrimitives):
    astrotype = "GMOS_SPECT"
    
    def init(self, rc):
        
        if "iraf" in rc and "adata" in rc["iraf"]:
            pyraf.iraf.set (adata=rc["iraf"]['adata'])  
        else:
            # @@REFERENCEIMAGE: used to set adata path for primitives
            if len(rc.inputs) > 0:
                (root, name) = os.path.split(rc.inputs[0].filename)
                pyraf.iraf.set (adata=root)
                if "iraf" not in rc:
                    rc.update({"iraf":{}})
                if "adata" not in rc["iraf"]:
                    rc["iraf"].update({"adata":root}) 
        
        GEMINIPrimitives.init(self, rc)
        return rc

    
    def display(self, rc):
        from adutils.future import gemDisplay
        import pyraf
        from pyraf import iraf
        iraf.set(stdimage='imtgmos')
        ds = gemDisplay.getDisplayService()
        for i in range(0, len(rc.inputs)):   
            inputRecord = rc.inputs[i]
            gemini.gmos.gdisplay( inputRecord.filename, i+1, fl_imexam=iraf.no,
                Stdout = rc.getIrafStdout(), Stderr = rc.getIrafStderr() )
            # this version had the display id conversion code which we'll need to redo
            # code above just uses the loop index as frame number
            #gemini.gmos.gdisplay( inputRecord.filename, ds.displayID2frame(rq.disID), fl_imexam=iraf.no,
            #    Stdout = coi.getIrafStdout(), Stderr = coi.getIrafStderr() )
        yield rc
    
    #+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
   
    #$$$$$$$$$$$$$$$$$$$$ NEW STUFF BY KYLE FOR: PREPARE $$$$$$$$$$$$$$$$$$$$$
    '''
    all the stuff in here is very much a work in progress and I will not be fully
    commenting it for others while developing it, sorry.
    '''

    def standardizeInstrumentHeaders(self,rc):
        #adds specific headers for a GMOS_SPECT file
        try:
            # 'importing' the logger and debug level    
            gemLog=rc["log"]
            
            for ad in rc.getInputs(style="AD"):
                if debugLevel>=1: 
                    print 'prim-G_I505: calling stdInstHdrs' #$$$$$$$$$$$$$$$
                stdInstHdrs(ad)
                if debugLevel>=3:  
                    # printing the updated headers
                    for ext in range(len(ad)+1):    
                        print ad.getHeaders()[ext-1] #this will loop to print the PHU and then each of the following pixel extensions
                if debugLevel>=1:          
                    print 'prim_G_I507: instrument headers fixed' 
                
        except:
            print "Problem preparing the image."
            raise 
        
        yield rc
    #-----------------------------------------------------------------------
    def attachMDF(self,rc):
        # this works to add an MDF if there is a MASKNAME in the images PHU only.  
        # will be upgraded later, early testing complete
        
        try:
            # 'importing' the logger and debug level  
            gemLog=rc["log"]
            debugLevel=int(rc['debugLevel'])
            
            if debugLevel>=1:
                print 'prepare step 2'
            
            for ad in rc.getInputs(style ='AD'):
                infilename = ad.filename
                if debugLevel>=1:
                    print 'prim_G_S162:', infilename
                #print 'prim_G_I531: ', os.path.abspath(infilename) #absolute path of input file
                #print 'prim_G_I531: ', os.path.dirname(infilename) #reletive directory of input file without /
                
                pathname = 'kyles_test_images/' #$$$$ HARDCODED FOR NOW, TILL FIX COMES FROM CRAIG
                maskname = ad.phuGetKeyValue("MASKNAME")
                if debugLevel>=1:
                    print "Pim_G_S170: maskname = ", maskname
                inMDFname = 'kyles_test_images/'+maskname +'.fits'
                if debugLevel>=1:
                    print 'Prim_G_S172: input MDF file = ', inMDFname
                admdf = AstroData(inMDFname)
                admdf.setExtname('MDF',1)  #$$$ HARDCODED EXTVER=1 FOR NOW, CHANGE LATER??
                admdf.extSetKeyValue(len(admdf)-1,'EXTNAME', 'MDF',"Extension name" )
                admdf.extSetKeyValue(len(admdf)-1,'EXTVER', 1,"Extension version" ) #$$$ HARDCODED EXTVER=1 FOR NOW, CHANGE LATER?? this one is to add the comment
                
                if debugLevel>=3:
                    print admdf[0].getHeader()
                    print admdf.info()
                
                ad.append(moredata=admdf)  #$$$$$$$$$$  STILL NEED TO GET CRAIG TO CREATE A FN THAT INSERTS RATHER THAN APPENDS
                if debugLevel>=1:
                    print ad.info()
                
                #addMDF(ad,mdf)     #$$ the call to the tool box function, currently not in use
                if debugLevel>=1:
                    print 'prim_G_S177: finished adding the MDF'
        except:
            print "Problem preparing the image."
            raise 
        
        yield rc
    #------------------------------------------------------------------------
    def validateInstrumentData(self,rc):
        try:
            # 'importing' the logger and debug level   
            gemLog=rc["log"]
            debugLevel=int(rc['debugLevel'])
            
            for ad in rc.getInputs(style="AD"):
                if debugLevel>=4:
                    print 'prim_G_S164: validating data for file = ',ad.filename
                valInstData(ad)
                if debugLevel>=4:
                    print 'prim_G_S167: data validated for file = ', ad.filename
                
        except:
            print "Problem preparing the image."
            raise 
        
        yield rc
        
        
    #$$$$$$$$$$$$$$$$$$$$$$$ END OF KYLES NEW STUFF $$$$$$$$$$$$$$$$$$$$$$$$$$
        