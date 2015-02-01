#!/bin/sh
# Matija Nalis <mnalis-git-openstreetmap@voyager.hr> GPLv3+ started 20150201
# download lastest OSN Notes planet dump

WGET="wget -N -q"
URL_BASE="http://planet.osm.org/notes"
PLANET_NOTES_FILE="planet-notes-latest.osn.bz2"
PLANET_NOTES_MD5="$PLANET_NOTES_FILE.md5"

$WGET "$URL_BASE/$PLANET_NOTES_FILE" || exit 1
$WGET "$URL_BASE/$PLANET_NOTES_MD5"  || exit 2
md5sum --status -c $PLANET_NOTES_MD5 || exit 3

echo "$URL_BASE/$PLANET_NOTES_FILE: `ls -l $PLANET_NOTES_FILE`"
