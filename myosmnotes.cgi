#!/usr/bin/perl -T
# Matija Nalis <mnalis-git-openstreetmap@voyager.hr> GPLv3+ started 20150201
# show only open notes for user(s) requested

use strict;
use warnings;
use autodie;
use feature 'say';

use Encode;
use CGI;
use CGI::Carp;
use URI::Escape;
use DB_File;
use List::MoreUtils qw(uniq);

$ENV{'PATH'} = '/usr/bin:/bin';
my $OSN_FILE = 'OK.planet-notes-latest.osn.bz2';
my $DB_NOTES_FILE = 'notes-txt.db';		# Note: same as in myosmnotes_parser.pl
my $DB_USERS_FILE = 'users.db';			# Note: same as in myosmnotes_parser.pl


my $q=CGI->new;
print $q->header (-charset=>'utf-8');

my @users = $q->param('s');

my $db_mtime = (stat($DB_USERS_FILE))[9];
my $dump_mtime = (stat($OSN_FILE))[9];

tie my %USER, "DB_File", "$DB_USERS_FILE", O_RDONLY;
tie my %NOTE, "DB_File", "$DB_NOTES_FILE", O_RDONLY;

say '<!DOCTYPE html><html><head><meta charset="UTF-8"><title>My OpenStreetMap Notes - results</title><style>';
say 'table { background:#ddd; border-collapse: separate; box-shadow: 0.3rem 0.3rem 0.5rem rgba(0, 0, 0, 0.3); border: 1px solid #777; border-spacing: 8px;}';
say 'th { color: #FFF; background-color: rgba(0, 0, 0, 0.3); text-shadow: 1px 1px 1px #111;';
say '</style></head><body>';
say '<font color=red>DEVEL VERSION FIXME DELME</font><p>';




# FIXME TODO - add support for multiple user searching, and mention in docs (add html support?) - also show here all users, and dedupe notes when using multiple users!
my @all_notes = ();
say 'Searching for OSM Notes for users: ';
foreach my $user (@users) {
    my $key = encode_utf8($user);
    my @user_notes = split ' ', $USER{$key};
    push @all_notes, @user_notes;
    say '<A HREF="http://www.openstreetmap.org/user/' . uri_escape($key) . '/notes">' . $key . '</A>(' . (scalar @user_notes) . ') ';
}

if (@all_notes) {
    say "<p><table><thead><tr><th>Note ID</th><th>last activity</th><th>first description</th></tr></thead><tbody>";
    foreach my $n (uniq sort {$a <=> $b} @all_notes) {
      my ($note_time, $note_text) = split / /, $NOTE{$n}, 2;
      $note_time =~ s/T/ /; $note_time =~ s/Z/ GMT/;
      say '<tr><td><A HREF="http://www.openstreetmap.org/note/' . $n . '">' . $n . '</A></td><td>' . $note_time . '</td><td>' . $note_text . '</td></tr>';
    }
    say '</tbody></table>';
} else {
    say '<br>No open notes found.';
}

say '<p>Database was last updated: ' . localtime($db_mtime);
say '<br>Last OSM Notes planet dump timestamp was: ' . localtime($dump_mtime);
say '</body></html>';

exit 0;
