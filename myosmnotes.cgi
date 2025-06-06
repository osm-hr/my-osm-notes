#!/usr/bin/perl -T
# Matija Nalis <mnalis-git-openstreetmap@voyager.hr> GPLv3+ started 20150201
# show only open notes for user(s) requested

use strict;
use warnings;
use autodie;
use feature 'say';

use Encode;
use POSIX qw(strftime);
use CGI qw(-utf8 escapeHTML);
use CGI::Carp;
use URI::Escape;
use DB_File;
use DBM_Filter;
use List::MoreUtils qw(uniq);
use Time::Piece;

$ENV{'PATH'} = '/usr/bin:/bin';
delete @ENV{ 'IFS', 'CDPATH', 'ENV', 'BASH_ENV' };

my $OSN_FILE = 'OK.planet-notes-latest.osn.bz2';
my $DB_NOTES_FILE = 'notes-txt.db';		# Note: same as in myosmnotes_parser.pl
my $DB_USERS_FILE = 'users.db';			# Note: same as in myosmnotes_parser.pl

binmode STDOUT, ":encoding(UTF-8)";
binmode STDERR, ":encoding(UTF-8)";

my $db_mtime = (stat($DB_USERS_FILE))[9];
my $dump_mtime = (stat($OSN_FILE))[9];
my $last_modified = strftime("%a, %d %b %Y %H:%M:%S GMT", gmtime($db_mtime));  # RFC 2822-compatible last-modified timestamp

my $q=CGI->new;
my %HTTP_COMMON_HEADERS = (
       -charset => 'utf-8',
       -expires => '+600s',
);

# adds some some security HTTP headers
$HTTP_COMMON_HEADERS{'-Strict-Transport-Security'} = q{max-age=15768000} if defined $ENV{'HTTPS'} and $ENV{'HTTPS'};  # enable HSTS if https:// is active

# CORS
my $allowed_origin = $q->http('Origin'); $allowed_origin = ($q->https() ? 'https' : 'http').'://'.$q->server_name if !defined $allowed_origin;  # allow only same domain access
$HTTP_COMMON_HEADERS{'-Access_Control_Allow_Origin'} = $allowed_origin if defined $allowed_origin;
$HTTP_COMMON_HEADERS{'-Access_Control_Allow_Methods'} = q{GET, POST, HEAD};

# misc
$HTTP_COMMON_HEADERS{'-Referrer-Policy'} = q{origin-when-cross-origin, strict-origin-when-cross-origin};
$HTTP_COMMON_HEADERS{'-X-Content-Type-Options'} =  q{nosniff};
$HTTP_COMMON_HEADERS{'-X-Xss-Protection'} = q{1; mode=block};
$HTTP_COMMON_HEADERS{'-X-Frame-Options'} = q{DENY};
$HTTP_COMMON_HEADERS{'-Feature-Policy'} = q{camera 'none'; microphone 'none'; accelerometer 'none'; gyroscope 'none'; payment 'none'; encrypted-media 'none'; autoplay 'none'; usb 'none'; };

# CSP
$HTTP_COMMON_HEADERS{'-Content-Security-Policy'}  = q{default-src 'none'; };    # sane CSP default, do not change!
$HTTP_COMMON_HEADERS{'-Content-Security-Policy'} .= q{img-src 'self'; };
$HTTP_COMMON_HEADERS{'-Content-Security-Policy'} .= q{script-src 'none'; };
$HTTP_COMMON_HEADERS{'-Content-Security-Policy'} .= q{style-src 'self'; };


# avoid re-requesting data from server if we know database hasn't been modified yet
my $if_modified_since = $q->http('If-Modified-Since');
if (defined $if_modified_since && $if_modified_since eq $last_modified) {   # NB: we should be smarter and actually compare which one is newer (as it *might* be returned in different TZ), but this should be good enough for majority of the cases
    print $q->header(-status  => '304 Not Modified', %HTTP_COMMON_HEADERS);
    exit;
}

print $q->header (%HTTP_COMMON_HEADERS, '-Last-Modified' => $last_modified);

