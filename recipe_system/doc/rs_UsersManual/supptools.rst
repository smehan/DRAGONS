.. supptools:
.. include discuss
.. include howto

Supplemental tools
==================

DRAGONS provides a number of command line tools that users should find helpful in
executing ``reduce`` on their data. These supplemental tools can help users
discover information, not only about their own data, but about the Recipe System,
such as available recipes, primitives, and defined tags.

If your environment has been configured correctly these applications will work
directly.

.. _showpars:

showpars
--------

Inheritance and class overrides within the primitive and parameter hierarchies
means that one cannot simply look at any given primitive function and its
parameters and extrapolate those to all such named primitives and parameters.
Primitives and their parameters are tied to the particular classes designed for
those datasets identified as a particular kind of data.

The ``showpars`` application is a simple command line utility allowing users
to see the available parameters and defaults for a particular primitive
function applicable to a given dataset. Since the applicable primitives
for a dataset are dependent upon the `tagset` of the identified dataset
(i.e. ``NIRI IMAGE`` , ``F2 SPECT`` , ``GMOS BIAS``, etc.), which is
to say, the `kind` of data we are looking at, the parameters available on a
named primitive function can vary across data types, as can the primitive function
itself. For example, F2 IMAGE ``stackFlats`` uses the generic implementation of
the function, while GMOS IMAGE ``stackFlats`` overrides that generic method.

We examine the help on the command line of showpars::

 $ showpars.py -h
 usage: showpars.py [-h] [-v] filen primn

 Primitive parameter display, v2.0.0 (beta)

 positional arguments:
   filen          filename
   primn          primitive name

 optional arguments:
   -h, --help     show this help message and exit
   -v, --version  show program's version number and exit

Two arguments are requiered: the dataset filename, and the primitive name of
interest. As readers will note, ``showpars`` provides a wealth of information
about the available parameters on the specified primitive, including allowable
values or ranges of values::

  $ showpars FR39441/S20180516S0237.fits stackFlats
  Dataset tagged as set(['RAW', 'GMOS', 'GEMINI', 'SIDEREAL', 'FLAT', 'UNPREPARED',
  'IMAGE', 'CAL', 'TWILIGHT', 'SOUTH'])
  
  Settable parameters on 'stackFlats':
  ========================================
  Name			Current setting

  suffix               '_stack'             Filename suffix
  apply_dq             True                 Use DQ to mask bad pixels?
  separate_ext         False                Handle extensions separately?
  statsec              None                 Section for statistics
  operation            'mean'               Averaging operation
  Allowed values:
	wtmean	variance-weighted mean
	mean	arithmetic mean
	median	median
	lmedian	low-median

  reject_method        'minmax'             Pixel rejection method
  Allowed values:
	minmax	reject highest and lowest pixels
	none	no rejection
	varclip	reject pixels based on variance array
	sigclip	reject pixels based on scatter

  hsigma               3.0                  High rejection threshold (sigma)
	Valid Range = [0,inf)
  lsigma               3.0                  Low rejection threshold (sigma)
	Valid Range = [0,inf)
  mclip                True                 Use median for sigma-clipping?
  max_iters            None                 Maximum number of clipping iterations
	Valid Range = [1,inf)
  nlow                 1                    Number of low pixels to reject
	Valid Range = [0,inf)
  nhigh                1                    Number of high pixels to reject
	Valid Range = [0,inf)
  memory               None                 Memory available for stacking (GB)
	Valid Range = [0.1,inf)
  scale                False                Scale images to the same intensity?

With this information, users can now confidently adjust parameters for
particular primitive functions. As we have seen already, this can be done
easily from the `reduce` command line. Building on material covered in this
manual, and continuing our example from above::

  $ reduce -p stackFlats:nhigh=3 <fitsfiles> [ <fitsfile>, ... ]

And the reduction proceeds. When the ``stackFlats`` primitive begins, the
new value for nhigh will be used.

.. note::
   ``showpars`` is not considered the final tool for users to examine and set
   parameters for dataset reduction. Plans are in the works to develop a more
   graphical tool to help users view and adjust parameters on primitive functions.
   But it does show users the important information: the parameters available
   on a primitive's interface, the current (default) settings of the named
   parameters, and allowed ranges of values where appropriate.


