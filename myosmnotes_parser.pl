#!/usr/bin/perl -T
# Matija Nalis <mnalis-git-openstreetmap@voyager.hr> GPLv3+ started 20150201
# parses OSM notes planet dump into BerkeleyDB
#
# WARNING: this branch users unsafe, but FAST parser (e.g. 2:15 minutes instead of 5:15 minutes)
# FIXME: might fail to parse multiline comments and will break if syntax of XML changes even slightly so beware! Use for fast develop testing only! And be buggy otherwise...

use strict;
use warnings;
use autodie;
use feature 'say';

use DB_File;
use DBM_Filter;

$ENV{'PATH'} = '/usr/bin:/bin';
my $OSN_FILE = 'OK.planet-notes-latest.osn.bz2';
my $DB_NOTES_FILE_FINAL = 'notes-txt.db';		# contains note_id(s) and first comment (Note description)
my $DB_USERS_FILE_FINAL = 'users.db';			# contains user_id(s) and list of all notes he took part in
my $DB_NOTES_FILE_TMP = $DB_NOTES_FILE_FINAL . '.tmp';
my $DB_USERS_FILE_TMP = $DB_USERS_FILE_FINAL . '.tmp';
my $count = 0;

my $DECOMPRESSOR = 'bzcat';
if (-e '/usr/bin/pbzip2') { $DECOMPRESSOR = 'pbzip2 -dc' }  # use faster decompressing if available


#$| = 1; # FIXME only enable for debug to avoid interleaved STDOUT/STDERR
my $start_time = time;
print 'parsing Q&D... ';

open (my $xml_file, '-|', "$DECOMPRESSOR $OSN_FILE");
#open my $xml_file, '<', 'a';
binmode $xml_file, ":encoding(UTF-8)";	# FIXME: segfaults on perl 5.18.2-2ubuntu1.3 on Ubuntu 14.04.5 LTS when using SAX?
binmode STDOUT, ":encoding(UTF-8)";
binmode STDERR, ":encoding(UTF-8)";

print 'opened bz2... ';

# case insensitive compare of hash keys
sub db_compare {
    my($key1, $key2) = @_;
    lc $key1 cmp lc $key2;
}
$DB_BTREE->{'compare'} = \&db_compare;
                                                                
#use open qw( :encoding(UTF-8) :std );

{ no autodie qw(unlink); unlink $DB_USERS_FILE_TMP; unlink "__db.$DB_USERS_FILE_TMP"; }
my $db_user = tie my %USER, "DB_File", "$DB_USERS_FILE_TMP", O_RDWR|O_CREAT, 0666, $DB_BTREE;
$db_user->Filter_Key_Push('utf8');

{ no autodie qw(unlink); unlink $DB_NOTES_FILE_TMP; unlink "__db.$DB_NOTES_FILE_TMP"; }
my $db_note = tie my %NOTE, "DB_File", "$DB_NOTES_FILE_TMP";
$db_note->Filter_Value_Push('utf8');

print 'go... ';
parse_file($xml_file);

undef $db_user;
undef $db_note;

untie %NOTE;
untie %USER;

rename $DB_NOTES_FILE_TMP, $DB_NOTES_FILE_FINAL;
rename $DB_USERS_FILE_TMP, $DB_USERS_FILE_FINAL;

say 'completed in ' . (time - $start_time) . ' seconds.';

exit 0;




###################################################
######### QUICK & DIRTY parser below ##############
###################################################

