#!/usr/bin/perl -T
# Matija Nalis <mnalis-git-openstreetmap@voyager.hr> GPLv3+ started 20150201
# show only open notes for user(s) requested

use strict;
use warnings;
use autodie;
use feature 'say';

use Encode;
use CGI qw(-utf8);
use CGI::Carp;
use URI::Escape;
use DB_File;
use DBM_Filter;
use List::MoreUtils qw(uniq);
use Time::Piece;
use Digest::SHA qw(sha1);

$ENV{'PATH'} = '/usr/bin:/bin';
my $OSN_FILE = 'OK.planet-notes-latest.osn.bz2';
my $DB_NOTES_FILE = 'notes-txt.db';		# Note: same as in myosmnotes_parser.pl
my $DB_USERS_FILE = 'users.db';			# Note: same as in myosmnotes_parser.pl

binmode STDOUT, ":encoding(UTF-8)";
binmode STDERR, ":encoding(UTF-8)";

my $q=CGI->new;
print $q->header (-charset=>'utf-8');

my @users = defined (&CGI::multi_param) ? $q->multi_param('s') : $q->param('s');
my $ignoreold = $q->param('ignoreold') || 0;
if ($ignoreold =~ /^(\d{0,5})$/) { $ignoreold = $1 } else { die "ignoreold must be a number"; }

my $db_mtime = (stat($DB_USERS_FILE))[9];
my $dump_mtime = (stat($OSN_FILE))[9];

my $DB_user = tie my %USER, "DB_File", "$DB_USERS_FILE", O_RDONLY, 0444, $DB_BTREE or die "no DB $DB_USERS_FILE: $!";

my $DB_note = tie my %NOTE, "DB_File", "$DB_NOTES_FILE", O_RDONLY or die "no DB $DB_NOTES_FILE: $!";;
$DB_note->Filter_Value_Push('utf8');

say '<!DOCTYPE html><html><head><meta charset="UTF-8"><title>My OpenStreetMap Notes - results</title><style>';
say 'table { background:#ddd; border-collapse: separate; box-shadow: 0.3rem 0.3rem 0.5rem rgba(0, 0, 0, 0.3); border: 1px solid #777; border-spacing: 8px;}';
say 'th { color: #FFF; background-color: rgba(0, 0, 0, 0.3); text-shadow: 1px 1px 1px #111;';
say '</style></head><body>';


my @all_notes = ();
say 'Searching for OSM Notes for users: ';
foreach my $username (@users) {
    my $org_key = sha1($username);
    my $value = $USER{$org_key};

    my @user_notes = split ' ', $value;
    push @all_notes, @user_notes;
    say '<A HREF="http://www.openstreetmap.org/user/' . uri_escape(encode('UTF-8', $username)) . '/notes">' . $username . '</A>(' . (scalar @user_notes) . ') ';
}

if (@all_notes) {
    say "<p><table><thead><tr><th>Note ID</th><th>last activity</th><th>first description</th></tr></thead><tbody>";
    foreach my $n (uniq sort {$a <=> $b} @all_notes) {
      my ($note_time, $note_text) = split / /, $NOTE{$n}, 2;
      $note_time =~ s/T/ /; $note_time =~ s/Z/ GMT/;
      my $days_old = int ((gmtime() - Time::Piece->strptime($note_time, '%Y-%m-%d %H:%M:%S %Z'))/86400);
      if ($days_old < $ignoreold or !$ignoreold) {
          say '<tr><td><A HREF="http://www.openstreetmap.org/note/' . $n . '">' . $n . '</A></td><td>' . $note_time . '</td><td>' . $note_text . '</td></tr>';
      }
    }
    say '</tbody></table>';
} else {
    say '<br>No open notes found.';
}

say '<p>Database was last updated: ' . localtime($db_mtime);
say '<br>Last <A HREF="http://planet.osm.org/notes/">OSM Notes planet dump</A> timestamp was: ' . localtime($dump_mtime);
say '</body></html>';

exit 0;
