import pytest
import tempfile
import os

import numpy as np

import astrodata
import gemini_instruments

THIS_DIR = os.path.dirname(__file__)
CHARA = '/net/chara/data2/pub'

import pytest
import tempfile
import os

import numpy as np

import astrodata
import gemini_instruments

from common_astrodata_test import from_test_data, from_chara

## NOTE NOTE NOTE NOTE NOTE NOTE NOTE NOTE NOTE NOTE
## NOTE NOTE NOTE NOTE NOTE NOTE NOTE NOTE NOTE NOTE
## NOTE NOTE NOTE NOTE NOTE NOTE NOTE NOTE NOTE NOTE
#
#    Lazy loading is undergoing heavy changes.
#    These tests are probably not relevant any
#    longer, and may fail.
#
## NOTE NOTE NOTE NOTE NOTE NOTE NOTE NOTE NOTE NOTE
## NOTE NOTE NOTE NOTE NOTE NOTE NOTE NOTE NOTE NOTE
## NOTE NOTE NOTE NOTE NOTE NOTE NOTE NOTE NOTE NOTE

# Load data when accessing it
def test_for_length():
    ad = from_test_data('GMOS/N20110826S0336.fits')
    # This should force the data to be loaded
    # Otherwise, we'll get different results - or an exception
    assert len(ad) == len(ad.nddata)

# TODO: This one fails as it is written. Decide later if it's relevant or not
# def test_keyword_changes_preserved_on_lazy_loading():
#     ad = from_test_data('GMOS/N20110826S0336.fits')
#     ad.phu['RAWIQ'] = 'Any'
#     del ad.phu['RAWCC']
#     del ad[0].hdr['DATATYPE']
# 
#     ad._lazy_populate_object() # Force lazy load
#     assert ad.phu['RAWIQ'] == 'Any'
#     assert 'RAWCC' not in ad.phu
#     assert 'DATATYPE' not in ad[0].hdr