sub fix_entities($)
{
  my ($txt) = @_;
  return $txt if !$txt;
  
  $txt =~ s/^\s*//g;
  $txt =~ s/\s*$//g;
  
  $txt =~ s{&lt;}{<}gi;
  $txt =~ s{&gt;}{>}gi;
  $txt =~ s{&quot;}{"}gi;
  $txt =~ s{&#13;}{}gi;
  $txt =~ s{&amp;}{&}gi;    # this one must be at the end!

  return $txt;
}

sub parse_file
{
   my ($xml_file) = @_;
   my $this = {};
   $this->{'inside_comment'} = 0;
   
   while (my $line = <$xml_file>) {
   
    #print "DEBUG1: parsing line: $line";

    # empty lines
    if ($line =~ /^\s*$/) { next };
    # <?xml>
    if ($line =~ /^\s*<\?xml.*\?>\s*$/) { next };

    # <osm-notes>, </osm-notes>
    if ($line =~ /^\s*<\/?osm-notes>\s*$/) { next };
    
    # <note ... />
    if ($line =~ /^\s*<note id.*\/>\s*$/) { next };    # skip empty notes without sub-tags
   
    # <note>     
    if ($line =~ s/^\s*<note id="(\d+?)".*created_at="(.+?)">\s*$//) {
       my $note_id = $1;
       my $created_at = $2;
       $this->{'inside_comment'} = 0;
       #say "\n/mn/ start note_id=$note_id";
       $this->{'note_ID'} = $note_id;
       $this->{'first_text'} = undef;
       $this->{'first_user'} = undef;
       $this->{'last_date'} = $created_at;
       %{$this->{'users'}} = ();
     }

     #print "DEBUG2: parsing line: $line";
     # <comment>
     if ($line =~ s/^\s*<comment action="(.+?)".*?timestamp="(.+?)"(?: .*?user="(.+?)")?.*?>//) {
       my $action = $1;
       my $timestamp = $2;
       my $user_id = $3 ? fix_entities($3) : '';
       $this->{'inside_comment'} = 1;
       $this->{'last_action'} = $1 if $action =~ /^(?:re)?(opened|closed)\s*$/;
       $this->{'text'} = '';  # start with empty string, we'll fill it later in characters()
       $this->{'last_comment_is_resurvey'} = 0;   # every new comment resets it to 0 as it does NOT contain "#surveyme"  at this time (as "text" is empty)
       if (defined($user_id)) {
         #say "  comment ($action) by user_id=$user_id, note_id=" . $this->{'note_ID'};
         if (!defined ($this->{'first_user'})) {
            #say "  first user/creator of this note: $user_id";
            $this->{'first_user'} = $user_id;
         }
         $this->{'users'}{$user_id} = 1;
       } else { 
         #say  "no user specified"
       }
       $this->{'last_date'} = $timestamp;
       #say '   comment timestamp: '  . $this->{'last_date'};
       #use Data::Dumper; say Dumper($this);
     }

     #print "DEBUG3: parsing line (inside_comment=" . $this->{'inside_comment'} . "): $line";
     # concat text between tags
     if ($this->{'inside_comment'} and $line =~ s/^\s*([^<]*?)\s*($|<)/$2/) {
       #say  '     adding >' . $1 . '< to text: >' . $this->{'text'} . '<';
       $this->{'text'} .= $1 . ' ';
     }
     
     #print "DEBUG4: parsing line: $line";
     # </comment>
     if ($line =~ s/^\s*<\/comment>\s*$//) {
       $this->{'inside_comment'} = 0;
       my $current_text = $this->{'text'};
       chop $current_text;
       if ($current_text =~ /#surveyme/i) {
           $this->{'last_comment_is_resurvey'} = 1;
       }
       #say 'end_comment[' . $this->{'note_ID'} .  '], surveyme=' . $this->{'last_comment_is_resurvey'} . ' full current text=' . $current_text;	# full text of this comment
       if (!defined($this->{'first_text'})) {	# only the full text of the FIRST comment (opening of bug)
           $this->{'first_text'} = $current_text;
           $this->{'first_text'} =~ s/\s+/ /g;
       }
       #say "comment tag=" . Dumper($tag);
     }

     #print "DEBUG5: parsing line: $line";
     # </note>
     if ($line =~ s/^\s*<\/note>\s*$//) {
       #use Data::Dumper; say Dumper($this);
       if (defined($this->{'last_action'}) and $this->{'last_action'} eq 'opened') {	# we're only interested in (re-)opened notes!
          #if ($count++ > 999) { say "exiting on $count for DEBUG, FIXME"; exit 0;} ; print "[$count] ";
          #say "end_note (non-closed), last note_id=" . $this->{'note_ID'} . ", first_text=" . $this->{'first_text'} . ", last_date=" . $this->{'last_date'};
          #print '.';
          #warn "no last_date for id=" . $this->{'note_ID'} if !defined $this->{'last_date'};
          #warn "no first_text for id=" . $this->{'note_ID'} . ' date=' . $this->{'last_date'} if !defined $this->{'first_text'};
          $NOTE{$this->{'note_ID'}} = $this->{'last_comment_is_resurvey'} . ' ' . $this->{'last_date'} . ' ' . fix_entities($this->{'first_text'} || ' ');	# save it to database
          $this->{'first_text'} = 1;	# reduce memory usage (no need to keep full text in memory, but still evalute to true)
          
          foreach my $username (keys %{$this->{'users'}}) {
              #say "\tuser=$username -- note is opened, remember it!";
              my $prefix = defined($USER{$username}) ? ' ' : '';
              $prefix .= ($username eq $this->{'first_user'}) ? 'c' : 'm';  # c=creator of note, m=only commented on the note
              $USER{$username} .= $prefix . $this->{'note_ID'};
          }
       }
       $this = {};
     }

     if ($line) {
       die "line should be empty by now, but it is: $line";
     }
     
   }                                                            # end while
   
   
}
