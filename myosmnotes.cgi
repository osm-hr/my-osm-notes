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


# case insensitive compare of hash keys
sub db_compare {
    my($key1, $key2) = @_;
    lc $key1 cmp lc $key2;
}
$DB_BTREE->{'compare'} = \&db_compare;
                                                                
my $DB_user = tie my %USER, "DB_File", "$DB_USERS_FILE", O_RDONLY, 0444, $DB_BTREE or die "no DB $DB_USERS_FILE: $!";
$DB_user->Filter_Key_Push('utf8');

my $DB_note = tie my %NOTE, "DB_File", "$DB_NOTES_FILE", O_RDONLY or die "no DB $DB_NOTES_FILE: $!";;
$DB_note->Filter_Value_Push('utf8');

say '<!DOCTYPE html><html><head><meta charset="UTF-8"><title>My OpenStreetMap Notes - results</title><style>';
say 'table { background:#ddd; border-collapse: separate; box-shadow: 0.3rem 0.3rem 0.5rem rgba(0, 0, 0, 0.3); border: 1px solid #777; border-spacing: 8px;}';
say 'th { color: #FFF; background-color: rgba(0, 0, 0, 0.3); text-shadow: 1px 1px 1px #111;';
say '</style></head><body>';


my @all_notes = ();
say 'Searching for OSM Notes for users: ';
foreach my $org_key (@users) {
    my $found_key = $org_key;
    #my $value = $USER{$found_key};
    my $value = ''; $DB_user->seq($found_key, $value, R_CURSOR );	# this will actually update $found_key to what is in the database, not what was provided (which could be in different case, since we're case insensitive due to db_compare() override! )

    #my $upg_org_key = $org_key; utf8::upgrade($org_key);
    #my $upg_key = $org_key; utf8::upgrade($org_key);
    #say "seeking for: $user: org=$org_key (upg=\L$upg_org_key), current=$found_key (upg=\L$upg_key), value=$value";

    #say "seeking: org=$org_key (lc=\L$org_key), current=$found_key (lc=\L$found_key), value=$value";

    if ( ($found_key ne $org_key) and (lc $found_key ne lc $org_key) ) { $value = ''; $found_key = $org_key; }		# note however, $DB_user->seq() will return partial matches too, which we don't want, so make sure we only match keys whose only difference is case
    my @user_notes = split ' ', $value;
    push @all_notes, @user_notes;
    say '<A HREF="http://www.openstreetmap.org/user/' . uri_escape(encode('UTF-8', $found_key)) . '/notes">' . $found_key . '</A>(' . (scalar @user_notes) . ') ';
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