my @users = defined (&CGI::multi_param) ? $q->multi_param('s') : $q->param('s');
my $ignoreold = $q->param('ignoreold') || 0;
if ($ignoreold =~ /^(\d{0,5})$/) { $ignoreold = $1 } else { die "ignoreold must be a number"; }
my $skip_surveyme = $q->param('skip_surveyme') || 0;
if ($skip_surveyme =~ /^(0|1|on)$/i) { $skip_surveyme = $1 } else { die "skip_surveyme must be a number"; }
my $skip_notcreator = $q->param('skip_notcreator') || 0;
if ($skip_notcreator =~ /^(0|1|on)$/i) { $skip_notcreator = $1 } else { die "skip_notcreator must be a number"; }



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

say '<!DOCTYPE html><html><head><meta charset="UTF-8"><title>My OpenStreetMap Notes - results</title>';
say '<META NAME="ROBOTS" CONTENT="NOFOLLOW"><link href="myosmnotes.css" rel="stylesheet" type="text/css" media="screen">';
say '</head><body>';


my @all_notes = ();
say 'Searching for OSM Notes for users: ';
foreach my $org_key (@users) {
    my $found_key = $org_key;
    #my $value = $USER{$found_key};
    my $value = ''; $DB_user->seq($found_key, $value, R_CURSOR );	# this will actually update $found_key to what is in the database, not what was provided (which could be in different case, since we're case insensitive due to db_compare() override! )
    next if !$org_key;  # skip empty fields if added by JS

    #my $upg_org_key = $org_key; utf8::upgrade($org_key);
    #my $upg_key = $org_key; utf8::upgrade($org_key);
    #say "DEBUG unsafe: seeking for: $user: org=$org_key (upg=\L$upg_org_key), current=$found_key (upg=\L$upg_key), value=$value";

    #say "DEBUG unsafe: seeking: org=$org_key (lc=\L$org_key), current=$found_key (lc=\L$found_key), value=$value";

    if ( ($found_key ne $org_key) and (lc $found_key ne lc $org_key) ) { $value = ''; $found_key = $org_key; }		# note however, $DB_user->seq() will return partial matches too, which we don't want, so make sure we only match keys whose only difference is case
    my @user_notes = split ' ', $value;
    push @all_notes, @user_notes;
    say '<A HREF="http://www.openstreetmap.org/user/' . uri_escape(encode('UTF-8', $found_key)) . '/notes">' . escapeHTML($found_key) . '</A>(' . escapeHTML(scalar @user_notes) . ') ';
}

if (@all_notes) {
    say "<p><table><thead><tr><th>Note ID</th><th>last activity</th><th>first description</th></tr></thead><tbody>";
    foreach my $nc (uniq sort {substr($a,1) <=> substr($b,1)} @all_notes) {
      my $n = substr($nc,1);   # extract just a number of a note
      next if $skip_notcreator and substr($nc,0,1) ne 'c';  # if requested, ignore notes which we didn't create
      my ($last_is_resurvey, $note_time, $note_text) = split / /, $NOTE{$n}, 3;
      next if $skip_surveyme and $last_is_resurvey;         # if requested, ignore notes with "#surveyme" in last comment
      $note_time =~ s/T/ /; $note_time =~ s/Z/ GMT/;
      my $days_old = int ((gmtime() - Time::Piece->strptime($note_time, '%Y-%m-%d %H:%M:%S %Z'))/86400);
      if ($days_old < $ignoreold or !$ignoreold) {
          say '<tr><td><A HREF="http://www.openstreetmap.org/note/' . uri_escape($n) . '">' . escapeHTML($n) . '</A></td><td>' . escapeHTML($note_time) . '</td><td>' . escapeHTML($note_text) . '</td></tr>';
      }
    }
    say '</tbody></table>';
} else {
    say '<br>No open notes found.';
}

say '<p>Database was last updated: ' . escapeHTML(localtime($db_mtime)."");
say '<br>Last <A HREF="http://planet.osm.org/notes/">OSM Notes planet dump</A> timestamp was: ' . escapeHTML(localtime($dump_mtime)."");
say '</body></html>';

exit 0;
