import os
from astrodata.adutils import gemLog
from astrodata.ReductionObjects import PrimitiveSet

class GENERALPrimitives(PrimitiveSet):
    """
    This is the class containing all of the primitives for the GENERAL level of
    the type hierarchy tree. It inherits all the primitives from the level
    above, 'PrimitiveSet'.
    """
    astrotype = "GENERAL"
    
    def init(self, rc):
        return 
    init.pt_hide = True
    
    def addInputs(self, rc):
        # Instantiate the log
        log = gemLog.getGeminiLog(logType=rc["logType"],
                                  logLevel=rc["logLevel"])
        import glob as gl
        if rc["files"] == None:
            glob = "./*.fits"
        else:
            glob = rc["files"]
        log.status("Listing for: "+ glob)
        files = gl.glob(glob)
        files.sort()
        if len(files) == 0:
            log.status("No files")
        else:
            log.status("\t"+"\n\t".join(files))
        yield rc
        add = True # rc["inputs"]
        if add:
            rc.add_input(files)
        
        yield rc
    
    def clearInputs(self, rc):
        rc.clear_input()
        
        yield rc
    
    def copy(self, rc):
        for ad in rc.get_inputs_as_astro_data():
            from copy import deepcopy
            nd = deepcopy(ad)
            nd.filename = "copy_"+os.path.basename(ad.filename)
            rc.report_output(nd)
        
        yield rc
    
    def listDir(self, rc):
        # Instantiate the log
        log = gemLog.getGeminiLog(logType=rc["logType"],
                                  logLevel=rc["logLevel"])
        if rc["dir"] == None:
            thedir = "."
        else:
            thedir = rc["dir"]
        log.status("Listing for: "+ thedir)
        files = os.listdir(thedir)
        sfiles = []
        for f in files:
            if f[-5:].lower() == ".fits":
                sfiles.append(f)
        sfiles.sort()
        if len(sfiles) == 0:
            log.status("No FITS files")
        else:
            log.status("\n\t".join(sfiles))
        
        yield rc
    
    def setInputs(self, rc):
        files = rc["files"]
        if files != None:
            a = files.split(" ")
            if len(a)>0:
                rc.add_input(a)
        
        yield rc

    def clearStream(self, rc):
        print repr(rc)
        if "stream" in rc:
            stream = rc['stream']
        else:
            stream = "main"
        
        rc.get_stream(stream)
        yield rc
        
    def forwardInput(self, rc):
        
        if rc["to_stream"] != None:
            stream = rc["to_stream"]
        else:
            stream = "main"
        
        
        if "by_token" in rc:
            bt = rc["by_token"]
            for ar in rc.inputs:
                if bt in ar.filename:
                    rc.report_output(ar.ad, stream = stream)
        else:
            inputs = rc.get_inputs_as_astrodata()
            rc.report_output(inputs, stream = stream)
        yield rc
    forwardStream = forwardInput
    
    def showOutputs(self, rc):
        log = gemLog.getGeminiLog(logType=rc["logType"],
                                  logLevel=rc["logLevel"])
        log = gemLog.getGeminiLog(logType=rc["logType"],
                                  logLevel=rc["logLevel"])
        streams = rc.outputs.keys()
        streams.sort()
        streams.remove("main")
        streams.insert(0,"main")
        for stream in streams:
            log.info("stream: "+stream)
            if len(rc.outputs[stream])>0:
                for adr in rc.outputs[stream]:
                    log.info(str(adr))
            else:
                log.info("    empty")                
    
        yield rc
