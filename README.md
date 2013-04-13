mytardis-app-datagrabber
========================

MyTardis app for CMM datagrabber integration.

This app defines plugin classes and Filters:

  * The DataGrabberFilter class is an ingestion filter that extracts 
    Dataset and Datafile metadata from a datagrabber ".admin" file.
    There are no custom arguments for this filter.

  * The source_path function is an organization mapper function that
    uses the 'instrument_pathname' parameter of a Datafile as the basis
    for the archive pathname.  This takes the following optional keyword 
    arguents:

    * The 'excludePatterns' argument gives a list of regex patterns.  
      If the Datafile's instrument_path matches one of these patterns, 
      it is filtered out.
    * The 'stripPrefix' argument gives a prefix that should be stripped 
      from the pathnames.
    * If the 'windowsPath' argument is True, the instrument_pathname value
      is massaged to convert '\' to '/' before filtering and prefix 
      stripping.
