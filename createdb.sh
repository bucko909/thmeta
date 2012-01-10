#!/bin/bash

function drop_table() {
	name="$1"
	shift
	for def in "$@"; do
		colname=${def%=*}
		tname=$name"_"$colname
		if [ "$colname" = "$def" ]; then
			rtname=${def%_id}
			tname=$name"_"$rtname
		fi
		echo "DROP TABLE $tname;"
	done
	echo "DROP TABLE $name CASCADE;"
	echo "DROP SEQUENCE $name""_id_seq;"
}
function create_table() {
	name="$1"
	shift
	echo "CREATE SEQUENCE $name""_id_seq START 1 INCREMENT 1;"
	echo -n "CREATE TABLE $name ($name""_id INT PRIMARY KEY DEFAULT nextval('$name""_id_seq') NOT NULL"
	for def in "$@"; do
		colname=${def%=*}
		type=${def#*=}
		if [ "$colname" = "$def" ]; then
			table=${def%_id}
			type="INT REFERENCES $table($colname)"
		fi
		echo -n ", $name""_c$colname $type"
	done
	echo ");"
	for def in "$@"; do
		colname=${def%=*}
		tname=$name"_"$colname
		type=${def#*=}
		if [ "$colname" = "$def" ]; then
			rtname=${def%_id}
			tname=$name"_"$rtname
			type="INT REFERENCES $rtname($colname)"
		fi
		echo "CREATE TABLE $tname ($name""_id INT NOT NULL REFERENCES $name($name""_id), $name""_$colname $type NOT NULL UNIQUE);"
	done
}


drop_table album atwiki_id name=TEXT circle_id event_id
drop_table circle atwiki_id name=TEXT
drop_table event atwiki_id name=TEXT date=DATE
drop_table atwiki url=TEXT

#create_table atwiki url=TEXT
#create_table event atwiki_id name=TEXT date=DATE
#create_table circle atwiki_id name=TEXT
#create_table album atwiki_id name=TEXT circle_id event_id
