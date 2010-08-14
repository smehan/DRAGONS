#from Reductionobjects import Reductionobject
from primitives_GEMINI import GEMINIPrimitives
# All GEMINI IRAF task wrappers.
import time
from astrodata.adutils import filesystem
from astrodata.adutils import gemLog
from astrodata import IDFactory
from astrodata import Descriptors
from astrodata.data import AstroData

from pyraf.iraf import tables, stsdas, images
from pyraf.iraf import gemini
import pyraf
import iqtool
from iqtool.iq import getiq
from gempy.instruments.gemini import *
from gempy.instruments.gmos import *


import pyfits
import numdisplay
import string
log=gemLog.getGeminiLog()
yes = pyraf.iraf.yes
no = pyraf.iraf.no
import shutil

# NOTE, the sys.stdout stuff is to shut up gemini and gmos startup... some primitives
# don't execute pyraf code and so do not need to print this interactive 
# package init display (it shows something akin to the dir(gmos)
import sys, StringIO, os
SAVEOUT = sys.stdout
capture = StringIO.StringIO()#from Reductionobjects import Reductionobject

log=gemLog.getGeminiLog()
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

class GMOSException:
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


class GMOSPrimitives(GEMINIPrimitives):
    astrotype = "GMOS"
    
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

#+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
#$$$$$$$$$$$$$$$$$$$$ NEW STUFF BY KYLE FOR: PREPARE $$$$$$$$$$$$$$$$$$$$$
    '''
    These primitives are now functioning and can be used, BUT are not set up to run with the current demo system.
    commenting has been added to hopefully assist those reading the code.
    Excluding validateWCS, all the primitives for 'prepare' are complete (as far as we know of at the moment that is)
    and so I am moving onto working on the primitives following 'prepare'.
    '''
    
    
    #------------------------------------------------------------------------    
    def validateInstrumentData(self,rc):
        '''
        This primitive is called by validateData to validate the instrument specific data checks for all input files.
        '''
        
        try:
            for ad in rc.getInputs(style="AD"):
                log.status('validating data for file = '+ad.filename,'status')
                log.debug('calling valInstData', 'status')
                valInstData(ad)
                #log.status('data validated for file = '+ad.filename,'status')
                
        except:
            log.critical("Problem preparing the image.",'critical')
            raise GMOSException
        
        yield rc       
        
    #-------------------------------------------------------------------------------
    def standardizeInstrumentHeaders(self,rc):
        '''
        This primitive is called by standardizeHeaders to makes the changes and additions to
        the headers of the input files that are instrument specific.
        '''
        try:            
            writeInt = rc['writeInt']
                               
            for ad in rc.getInputs(style="AD"): 
                log.debug('calling stdInstHdrs','status') 
                stdInstHdrs(ad) 
            
            if writeInt:
                log.debug('writing the outputs to disk')
                rc.run('writeOutputs(postpend=_instHdrs)')  #$$$$$$$$$$$$$this needs to accept arguments to work right!!!!!!!!!!!! currently hardcoded
                log.debug('writting complete')
                    
        except:
            log.critical("Problem preparing the image.",'critical')
            raise GMOSException
        
        yield rc

 #$$$$$$$$$$$$$$$$$$$$$$$$$$$$$ Prepare primitives end here $$$$$$$$$$$$$$$$$$$$$$$$$$$$
 
 #$$$$$$$$$$$$$$$$$$$$$$$$$$$$$ primitives following Prepare below $$$$$$$$$$$$$$$$$$$$  
    def overscanSubtract(self,rc):
        """
        This primitive uses the CL script gireduce to subtract the overscan from the input images.
        """
        try:
            log.status('*STARTING* to subtract the overscan from the input data','status')
            # writing input files to disk with prefixes onto their file names so they can be deleted later easily 
            clm = CLManager(rc)
            clm.LogCurParams()
            
            # params set by the CLManager or the definition of the prim 
            clPrimParams={
                          'inimages'    :clm.inputsAsStr(),
                          'gp_outpref'  :clm.uniquePrefix(),
                          'fl_over'     :yes, #yes=pyraf.iraf.yes and no=pyraf.iraf.no globally set
                          'Stdout'      :IrafStdout(), #this is actually in the default dict but wanted to show it again
                          'Stderr'      :IrafStdout(), #this is actually in the default dict but wanted to show it again
                          'logfile'    :'TEMP.log', # this log will get created and will then be deleted near the end of this prim
                          'verbose'    :yes # this is actually in the default dict but wanted to show it again
                          }
            # params from the Parameter file adjustable by the user
            clSoftcodedParams={
                               'fl_trim'    :pyrafBoolean(rc["fl_trim"]),
                               'outpref'    :rc["outpref"],
                               'fl_vardq'   :pyrafBoolean(rc['fl_vardq'])
                               }
            # grabbing the default params dict and updating it with the two above dicts
            clParamsDict=CLDefaultParamsDict('gireduce')
            clParamsDict.update(clPrimParams)
            clParamsDict.update(clSoftcodedParams)
            
            # taking care of the biasec->nbiascontam param
            if not rc['biassec']=='':
                nbiascontam=clm.nbiascontam()
                clParamsDict.update({'nbiascontam':nbiascontam})
                log.fullinfo('nbiascontam parameter was updated to = '+str(clParamsDict['nbiascontam']),'params')

            log.fullinfo('calling the gireduce CL script', 'status')
            
            gemini.gmos.gireduce(**clParamsDict)
            
            #gemini.gmos.gireduce(clm.inputsAsStr(), gp_outpref=clm.uniquePrefix(),fl_over=pyrafBoolean(True), \
            #        fl_trim=pyrafBoolean(rc["fl_trim"]), fl_bias=no, \
            #        fl_flat=no, outpref=rc["outpref"], fl_vardq=pyrafBoolean(rc['fl_vardq']), \
            #        Stdout = IrafStdout(), Stderr = IrafStdout())

            if gemini.gmos.gireduce.status:
                log.critical('gireduce failed','critical') 
                raise GMOSException("gireduce exception")
            else:
                log.fullinfo('exited the gireduce CL script successfully', 'status')
         
            # renaming CL outputs and loading them back into memory and cleaning up the intermediate tmp files written to disk
            clm.finishCL()
            os.remove(clPrimParams['logfile'])
            i=0
            for ad in rc.getOutputs(style="AD"):
                if ad.phuGetKeyValue('GIREDUCE'): # varifies gireduce was actually ran on the file
                    log.fullinfo('file '+clm.preCLNames()[i]+' had its overscan subracted successfully', 'status')
                    log.fullinfo('new file name is: '+ad.filename, 'status')
                i=i+1
                ut = ad.historyMark()  
                #$$$$$ should we also have a OVERSUB UT time stame in the PHU???
                log.fullinfo('****************************************************','header')
                log.fullinfo('file = '+ad.filename,'header')
                log.fullinfo('~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~','header')
                log.fullinfo('PHU keywords updated/added:\n', 'header')
                log.fullinfo('GEM-TLM = '+str(ut)+'\n','header' )
            
            log.status('*FINISHED* subtracting the overscan from the input data','status')
        except:
            log.critical("Problem preparing the image.",'critical')
            raise GMOSException
        
        yield rc    
    #--------------------------------------------------------------------------------------------    
    def overscanTrim(self,rc):
        """
        This primitive uses pyfits and AstroData to trim the overscan region from the input images
        and update their headers.
        """
        try:
            log.status('*STARTING* to trim the overscan region from the input data','status')
            
            for ad in rc.getInputs(style='AD'):
                ad.phuSetKeyValue('TRIMMED','yes','Overscan sectiUIADVANCEDon trimmed')
                for sciExt in ad['SCI']:
                    datasecStr=sciExt.data_section()
                    datasecList=secStrToIntList(datasecStr) 
                    dsl=datasecList
                    log.stdinfo('\nfor '+ad.filename+' extension '+str(sciExt.extver())+\
                                                            ', keeping the data from the section '+datasecStr,'science')
                    sciExt.data=sciExt.data[dsl[2]-1:dsl[3],dsl[0]-1:dsl[1]]
                    sciExt.header['NAXIS1']=dsl[1]-dsl[0]+1
                    sciExt.header['NAXIS2']=dsl[3]-dsl[2]+1
                    newDataSecStr='[1:'+str(dsl[1]-dsl[0]+1)+',1:'+str(dsl[3]-dsl[2]+1)+']' 
                    sciExt.header['DATASEC']=newDataSecStr
                    sciExt.extSetKeyValue(('SCI',int(sciExt.header['EXTVER'])),'TRIMSEC', datasecStr, "Data section prior to trimming")
                    ## updating logger with updated/added keywords to each SCI frame
                    log.fullinfo('****************************************************','header')
                    log.fullinfo('file = '+ad.filename,'header')
                    log.fullinfo('~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~','header')
                    log.fullinfo('SCI extension number '+str(sciExt.extver())+' keywords updated/added:\n', 'header')
                    log.fullinfo('NAXIS1= '+str(sciExt.header['NAXIS1']),'header' )
                    log.fullinfo('NAXIS2= '+str(sciExt.header['NAXIS2']),'header' )
                    log.fullinfo('DATASEC= '+newDataSecStr,'header' )
                    log.fullinfo('TRIMSEC= '+datasecStr,'header' )
                    
                # updating the GEM-TLM value and reporting the output to the RC    
                ut = ad.historyMark()
                #$$$$$ should we also have a OVERTRIM UT time same in the PHU???
                ad.filename=fileNameUpdater(ad.filename,postpend=rc["outpref"], strip=False)
                rc.reportOutput(ad)
                
                # updating logger with updated/added keywords to the PHU
                log.fullinfo('****************************************************','header')
                log.fullinfo('file = '+ad.filename,'header')
                log.fullinfo('~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~','header')
                log.fullinfo('PHU keywords updated/added:\n', 'header')
                log.fullinfo('GEM-TLM = '+str(ut)+'\n','header' ) 
                
            log.status('*FINISHED* trimming the overscan region from the input data','status')
        except:
            log.critical("Problem preparing the image.",'critical')
            raise GMOSException
        
        yield rc
    #---------------------------------------------------------------------------    
    def storeProcessedBias(self,rc):
        '''
        this should be a primitive that interacts with the calibration system (MAYBE) but that isn't up and running yet
        thus, this will just strip the extra postfixes to create the 'final' name for the makeProcessedBias outputs
        and write them to disk.
        '''
        
        try:
                
            log.status('*STARTING* to store the processed bias by writing it to disk','status')
            for ad in rc.getInputs(style='AD'):
                ad.filename=fileNameUpdater(ad.filename, postpend="_preparedBias", strip=True)
                ad.historyMark(key='GBIAS',comment='fake key to trick CL that GBIAS was ran')
                log.fullinfo('filename written to = '+rc["storedbiases"]+"/"+ad.filename,'fullinfo')
                ad.write(os.path.join(rc['storedbiases'],ad.filename),clobber=rc['clob'])
            log.status('*FINISHED* storing the processed bias on disk','status')
        except:
            log.critical("Problem preparing the image.",'critical')
            raise GMOSException
        
        yield rc
    
    
     #+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++    
    def storeProcessedFlat(self,rc):
        '''
        this should be a primitive that interacts with the calibration system (MAYBE), but that isn't up and running yet
        thus, this will just strip the extra postfixes to create the 'final' name for the makeProcessedBias outputs
        and write them to disk.
        '''
        
        try:
                
            log.status('*STARTING* to store the processed bias by writing it to disk','status')
            for ad in rc.getInputs(style='AD'):
                ad.filename=fileNameUpdater(ad.filename, postpend="_preparedFlat", strip=True)
                log.fullinfo('filename written to = '+rc["storedflats"]+"/"+ad.filename,'fullinfo')
                ad.write(os.path.join(rc['storedflats'],ad.filename),clobber=rc['clob'])
            log.status('*FINISHED* storing the processed bias on disk','status')
        except:
            log.critical("Problem preparing the image.",'critical')
            raise GMOSException
        
        yield rc
    #+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    def getProcessedBias(self,rc):
        '''
        a prim that works with the calibration system (MAYBE), but as it isn't written yet this simply
        copies the bias file from the stored processed bias directory and reports its name to the
        reduction context. this is the basic form that the calibration system will work as well but 
        with proper checking for what the correct bias file would be rather than my oversimplified checking
        the binning alone.
        '''
        try:
            packagePath=sys.argv[0].split('gemini_python')[0]
            calPath='gemini_python/test_data/test_cal_files/processed_biases/'
            
            for ad in rc.getInputs(style='AD'):
                if ad.extGetKeyValue(1,'CCDSUM')=='1 1':
                    log.error('NO 1x1 PROCESSED BIAS YET TO USE','error')
                    raise 'error'
                elif ad.extGetKeyValue(1,'CCDSUM')=='2 2':
                    biasfilename = 'N20020214S022_preparedBias.fits'
                    if not os.path.exists(os.path.join('.reducecache/storedcals/retrievedbiases',biasfilename)):
                        shutil.copy(packagePath+calPath+biasfilename, '.reducecache/storedcals/retrievedbiases')
                    rc.addCal(ad,'bias',os.path.join('.reducecache/storedcals/retrievedbiases',biasfilename))
                else:
                    log.error('CCDSUM is not 1x1 or 2x2 for the input flat!!', 'error')
           
        except:
            log.critical("Problem preparing the image.",'critical')
            raise GMOSException
        
        yield rc
            
    #-----------------------------------------------------------------------
   
    def getProcessedFlat(self,rc):
        '''
        a prim that works with the calibration system (MAYBE), but as it isn't written yet this simply
        copies the bias file from the stored processed bias directory and reports its name to the
        reduction context. this is the basic form that the calibration system will work as well but 
        with proper checking for what the correct bias file would be rather than my oversimplified checking
        the binning alone.
        '''
        try:
            packagePath=sys.argv[0].split('gemini_python')[0]
            calPath='gemini_python/test_data/test_cal_files/processed_flats/'
            
            for ad in rc.getInputs(style='AD'):
                if ad.extGetKeyValue(1,'CCDSUM')=='1 1':
                    log.error('NO 1x1 PROCESSED BIAS YET TO USE','error')
                    raise 'error'
                elif ad.extGetKeyValue(1,'CCDSUM')=='2 2':
                    flatfilename = 'N20020211S156_preparedFlat.fits'
                    if not os.path.exists(os.path.join('.reducecache/storedcals/retrievedflats',flatfilename)):
                        shutil.copy(packagePath+calPath+flatfilename, '.reducecache/storedcals/retrievedflats')
                    rc.addCal(ad,'flat',os.path.join('.reducecache/storedcals/retrievedflats',flatfilename))
                else:
                    log.error('CCDSUM is not 1x1 or 2x2 for the input image!!', 'error')
           
        except:
            log.critical("Problem preparing the image.",'critical')
            raise GMOSException
        
        yield rc
        
     #+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    def biasCorrect(self, rc):
        '''
        This primitive will subtract the biases from the inputs using the CL script gireduce.
        
        WARNING: The gireduce script used here replaces the previously calculated DQ frames with
        its own versions.  This may be corrected in the future by replacing the use of the gireduce
        with a Python routine to do the bias subtraction.
        '''
       
        try:
            log.status('*STARTING* to subtract the bias from the input flats','status')
            
            clm=CLManager(rc)
            clm.LogCurParams()
            
            # getting the bias file for the first file of the inputs and assuming it is the same for all the inputs.
            # This should be corrected in the future to be more intelligent and get the correct bias for each input
            # individually if they are not all the same. Then gireduce can be called in a loop with one flat and one bias,
            # this will work well with the CLManager as that was how i wrote this prim originally.
            ad=rc.getInputs(style='AD')[0]
            processedBias=rc.getCal(ad,'bias')
            
             # params set by the CLManager or the definition of the prim 
            clPrimParams={
                          'inimages'    :clm.inputsAsStr(),
                          'gp_outpref'  :clm.uniquePrefix(),
                          'fl_bias'     :yes,
                          'bias'       :processedBias, #possibly add this to the prameters file so the user can override this file
                          'Stdout'      :IrafStdout(), # this is actually in the default dict but wanted to show it again
                          'Stderr'      :IrafStdout(), # this is actually in the default dict but wanted to show it again
                          'logfile'     :'TEMP.log', # this log will get created and will then be deleted near the end of this prim
                          'verbose'     :yes # this is actually in the default dict but wanted to show it again
                          }
            # params from the Parameter file adjustable by the user
            clSoftcodedParams={
                               'fl_trim'    :pyrafBoolean(rc["fl_trim"]),
                               'outpref'    :rc["outpref"],
                               'fl_over'    :pyrafBoolean(rc["fl_over"]),
                               'fl_vardq'   :pyrafBoolean(rc['fl_vardq'])
                               }
            # grabbing the default params dict and updating it with the two above dicts
            clParamsDict=CLDefaultParamsDict('gireduce')
            clParamsDict.update(clPrimParams)
            clParamsDict.update(clSoftcodedParams)
            
            log.fullinfo('calling the gireduce CL script', 'status')
            
            gemini.gmos.gireduce(**clParamsDict)
            
            #gemini.gmos.gireduce(clm.inputList(), fl_over=pyrafBoolean(rc["fl_over"]),\
            #    fl_trim=pyrafBoolean(rc["fl_trim"]), fl_bias=yes,bias=processedBias,\
            #    fl_flat=no, outpref=rc["outpref"],bpm='',fl_vardq=pyrafBoolean(True),\
            #  Stdout = IrafStdout(), Stderr = IrafStdout())
            
            if gemini.gmos.gireduce.status:
                 log.critical('gireduce failed','critical') 
                 raise GMOSException('gireduce failed')
            else:
                 log.fullinfo('exited the gireduce CL script successfully', 'status')
            
            # renaming CL outputs and loading them back into memory and cleaning up the intermediate tmp files written to disk
            clm.finishCL()
            os.remove(clPrimParams['logfile'])
            i=0
            for ad in rc.getOutputs(style="AD"):
                if ad.phuGetKeyValue('GIREDUCE'): # varifies gireduce was actually ran on the file
                    log.fullinfo('file '+clm.preCLNames()[i]+' was bias subracted successfully', 'status')
                    log.fullinfo('new file name is: '+ad.filename, 'status')
                i=i+1
                ut = ad.historyMark()  
                #$$$$$ should we also have a OVERSUB UT time stame in the PHU???
                log.fullinfo('****************************************************','header')
                log.fullinfo('file = '+ad.filename,'header')
                log.fullinfo('~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~','header')
                log.fullinfo('PHU keywords updated/added:\n', 'header')
                log.fullinfo('GEM-TLM = '+str(ut)+'\n','header' )
                
            log.warning('The CL script gireduce REPLACED the previously calculated DQ frames','warning')
            log.status('*FINISHED* subtracting the bias from the input flats','status')
        except:
            print "Problem subtracting bias"
            raise GMOSException
            
        yield rc
    #---------------------------------------------------------------------------
    def makeNormalizedFlat(self,rc):
        '''
        This primitive will combine the input flats and then normalize them using the CL script giflat.
        
        Warning: giflat calculates its own DQ frames and thus replaces the previously produced ones in calculateDQ.
        This may be fixed in the future by replacing giflat with a Python equivilent with more appropriate options
        for the recipe system.
        '''
        
        try:
            
            log.status('*STARTING* to combine and normalize the input flats','status')
            ## writing input files to disk with prefixes onto their file names so they can be deleted later easily 
            clm = CLManager(rc)
            clm.LogCurParams()

            # params set by the CLManager or the definition of the prim 
            clPrimParams={
                          'inflats'    :clm.inputList(),
                          'outflat'    :clm.combineOutname(), # maybe allow the user to override this in the future
                          'Stdout'      :IrafStdout(), # this is actually in the default dict but wanted to show it again
                          'Stderr'      :IrafStdout(), # this is actually in the default dict but wanted to show it again
                          'logfile'     :'TEMP.log', # this log will get created and will then be deleted near the end of this prim
                          'verbose'     :yes # this is actually in the default dict but wanted to show it again
                          }
            # params from the Parameter file adjustable by the user
            clSoftcodedParams={
                               'fl_bias'    :rc['fl_bias'],
                               'fl_vardq'   :rc["fl_vardq"],
                               'fl_over'    :rc["fl_over"],
                               'fl_trim'    :rc["fl_trim"]
                               }
            # grabbing the default params dict and updating it with the two above dicts
            clParamsDict=CLDefaultParamsDict('giflat')
            clParamsDict.update(clPrimParams)
            clParamsDict.update(clSoftcodedParams)
            
            log.fullinfo('calling the giflat CL script', 'status')
            
            gemini.giflat(**clParamsDict)
            
           # gemini.giflat(clm.inputList(), outflat=clm.combineOutname(),\
           #     fl_bias=rc['fl_bias'],fl_vardq=rc["fl_vardq"],\
           #     fl_over=rc["fl_over"], fl_trim=rc["fl_trim"], \
           #     Stdout = IrafStdout(), Stderr = IrafStdout(),\
           #     verbose=pyrafBoolean(True))
            
            if gemini.giflat.status:
                log.critical('giflat failed','critical')
                raise GMOSException('giflat failed')
            else:
                log.fullinfo('exited the giflat CL script successfully', 'status')
                
            # renaming CL outputs and loading them back into memory and cleaning up the intermediate tmp files written to disk
            clm.finishCL(combine=True) 
            os.remove(clPrimParams['logfile'])
            
            ad = rc.getOutputs(style='AD')[0] #there is only one after above combination, so no need to perform a loop
                
            ut = ad.historyMark()
            ad.historyMark(key='GIFLAT',stomp=False)
            
            log.fullinfo('****************************************************','header')
            log.fullinfo('file = '+ad.filename,'header')
            log.fullinfo('~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~','header')
            log.fullinfo('PHU keywords updated/added:\n', 'header')
            log.fullinfo('GEM-TLM = '+str(ut),'header' )
            log.fullinfo('GIFLAT = '+str(ut),'header' )
            log.fullinfo('---------------------------------------------------','header')    
                
                
            log.status('*FINISHED* combining and normalizing the input flats', 'status')
        except:
            print "Problem subtracting bias"
            raise GMOSException
            
        yield rc
    #------------------------------------------------------------------------------------------
    def flatCorrect(self,rc):
        '''
        This primitive performs a flat correction by deviding the inputs by aprocessed flat similar
        to the way gireduce would perform this operation but written in pure python.
        '''
        try:
            log.status('*STARTING* to flat correct the inputs','status')
            ad=rc.getInputs(style='AD')[0]
            processedFlat=AstroData(rc.getCal(ad,'flat'))
            
            for ad in rc.getInputs(style='AD'):
                log.fullinfo('calling ad.div','fullinfo')
                adOut = ad.div(processedFlat)
                ut = adOut.historyMark()
                adOut.filename=fileNameUpdater(ad.filename,postpend=rc["outpref"], strip=False)
                rc.reportOutput(adOut)   
                log.fullinfo('****************************************************','header')
                log.fullinfo('file = '+adOut.filename,'header')
                log.fullinfo('~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~','header')
                log.fullinfo('PHU keywords updated/added:\n', 'header')
                log.fullinfo('GEM-TLM = '+str(ut),'header' )
                log.fullinfo('---------------------------------------------------','header')    
            log.status('*FINISHED* flat correcting the inputs','status')    
        except:
            print "Problem flat correcting the input"
            raise GMOSException
            
        yield rc
        
