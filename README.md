outsidehacks
============

ec2 info
--------
i didn't add the .pem, because i don't want randos logging in and breaking the
app. i'm sure they're out there, waiting, watching.

to login simply put the .pem that i emailed you into this directory and run
the login script. you may need to change the permissions on the .pem file to
600 .

parsing schedule
----------------
parse.py is the script that scrapes the outside lands schedule site and pulls
in information about each set

artist info
-----------
in order to recommend artists to a user, we first need to get artist to artist
similarities. the artist to artist similarities come from two sources, the
EchoNest's similar artists feature, and Gracenote's genre information. we first
select the top 100 similar artists for each band playing at outside lands. we
assign a similarity score based on the rank provided by the EN. we then look up
the artists that have matching second and third level genres to each of the
bands performing at outside lands and give an additional boost to these
artists.

user recommendations
--------------------
now we can make user to artist recommendations. for a new user, we parse
artist play counts using the facebook graph api. we weight each artist based on
relative play counts. then, for each artist that a user has listened to, we
lookup the outside lands performers that are similar to the artist. we rank
order the artists performing at outside lands by how similar they are to the
user's listening history.

creating the shedule
--------------------
waaa
