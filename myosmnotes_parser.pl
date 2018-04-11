#!/usr/bin/perl -T
# Matija Nalis <mnalis-git-openstreetmap@voyager.hr> GPLv3+ started 20150201
# parses OSM notes planet dump into BerkeleyDB

use strict;
use warnings;
use autodie;
use feature 'say';

use DB_File;
use DBM_Filter;
use XML::SAX;

$ENV{'PATH'} = '/usr/bin:/bin';
my $OSN_FILE = 'OK.planet-notes-latest.osn.bz2';
my $DB_NOTES_FILE_FINAL = 'notes-txt.db';		# contains note_id(s) and first comment (Note description)
my $DB_USERS_FILE_FINAL = 'users.db';			# contains user_id(s) and list of all notes he took part in
my $DB_NOTES_FILE_TMP = $DB_NOTES_FILE_FINAL . '.tmp';
my $DB_USERS_FILE_TMP = $DB_USERS_FILE_FINAL . '.tmp';
my $count = 0;

my $start_time = time;
print 'parsing... ';

open (my $xml_file, '-|', "bzcat $OSN_FILE");
#binmode $xml_file, ":encoding(UTF-8)";	# FIXME: segfaults on perl 5.18.2-2ubuntu1.3 on Ubuntu 14.04.5 LTS
binmode STDOUT, ":encoding(UTF-8)";
binmode STDERR, ":encoding(UTF-8)";

my $parser = XML::SAX::ParserFactory->parser(
  Handler => SAX_OSM_Notes->new
);

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


$parser->parse_file($xml_file);

undef $db_user;
undef $db_note;

untie %NOTE;
untie %USER;

rename $DB_NOTES_FILE_TMP, $DB_NOTES_FILE_FINAL;
rename $DB_USERS_FILE_TMP, $DB_USERS_FILE_FINAL;

say 'completed in ' . (time - $start_time) . ' seconds.';

exit 0;




#########################################
######### SAX parser below ##############
#########################################

package SAX_OSM_Notes;
use base qw(XML::SAX::Base);

use strict;
use warnings;

use Data::Dumper;
# when a '<foo>' is seen
sub start_element
{
   my $this = shift;
   my $tag = shift;
   
   if ($tag->{'LocalName'} eq 'note') {
     my $note_id = $tag->{'Attributes'}{'{}id'}{'Value'};
     my $created_at = $tag->{'Attributes'}{'{}created_at'}{'Value'};
     #say "\n/mn/ start note_id=$note_id";
     $this->{'note_ID'} = $note_id;
     $this->{'first_text'} = undef;
     $this->{'last_date'} = $created_at;
     %{$this->{'users'}} = ();
     #Dumper($tag->{Attributes})
   }
   
   if ($tag->{'LocalName'} eq 'comment') {
     my $user_id = $tag->{'Attributes'}{'{}user'}{'Value'};
     my $action = $tag->{'Attributes'}{'{}action'}{'Value'};
     $this->{'last_action'} = $1 if $action =~ /^(?:re)?(opened|closed)$/;
     $this->{'text'} = '';
     if (defined($user_id)) {
       #say "  comment by user_id=$user_id, note_id=" . $this->{'note_ID'};
       $this->{'users'}{$user_id} = 1;
     }
     $this->{'last_date'} = $tag->{'Attributes'}{'{}timestamp'}{'Value'};
     #say '   comment timestamp: '  . $this->{'last_date'};
   }
   
   # call the super class to properly handle the event
   return $this->SUPER::start_element($tag)
}

# content of a element (stuff between <foo> and </foo>) - may be multiple, so concat() it!
sub characters
{
   my $this = shift;
   my $tag = shift;
   $this->{'text'} .= $tag->{'Data'};
}

# when a '</foo>' is seen
sub end_element
{
   my $this = shift;
   my $tag = shift;

   if ($tag->{LocalName} eq 'note') {
     if ($this->{'last_action'} eq 'opened') {	# we're only interested in (re-)opened notes!
        #if ($count++ > 999) { say "exiting on $count for DEBUG, FIXME"; exit 0;} ; print "[$count] ";
        #say "end_note (non-closed), last note_id=" . $this->{'note_ID'} . ", first_text=" . $this->{'first_text'} . ", last_date=" . $this->{'last_date'};
        #print '.';
	#warn "no last_date for id=" . $this->{'note_ID'} if !defined $this->{'last_date'};
	#warn "no first_text for id=" . $this->{'note_ID'} . ' date=' . $this->{'last_date'} if !defined $this->{'first_text'};
        $NOTE{$this->{'note_ID'}} = $this->{'last_date'} . ' ' . ($this->{'first_text'} || ' ');	# save it to database
        $this->{'first_text'} = 1;	# reduce memory usage (no need to keep full text in memory)
        
        foreach my $username (keys %{$this->{'users'}}) {
            #say "\tuser=$username -- note is opened, remember it!";
            if (defined($USER{$username})) {
               $USER{$username} .= ' ' . $this->{'note_ID'};
            } else {
               $USER{$username} = $this->{'note_ID'};
            }
        }
     }
   }
   
  if ($tag->{'LocalName'} eq 'comment') {
    #say 'end_comment[' . $this->{'note_ID'} .  '], full text=' . $this->{'text'};	# full text of this comment
    if (!defined($this->{'first_text'})) {	# only the full text of the FIRST comment (opening of bug)
        $this->{'first_text'} = $this->{'text'};
        $this->{'first_text'} =~ s/\s+/ /g;
    }
    #say "comment tag=" . Dumper($tag);
  }
      
   return $this->SUPER::end_element($tag)
}

1;
