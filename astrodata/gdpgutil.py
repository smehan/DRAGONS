import sys
#------------------------------------------------------------------------------ 
from astrodata.AstroData import AstroData
import AstroDataType

from ReductionContextRecords import AstroDataRecord
from copy import copy

#removed old logger, calls changed to prints, need to incorporate new logger
#------------------------------------------------------------------------------ 
class GDPGUtilExcept:
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

#------------------------------------------------------------------------------ 

def checkDataSet( filenames ):
    '''
    Takes a list or individual AstroData, filenames, and then verifies and
    returns list of AstroData instances. Will crash if bad arguments.
    
    @param filenames: Parameters you want to verify. 
    @type filenames: list, AstroData, str
    
    @return: List of verified AstroData instances.
    @rtype: list
    '''    
    if type( filenames ) != list:
        filenames = [filenames]
    
    outlist = []
    
    for filename in filenames:
        if type( filename ) == str:
            filename = AstroData( filename )
        elif type( filename ) == AstroData:
            pass
        else:
            raise("BadArgument: '%(name)s' is an invalid type '%(type)s'. Should be str or AstroData." 
                      % {'name':str(filename), 'type':str(type(filename))})
        
        outlist.append( filename )
    
    return outlist

#------------------------------------------------------------------------------ 

def clusterTypes( datalist ):
    '''
    Given a list or singleton of filenames, or AstroData, generate an index of AstroData based on 
    types (e.g. So each file can run under the same recipe).
    
    Example Output:
{('GEMINI_NORTH', 'GEMINI', 'GMOS_N', 'GMOS', 'GMOS_BIAS', 'PREPARED'): [<AstroData object>,
                                                                         <AstroData object>],
 ('GEMINI_NORTH', 'GEMINI', 'GMOS_N', 'GMOS_FLAT', 'GMOS', 'PREPARED'): [<AstroData object>],
 ('GEMINI_NORTH', 'GEMINI', 'GMOS_N', 'GMOS_IMAGE', 'GMOS', 'UNPREPARED', 'GMOS_RAW'): [<AstroData object>]}
 
    @param datalist: The list of data to be clustered.
    @type datalist: list, str, AstroData
    
    @return: Index of AstroDatas keyed by types.
    @rtype: dict
    '''
    
    #log.debug( 'Importing AstroData' )
    from astrodata.AstroData import AstroData
    
    datalist = checkDataSet( datalist )
    
    clusterIndex = {}
    
    for data in datalist:
        try:
            assert( type(data) == AstroData )
        except:
            #log.exception( "Bad Argument: '%(data)s' '%(astr)s'" %{'data':str(type(data)), 'astr':str(AstroData)})
            print ( "gdbputil 85: Bad Argument: '%(data)s' '%(astr)s'" %{'data':str(type(data)), 'astr':str(AstroData)} )
            raise
        
        types = tuple( data.getTypes() )
        if clusterIndex.has_key( types ):
            dlist = clusterIndex[types]
            dlist.append( data )
        else:
            dlist = [data]
        clusterIndex.update( {types:dlist} )
    
    #log.debug( 'clusterIndex: ' + str(clusterIndex) )
    return clusterIndex

#------------------------------------------------------------------------------ 

def openIfName(dataset):
    """Utility function to handle accepting datasets as AstroData
    instances or string filenames. Works in conjunction with closeIfName.
    The way it works, openIfName opens returns an GeminiData isntance"""
    
    bNeedsClosing = False
    if type(dataset) == str:
        bNeedsClosing = True
        gd = AstroData(dataset)
    elif type(dataset) == AstroData:
        bNeedsClosing = False
        gd = dataset
    elif type(dataset) == AstroDataRecord:
        bNeedsClosing = False
        gd = dataset.ad
    else:
        raise GDPGUtilExcept("BadArgument in recipe utility function: openIfName(..)\n MUST be filename (string) or GeminiData instrument")
    
    return (gd, bNeedsClosing)
    
    
