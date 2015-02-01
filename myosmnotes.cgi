#!/usr/bin/perl -T
# Matija Nalis <mnalis-git-openstreetmap@voyager.hr> GPLv3+ started 20150201
# show only open notes for user(s) identified by regexp.

use strict;
use warnings;
use autodie;
use feature 'say';

use Encode;
use CGI;
use CGI::Carp;
use DB_File;

$ENV{'PATH'} = '/usr/bin:/bin';
my $DB_NOTES_FILE = 'notes-txt.db';		# Note: same as in myosmnotes_parser.pl
my $DB_USERS_FILE = 'users.db';			# Note: same as in myosmnotes_parser.pl


my $q=CGI->new;
print $q->header (-charset=>'utf-8');
my $search = $q->param('s');
my $key = encode_utf8($search);

tie my %USER, "DB_File", "$DB_USERS_FILE", O_RDONLY;
tie my %NOTE, "DB_File", "$DB_NOTES_FILE", O_RDONLY;

say '<!DOCTYPE html><html><head><meta charset="UTF-8"><title>My OpenStreetMap Notes - results</title></head><body>';
say "Searching for OSM Notes for user: <strong>$search</strong><p>";

my $notes = $USER{$key};
if (defined($notes)) {
    say "FOUND $notes<p>";
    foreach my $n (split / /, $notes) {
      say "NOTE{$n}=$NOTE{$n}<br>";
    }
} else {
    say "nothing found for >$key<";
}

say '</body></html>';

exit 0;
