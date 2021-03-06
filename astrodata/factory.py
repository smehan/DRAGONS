from builtins import object
from future.builtins import str
from future.utils import PY3
from copy import deepcopy

from astropy.io import fits
from astropy.io.fits import HDUList, PrimaryHDU, ImageHDU, Header, DELAYED

from .core import AstroDataError

def fits_opener(source):
    if isinstance(source, HDUList):
        return source
    return fits.open(source, memmap=True)

class AstroDataFactory(object):
    _file_openers = (
            fits_opener,
            )
    def __init__(self):
        self._registry = set()

    @staticmethod
    def _openFile(source):
        """
        Internal static method that takes a `source`, assuming that it is a string
        pointing to a file to be opened.

        If this is the case, it will try to open the file and return an instance of
        the appropriate native class to be able to manipulate it (eg. ``HDUList``).

        If `source` is not a string, it will be returned verbatim, assuming that it
        represents an already opened file.
        """
        if isinstance(source, (str if PY3 else basestring)):
            for func in AstroDataFactory._file_openers:
                try:
                    return func(source)
                except Exception as excp:
                    # Just ignore the error. Assume that it is a not supported format
                    # and go for the next opener
                    pass
            raise AstroDataError("Not access, or not supported format for: {}".format(source))
        else:
            return source

    def addClass(self, cls):
        """
        Add a new class to the AstroDataFactory registry. It will be used when
        instantiating an AstroData class for a FITS file.
        """
        if not hasattr(cls, '_matches_data'):
            raise AttributeError("Class '{}' has no '_matches_data' method".format(cls.__name__))
        self._registry.add(cls)

    def getAstroData(self, source):
        """
        Takes either a string (with the path to a file) or an HDUList as input, and
        tries to return an AstroData instance.

        It will raise exceptions if the file is not found, or if there is no match
        for the HDUList, among the registered AstroData classes.

        Returns an instantiated object, or raises AstroDataError if it was
        not possible to find a match
        """

        opened = self._openFile(source)
        candidates = []
        for adclass in self._registry:
            try:
                if adclass._matches_data(opened):
                    candidates.append(adclass)
            except:  # Some problem opening this
                pass

        # For every candidate in the list, remove the ones that are base classes
        # for other candidates. That way we keep only the more specific ones.
        final_candidates = []
        for cnd in candidates:
            if any(cnd in x.mro() for x in candidates if x != cnd):
                continue
            final_candidates.append(cnd)

        if len(final_candidates) > 1:
            raise AstroDataError("More than one class is candidate for this dataset")
        elif not final_candidates:
            raise AstroDataError("No class matches this dataset")

        return final_candidates[0].load(source)

    def createFromScratch(self, phu, extensions=None):
        """
        Creates an AstroData object from a collection of objects.
        """

        lst = HDUList()
        if phu is not None:
            if isinstance(phu, PrimaryHDU):
                lst.append(phu)
            elif isinstance(phu, Header):
                lst.append(PrimaryHDU(header=deepcopy(phu), data=DELAYED))
            elif isinstance(phu, (dict, list, tuple)):
                p = PrimaryHDU()
                p.header.update(phu)
                lst.append(p)
            else:
                raise ValueError("phu must be a PrimaryHDU or a valid header object")

        # TODO: Verify the contents of extensions...
        if extensions is not None:
            for ext in extensions:
                lst.append(ext)

        return self.getAstroData(lst)