def closeIfName(dataset, bNeedsClosing):
    """Utility function to handle accepting datasets as AstroData
    instances or string filenames. Works in conjunction with openIfName."""

    if bNeedsClosing == True:
        dataset.close()
    
    return


def DEADFUNCTIONinheritConfig(typ, index, cl = None):
    # print "GU34:", typ, str(index)
    if cl == None:
        cl = AstroDataType.getClassificationLibrary()

    if typ in index:
        #print "GU51:", typ, index[typ]
        return {typ:index[typ]}
    else:
        typo = cl.getTypeObj(typ)
        supertypos = typo.getSuperTypes()
        cfgs = {}
        for supertypo in supertypos:
            cfg = inheritConfig(supertypo.name, index, cl = cl)
            if cfg != None:
                cfgs.update(cfg)
        if len(cfgs) == 0:
            return None
        else:
            return cfgs

def pickConfig(dataset, index, style = "unique"):
    """Pick config will pick the appropriate config for the style.
    NOTE: currently style must be unique, a unique config is chosen using
    inheritance.
    """
    ad,obn = openIfName(dataset)
    cl = ad.getClassificationLibrary()
    
    candidates = {}
    if style == "unique":
        types = ad.getTypes(prune=True)
    else:
        types = ad.getTypes()
        
    # print "\nGU58:", types, "\nindex:",index, "\n"
    # only one type can imply a package
    # this goes through the types, making candidates of the
    # first value in the index in order from child 
    # to grandparent.
    # for style="unique" the end result must be just one
    # configuration object returned.
    def inheritConfig(typ, index):
        # print "gd168:", typ
        if typ in index.keys():
            return (typ,index[typ])
        else:
            typo = cl.getTypeObj(typ)
            if typo.parent:
                return inheritConfig(typo.parent, index)
            else:
                return None  
                
    # generate candidate configs from leave types 
    for typ in types:
        cand = None
        # if the typ is in the index, it's a candidate
        # else if the type has an inherited Config, it is used
        if typ in index:
            cand = index[typ]
            if cand:
                candidates.update({typ:cand})
        else:
            candtuple = inheritConfig(typ, index)
            if candtuple:
                candidates.update({candtuple[0]:candtuple[1]})        
    k = candidates.keys()
    # print "GU191:", repr(candidates)
    
    # have to prune here, the reason, config inheritance reintroduces
    # resolvable conflicts
    candscopy = copy(candidates)
    for cantyp in candscopy.keys():
        for partyp in candscopy.keys():
            if cl.typeIsChildOf(cantyp, partyp):
                if partyp in candidates:
                    del(candidates[partyp])
    # print "gu205:", repr(candidates)
    
    
    # print "GU211:", repr(candidates)
    if len(k) == 0:
        for typ in types:
            candtuple = inheritConfig(typ, index)
            if candtuple:
                candidates.update({candtuple[0]:candtuple[1]})

    k = candidates.keys()
    
    # print "\nGU61: candidates:", candidates, "\n"
        # sys.exit(1)
    # style unique this can only be one thing
    if style=="unique":
        if len(k)>1:
            #print "CONFIG CONFLICT for %s, configs = %s" % (ad.filename,repr(k))
            
            msg="${RED}Config Conflict:\n" \
                "   %(num)d possible configurations found, maximum 1\n" \
                "   found: %(typs)s \n" \
                '   for file "%(file)s" configuration space is\n' \
                "%(cs)s${NORMAL}\n" % { 
                            "num":len(k),
                            "file":dataset.filename,
                            "cs":repr(index),
                            "typs": ", ".join(k)
                            }     
            print msg                           
            raise GDPGUtilExcept('Multiple Configs Found for style = "unique"')
        if len(k) == 0:
            print "${RED}types: %s" % types
            print "config index:", repr(index), "${NORMAL}"
            s = "NO CONFIG for %s" % (ad.filename)
            raise GDPGUtilExcept(s)
            
    closeIfName(ad, obn)
    return candidates