.. _typewalk:

typewalk
--------
The ``typewalk`` application examines files in a directory or directory tree
and reports the data classifications through the ``astrodata`` tag sets. By
default, typewalk will recurse all subdirectories under the current
directory. Users may specify an explicit directory with the ``-d,--dir``
option.

``typewalk`` supports the following options::

  -h, --help            show this help message and exit
  -b BATCHNUM, --batch BATCHNUM
                        In shallow walk mode, number of files to process at a
                        time in the current directory. Controls behavior in
                        large data directories. Default = 100.
  -d TWDIR, --dir TWDIR
                        Walk this directory and report tags. default is cwd.
  -f FILEMASK, --filemask FILEMASK
                        Show files matching regex <FILEMASK>. Default is all
                        .fits and .FITS files.
  -n, --norecurse       Do not recurse subdirectories.
  --or                  Use OR logic on 'tags' criteria. If not specified,
                        matching logic is AND (See --tags). Eg., --or --tags
                        SOUTH GMOS IMAGE will report datasets that are one of
                        SOUTH *OR* GMOS *OR* IMAGE.
  -o OUTFILE, --out OUTFILE
                        Write reported files to this file. Effective only with
                        --tags option.
  --tags TAGS [TAGS ...]
                        Find datasets that match only these tag criteria. Eg.,
                        --tags SOUTH GMOS IMAGE will report datasets that are
                        all tagged SOUTH *and* GMOS *and* IMAGE.
  --xtags XTAGS [XTAGS ...]
                        Exclude <xtags> from reporting.

Files are selected and reported through a regular expression mask which, 
by default, finds all ".fits" and ".FITS" files. Users can change this mask 
with the **-f, --filemask** option.

As the **--tags** option indicates, ``typewalk`` can find and report data
that match specific tag criteria. For example, a user might want to find
all GMOS image flats under a certain directory. ``typewalk`` will locate and
report all datasets that would match the AstroData tags,
``set(['GMOS', 'IMAGE', 'FLAT'])``.

A user may request that an output file be written containing all datasets 
matching AstroData tag qualifiers passed by the **--tags** option. An output 
file is specified through the **-o, --out** option. Output files are
formatted so they may be passed `directly to the reduce command line` via
that applications 'at-file' (@file) facility. See :ref:`atfile` or the reduce
help for more on 'at-files'.

Users may select tag matching logic with the **--or** switch. By default,
qualifying logic is AND, i.e. the logic specifies that `all` tags must be
present (x AND y); **--or** specifies that ANY tags, enumerated with 
**--tags**, may be present (x OR y). **--or** is only effective when the 
**--tags** option is specified with more than one tag.

For example, find all GMOS images from Cerro Pachon in the top level
directory and write out the matching files, then run reduce on them
(**-n** is 'norecurse')::

  $ typewalk -n --tags SOUTH GMOS IMAGE --out gmos_images_south
  $ reduce @gmos_images_south

Find all F2 SPECT datasets in a directory tree::

 $ typewalk --tags SPECT F2

This will also report match results to stdout.

Users may find the **--xtags** flag useful, as it provides a facility for
filtering results further by allowing certain tags to be excluded from the
report. 

For example, find GMOS, IMAGE tag sets, but exclude ACQUISITION images from
reporting::

  $ typewalk --tags GMOS IMAGE --xtags ACQUISITION

  directory: ../test_data/output
     S20131010S0105.fits .............. (GEMINI) (SOUTH) (GMOS) (IMAGE) (RAW)
     (SIDEREAL) (UNPREPARED)

     S20131010S0105_forFringe.fits .... (GEMINI) (SOUTH) (GMOS)
     (IMAGE) (NEEDSFLUXCAL) (OVERSCAN_SUBTRACTED) (OVERSCAN_TRIMMED) 
     (PREPARED) (PROCESSED_SCIENCE) (SIDEREAL)

     S20131010S0105_forStack.fits ...... (GEMINI) (SOUTH) (GMOS) (IMAGE) 
     (NEEDSFLUXCAL) (OVERSCAN_SUBTRACTED) (OVERSCAN_TRIMMED) 
     (PREPARED) (SIDEREAL)

