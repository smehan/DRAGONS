#
#                                                           request_transport.py
# ------------------------------------------------------------------------------
import urllib
import urllib2
import datetime
import traceback


from os.path import join, basename
from xml.dom import minidom
from pprint  import pformat

from . import calurl_dict
from ..utils import logutils
# ------------------------------------------------------------------------------
CALURL_DICT   = calurl_dict.calurl_dict
UPLOADPROCCAL = CALURL_DICT["UPLOADPROCCAL"]
UPLOADCOOKIE  = CALURL_DICT["UPLOADCOOKIE"]
_CALMGR       = CALURL_DICT["CALMGR"]
# ------------------------------------------------------------------------------
CALTYPEDICT = { "arc": "arc",
                "bias": "bias",
                "dark": "dark",
                "flat": "flat",
                "processed_arc":   "processed_arc",
                "processed_bias":   "processed_bias",
                "processed_dark":   "processed_dark",
                "processed_flat":   "processed_flat",
                "processed_fringe": "processed_fringe"}
# -----------------------------------------------------------------------------
RESPONSESTR = """########## Request Data BEGIN ##########
%(sequence)s
########## Request Data END ##########

########## Calibration Server Response BEGIN ##########
%(response)s
########## Calibration Server Response END ##########

########## Nones Report (descriptors that returned None):
%(nones)s
########## Note: all descriptors shown above, scroll up.
        """
# -----------------------------------------------------------------------------
log = logutils.get_logger(__name__)

# -----------------------------------------------------------------------------
def upload_calibration(filename):
    """Uploads a calibration file to the FITS Store.

    parameters: <string>, the file to be uploaded.
    return:     <void>
    """
    fn  = basename(filename)
    url = join(UPLOADPROCCAL, fn)
    postdata = open(filename).read()
    try:
        rq = urllib2.Request(url)
        rq.add_header('Content-Length', '%d' % len(postdata))
        rq.add_header('Content-Type', 'application/octet-stream')
        rq.add_header('Cookie', 'gemini_fits_upload_auth=%s' % UPLOADCOOKIE)
        u = urllib2.urlopen(rq, postdata)
        response = u.read()
    except urllib2.HTTPError, error:
        contents = error.read()
        raise
    return


def calibration_search(rq, return_xml=False):
    rqurl = None
    calserv_msg = None
    CALMGR = _CALMGR
    
    if "source" not in rq:
        source = "central"
    else:
        source = rq["source"]
    
    if source == "central" or source == "all":
        rqurl = join(CALMGR, CALTYPEDICT[rq['caltype']])
        log.stdinfo("CENTRAL SEARCH: {}".format(rqurl))

    rqurl = rqurl + "/{}".format(rq["filename"])
    # encode and send request
    sequence = [("descriptors", rq["descriptors"]), ("types", rq["types"])]
    postdata = urllib.urlencode(sequence)
    response = "CALIBRATION_NOT_FOUND"
    try:
        calRQ = urllib2.Request(rqurl)
        if source == "local":
            u = urllib2.urlopen(calRQ, postdata)
        else:
            u = urllib2.urlopen(calRQ, postdata)
        response = u.read()
    except urllib2.HTTPError, error:
        calserv_msg = error.read()
        traceback.print_exc()
        return (None, calserv_msg)

    if return_xml:
        return (None, response)

    nones = []
    descripts = rq["descriptors"]
    for desc in descripts:
        if descripts[desc] is None:
            nones.append(desc)

    preerr = RESPONSESTR % { "sequence": pformat(sequence),
                             "response": response.strip(),
                             "nones"   : ", ".join(nones) \
                             if len(nones) > 0 else "No Nones Sent" }

    try:
        dom = minidom.parseString(response)
        calel = dom.getElementsByTagName("calibration")
        calurlel = dom.getElementsByTagName('url')[0].childNodes[0]
        calurlmd5 = dom.getElementsByTagName('md5')[0].childNodes[0]
    except IndexError:
        return (None, preerr)

    log.stdinfo(repr(calurlel.data))

    return (calurlel.data, calurlmd5.data)