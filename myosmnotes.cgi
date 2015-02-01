#!/usr/bin/perl -T
# Matija Nalis <mnalis-git-openstreetmap@voyager.hr> GPLv3+ started 20150201
# show only open notes for user(s) identified by regexp.

use strict;
use warnings;
use autodie;
use CGI;

my $q=CGI->new;
print $q->header;
my $search = $q->param('s');

print "FIXME Searching for: $search";

exit 0;