Exclude GMOS ACQUISITION images and GMOS IMAGE datasets that have been 
'prepared'::

  $ typewalk --tags GMOS IMAGE --xtags ACQUISITION PREPARED

  directory: ../test_data/output
     S20131010S0105.fits .............. (GEMINI) (SOUTH) (GMOS) (IMAGE) (RAW)
     (SIDEREAL) (UNPREPARED)

With **--tags** and **--xtags**, users may really tune their searches for
very specific datasets.

.. _adcc:

adcc
----
The application that has been historically known as the ``adcc`` (Automated
Data Communication Center), is an HTTP proxy server. The webservice provided
by the ``adcc`` allows both the Recipe System and primitive functions to post
data produced during data processing. These data comprise image quality and
observing condition metrics, passed to the web server in the form of messages
encapsulating Quality Assessment (QA) metrics data. The metrics themselves are
produced by three specific primitive functions, ``measureIQ``, ``measuerBG``,
and ``measureCC``, which respectively measure image quality, background level,
and cloud cover (measured atmospheric extinction). These QA metrics are the
priniciple product generated by the Quality Assessment Pipeline (QAP), that
provides near real time assessments of observing conditions. 

Neither the Recipe System nor the primitives require the ``adcc`` to be
running, but if an ``adcc`` instance is alive, then QA metrics will be
reported to the service by the QA measurement primitives if they are called.
The ``adcc`` provides an interactive web interface and renders metric
"events" in real time. Metrics events are also directly reported to the
:ref:`fitsstore` and stored in the fitsstore metrics database when the
``reduce`` option, ``--upload_metrics``, is specified.

The ``adcc`` is started with the command of the same name, and one may request
the help (or the manpage), in order to see the possible controllers supplied::

  $ adcc --help

  usage: adcc [-h] [-d] [-v] [--startup-report ADCCSRN] [--http-port HTTPPORT]

  Automated Data Communication Center (ADCC), v2.0 (beta)

  optional arguments:
    -h, --help            Show this help message and exit
    -d, --dark            Use the adcc faceplate 'dark' theme.
    -v, --verbose         Increase HTTP client messaging on GET requests.
    --startup-report ADCCSRN
                          File name for adcc startup report.
    --http-port HTTPPORT  Response port for the web interface.
                          Default port is 8777.

The application provides a HTTP server that listens on either a user-provided
port number (via ``--http-port``), or the default port of 8777. This webserver
provides an interactive, graphical interface by which users can monitor incoming
metrics that may be reported by recipe system pipelines (recipes), specifically,
the Quality Assurance Pipeline (QAP). It is worth repeating that the near
real-time QAP produces image quality and weather related metrics that are passed
to the adcc as message events. Users wishing to use the adcc to monitor QA
metrics need to simply open a web browser on the service's URL.

.. figure:: images/adcc_dark_metrics.png

   Snapshot of the Nighttime Metrics GUI, using the "dark" theme and displaying
   the metrics retrieved from fitsstore for operational day 20170209.

E.g., In a terminal window, start the adcc with default values::

    $ adcc

Or in a terminal window, start the adcc and request the "dark" page theme and
verbosity::

    $ adcc -d -v

The ``-v`` (verbose) option displays server messages to stdout. These messages
will comprise POST and GET requests made on the server and selected server
responses. These messages are informational only, though may be of some
interest to users.

Once an adcc is up and running, open a browser window on

    http://localhost:8777/qap/nighttime_metrics.html

This will render any metrics received from the server for the current
operational day. When metrics are produced and sent to the adcc, the display
will automatically update with the latest metric event. If users are processing
datasets taken on a day prior to the current operational day, the URL to
monitor metrics produced for that day is

     http://localhost:8777/qap/nighttime_metrics.html?date=YYYYMMDD

When the adcc is started, certain information is written to a special file in
a ``.adcc`` directory that records the process id (pid) of the adcc instance and
port number on which the web server is listening.

.. note::
   Currently, only one adcc instance is permitted to run. Any and all instances
   of ``reduce`` will report metrics to the currently running instance of the
   adcc.
