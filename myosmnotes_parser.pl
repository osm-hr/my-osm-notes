#!/usr/bin/perl -T
# Matija Nalis <mnalis-git-openstreetmap@voyager.hr> GPLv3+ started 20150201
# parses OSM notes planet dump into BerkeleyDB

use utf8;

use strict;
use warnings;
use autodie;
use feature 'say';

use DB_File;
use XML::SAX;

$ENV{'PATH'} = '/usr/bin:/bin';
my $OSN_FILE = 'OK.planet-notes-latest.osn.bz2';
my $DB_NOTES_FILE = 'notes-txt.db';		# contains note_id(s) and first comment (Note description)
my $DB_USERS_FILE = 'users.db';			# contains user_id(s) and list of all notes he took part in
my $count = 0;

my $start_time = time;
print 'parsing... ';

#open (my $xml_file, '-|:encoding(utf8)', "bzcat $OSN_FILE");
open (my $xml_file, '-|', "bzcat $OSN_FILE");
binmode STDOUT, ":utf8"; 

my $parser = XML::SAX::ParserFactory->parser(
  Handler => SAX_OSM_Notes->new
);

use open qw( :encoding(UTF-8) :std );

{ no autodie qw(unlink); unlink $DB_USERS_FILE; unlink "__db.$DB_USERS_FILE"; }
tie my %USER, "DB_File", "$DB_USERS_FILE";

{ no autodie qw(unlink); unlink $DB_NOTES_FILE; unlink "__db.$DB_NOTES_FILE"; }
tie my %NOTE, "DB_File", "$DB_NOTES_FILE";


$parser->parse_file($xml_file);

say 'completed in ' . (time - $start_time) . ' seconds.';

exit 0;




#########################################
######### SAX parser below ##############
#########################################

package SAX_OSM_Notes;
use base qw(XML::SAX::Base);
use Encode;


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
     #say "\n/mn/ start note_id=$note_id";
     $this->{'note_ID'} = $note_id;
     $this->{'first_text'} = undef;
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
        #say "end_note (non-closed), last note_id=" . $this->{'note_ID'} . ", first_text=" . $this->{'first_text'};
        #print '.';
        $NOTE{$this->{'note_ID'}} = encode_utf8($this->{'first_text'});	# save it to database
        $this->{'first_text'} = 1;	# reduce memory usage (no need to keep full text in memory)
        
        foreach my $u (keys %{$this->{'users'}}) { 
            my $key = encode_utf8($u);
            #say "\tuser=$u -- note is opened, remember it!";
            if (defined($USER{$key})) {
               $USER{$key} .= ' ' . $this->{'note_ID'};
            } else {
               $USER{$key} = $this->{'note_ID'};
            }
        }
     }
   }
   
  if ($tag->{'LocalName'} eq 'comment') {
    # say "end_comment[" . $this->{'note_ID'} .  "], full text=". $this->{'text'};	# full text of this comment
    if (!defined($this->{'first_text'})) {	# only the full text of the FIRST comment (opening of bug)
        $this->{'first_text'} = $this->{'text'};
        $this->{'first_text'} =~ s/\s+/ /g;
    }
  }
      
   return $this->SUPER::end_element($tag)
}

1;
