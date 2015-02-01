My OpenStreetMap Notes 

This will use OpenStreetMap.org Notes dump (updated daily) and show you only unresolved (not-closed) Notes for specified user(s).

This is currently needed (as of 2015-02-01) since your user page at OSM will
only show all bugs (open and closed) mixed together sorted by date, so if
you use the Notes a lot, you'll have to wade through dozens (or hundreds!)
of pages so you can find Notes that are still open.

Code allows for searching bugs for multiple users at once (removing
duplicates in the process: for example if bug was created by one user, and
commented on by another) by using "s" CGI parameter multiple times (for example:
<A HREF="https://torres.voyager.hr/~mnalis/my-osm-notes/myosmnotes.cgi?s=Matija+Nalis;s=mnalis+ALTernative;s=ksenija">myosmnotes.cgi?s=Matija+Nalis;s=mnalis+ALTernative;s=ksenija</A>)


You can also use my <A HREF="https://torres.voyager.hr/~mnalis/my-osm-notes/">developer instance</A> directly.

(OSM Notes were previously known as OSMBugs while hosted at 3rd party servers)