def CLDefaultParamsDict(CLscript):
    '''
    A function to return a dictionary full of all the default parameters for each CL script used so far in the Recipe System.
    '''
    if CLscript=='gireduce':
        defaultParams={
                           'inimages'    :'',               #Input GMOS images 
                           'outpref'    :'DEFAULT',         #Prefix for output images
                           'outimages'  :"",                #Output images
                           'fl_over'    :no,                #Subtract overscan level
                           'fl_trim'    :no,                #Trim off the overscan section
                           'fl_bias'    :no,                #Subtract bias image
                           'fl_dark'    :no,                #Subtract (scaled) dark image
                           'fl_flat'    :no,                #Do flat field correction?
                           'fl_vardq'   :no,                #Create variance and data quality frames
                           'fl_addmdf'  :no,                #Add Mask Definition File? (LONGSLIT/MOS/IFU modes)
                           'bias'       :'',                #Bias image name
                           'dark'       :'',                #Dark image name
                           'flat1'      :'',                #Flatfield image 1
                           'flat2'      :'',                #Flatfield image 2
                           'flat3'      :'',                #Flatfield image 3
                           'flat4'      :'',                #Flatfield image 4
                           'key_exptime':'EXPTIME',         #Header keyword of exposure time
                           'key_biassec':'BIASSEC',         #Header keyword for bias section
                           'key_datasec':'DATASEC',         #Header keyword for data section
                           'rawpath'    :'',                #GPREPARE: Path for input raw images
                           'gp_outpref' :'g',               #GPREPARE: Prefix for output images
                           'sci_ext'    :'SCI',             #Name of science extension
                           'var_ext'    :'VAR',             #Name of variance extension
                           'dq_ext'     :'DQ',              #Name of data quality extension
                           'key_mdf'    :'MASKNAME',        #Header keyword for the Mask Definition File
                           'mdffile'    :'',                #MDF file to use if keyword not found
                           'mdfdir'     :'',                #MDF database directory
                           'bpm'        :'',                #Bad pixel mask
                           #'giandb'     :'default',        #Database with gain data
                           'sat'        :65000,             #Saturation level in raw images [ADU]
                           'key_nodcount':"NODCOUNT",       #Header keyword with number of nod cycles
                           'key_nodpix' :"NODPIX",          #Header keyword with shuffle distance
                           'key_filter' :"FILTER2",         #Header keyword of filter
                           'key_ron'    :"RDNOISE",         #Header keyword for readout noise
                           'key_gain'   :"GAIN",            #Header keyword for gain (e-/ADU)
                           'ron'        :3.5,               #Readout noise in electrons
                           'gain'       :2.2,               #Gain in e-/ADU
                           'fl_mult'    :no, #$$$$$$$$$     #Multiply by gains to get output in electrons
                           'fl_inter'   :no,                #Interactive overscan fitting?
                           'median'     :no,                #Use median instead of average in column bias?
                           'function'   :"chebyshev",       #Overscan fitting function
                           'nbiascontam':4, #$$$$$$$        #Number of columns removed from overscan region
                           'biasrows'   :"default",         #Rows to use for overscan region
                           'order'      :1,                 #Order of overscan fitting function
                           'low_reject' :3.0,               #Low sigma rejection factor in overscan fit
                           'high_reject':3.0,               #High sigma rejection factor in overscan fit
                           'niterate'   :2,                 #Number of rejection iterations in overscan fit
                           'logfile'    :'',                #Logfile
                           'verbose'    :yes,               #Verbose?
                           'status'     :0,                 #Exit status (0=good)
                           'Stdout'      :IrafStdout(),
                           'Stderr'      :IrafStdout()
                           }
    if CLscript=='giflat':
        defaultParams={ 
                       'inflats'    :'',            #Input flat field images
                       'outflat'    :"",            #Output flat field image
                       'normsec'    :'default',     #Image section to get the normalization.
                       'fl_scale'   :yes,           #Scale the flat images before combining?
                       'sctype'     :"mean",        #Type of statistics to compute for scaling
                       'statsec'    :"default",     #Image section for relative intensity scaling
                       'key_gain'   :"GAIN",        #Header keyword for gain (e-/ADU)
                       'fl_stamp'   :no,            #Input is stamp image
                       'sci_ext'    :'SCI',         #Name of science extension
                       'var_ext'    :'VAR',         #Name of variance extension
                       'dq_ext'     :'DQ',          #Name of data quality extension
                       'fl_vardq'   :no,            #Create variance and data quality frames?
                       'sat'        :65000,         #Saturation level in raw images (ADU)
                       'verbose'    :yes,           #Verbose output?
                       'logfile'    :'',            #Name of logfile
                       'status'     :0,             #Exit status (0=good)
                       'combine'    :"average",     #Type of combine operation
                       'reject'     :"avsigclip",   #Type of rejection in flat average
                       'lthreshold' :'INDEF',       #Lower threshold when combining
                       'hthreshold' :'INDEF',       #Upper threshold when combining
                       'nlow'       :0,             #minmax: Number of low pixels to reject
                       'nhigh'      :1,             #minmax: Number of high pixels to reject
                       'nkeep'      :1,             #avsigclip: Minimum to keep (pos) or maximum to reject (neg)
                       'mclip'      :yes,           #avsigclip: Use median in clipping algorithm?
                       'lsigma'     :3.0,           #avsigclip: Lower sigma clipping factor
                       'hsigma'     :3.0,           #avsigclip: Upper sigma clipping factor
                       'sigscale'   :0.1,           #avsigclip: Tolerance for clipping scaling corrections
                       'grow'       :0.0,           #minmax or avsigclip: Radius (pixels) for neighbor rejection
                       'gp_outpref' :'g',           #Gprepare prefix for output images
                       'rawpath'    :'',            #GPREPARE: Path for input raw images
                       'key_ron'    :"RDNOISE",     #Header keyword for readout noise
                       'key_datasec':'DATASEC',     #Header keyword for data section
                       #'giandb'     :'default',    #Database with gain data
                       'bpm'        :'',            #Bad pixel mask
                       'gi_outpref' :'r',           #Gireduce prefix for output images
                       'bias'       :'',            #Bias calibration image
                       'fl_over'    :no,            #Subtract overscan level?
                       'fl_trim'    :no,            #Trim images?
                       'fl_bias'    :no,            #Bias-subtract images?
                       'fl_inter'   :no,            #Interactive overscan fitting?
                       'nbiascontam':4, #$$$$$$$    #Number of columns removed from overscan region
                       'biasrows'   :"default",     #Rows to use for overscan region
                       'key_biassec':'BIASSEC',     #Header keyword for overscan image section
                       'median'     :no,            #Use median instead of average in column bias?
                       'function'   :"chebyshev",   #Overscan fitting function.
                       'order'      :1,             #Order of overscan fitting function.
                       'low_reject' :3.0,           #Low sigma rejection factor.
                       'high_reject':3.0,           #High sigma rejection factor.
                       'niterate'   :2,             #Number of rejection iterations.
                       'Stdout'      :IrafStdout(),
                       'Stderr'      :IrafStdout()
                       }      
    return defaultParams    
        
        
   
    #$$$$$$$$$$$$$$$$$$$$$$$ END OF KYLES NEW STUFF $$$$$$$$$$$$$$$$$$$$$$$$$$