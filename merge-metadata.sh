#!/bin/bash

function ask_input {
	testfile="$1"
	teststring="$2"
	Threshold=10
	if [ ! -s "$testfile" ]; then
		return
	fi
	while true; do
		tre-agrep -s -D 10 -S 20 -I 1 -E $Threshold -i "^$teststring$" $testfile > guesses
		tre-agrep -s -D 1 -S 20 -I 10 -E $Threshold -i "^$teststring$" $testfile >> guesses
		sort -n -t: guesses | cut -d: -f2- | uniq > guessess
		if [ ! -s guessess ]; then
			Threshold="$(dc -e "$Threshold 2*p")"
			continue
		fi
		mv guessess guesses
		cat -n guesses >&2
		echo >&2
		echo -n "0 for none, blank for more... " >&2
		read I <&2
		case "$I" in
			0)
				echo "FAKENBLANK"
				break
				;;
			"")
				Threshold="$(dc -e "$Threshold 2*p")"
				;;
			*)
				sed -n "$I"p guesses
				break
				;;
		esac
	done
	exit
}

find data -maxdepth 1 -type d|cut -d/ -f2 > circletemp
I=0
J=0
find /disks/mediaa/public/Music/Touhou\ lossless\ music\ collection/ -type f -name '*.cue' |sort|while read CUE; do
	#echo "Cue: $CUE"
	I=$(expr $I + 1)
	CircleName="$(echo "$CUE"|perl -pe 'use utf8;s|.*ion/\[([^/\]]*)\].*|\1|')"
	AlbumName="$(echo "$CUE"|perl -pe 's|.*ion/[^/]*/[^ ][^ ]*( \[[^/\]]*\])?\s+((?:[^/\]]\|\[[^\]]*\])+?)(\s*\[[^/\]]*\])?/.*|\2|')"
	if [ ! -d "data/$CircleName" -a ! -L "data/$CircleName" ]; then
		echo
		echo "        $CircleName not found (album: $AlbumName)."
		NewName="$(ask_input circletemp "$CircleName")"
		if [ -z "$NewName" ]; then
			echo "No results. Skipping."
			J=$(expr $J + 1)
			continue
		elif [ "$NewName" = "FAKENBLANK" ]; then
			mkdir "data/$CircleName"
			echo "OK, won't bother with that one."
		else
			ln -s -- "$NewName" "data/$CircleName"
			echo "Made link"
		fi
		echo
	fi
	if [ -e "data/$CircleName/$AlbumName.ignore" ]; then
		J=$(expr $J + 1)
		continue
	fi
	if [ ! -e "data/$CircleName/$AlbumName.txt" -a ! -L "data/$CircleName/$AlbumName.txt" ]; then
		find -L data/"$CircleName" -name '*.txt' -maxdepth 1 -type f|grep -v 'albums.txt'|cut -d/ -f3|sed 's/\(.*\)\..*/\1/' > albumtemp
		echo
		echo "        $AlbumName not found (circle: $CircleName)."
		NewName="$(ask_input albumtemp "$AlbumName")"
		if [ -z "$NewName" ]; then
			echo "No results. Skipping line $I."
			J=$(expr $J + 1)
			continue
		elif [ "$NewName" = "FAKENBLANK" ]; then
			touch "data/$CircleName/$AlbumName.ignore"
			echo "Marking $AlbumName as ignore."
		else
			ln -s -- "$NewName.txt" "data/$CircleName/$AlbumName.txt"
			echo "Made link ($AlbumName->$NewName)"
		fi
	fi

	F="$(ls "data/$CircleName/$AlbumName.txt" 2>/dev/null)"
	if [ -e "$F" ]; then
		if perl -e 'open META, $ARGV[0]; my(%last,%this,@data,@d2); sub add { if($d2[$last{number}]) { print STDERR "$ARGV[0] is multi-CD album with two $last{number}-track CDs\n"; $d2[$last{number}] = 1; return } $d2[$last{number}] = [@data]; @data = () } while(<META>){chomp; %this=(); for (split /;;;/) { /\s*([^=]*?)\s*=\s*(.*?)\s*$/; ($k,$v) = (lc$1, $2); $k=~s/wokrs|works/work/; $k=~s/tunes/tune/; $k =~ s/lylics|lyrics/lyric/; $k =~ s/trach/track/; $v =~ s/<[^>]*>//g; next if $k =~ /length|lendth/; $this{$k}=$v eq ""?$last{$k}:$v} $this{number} = $last{number}+1 unless $this{number} =~ /^\d+$/; add() if $this{number} < $last{number}; $num=$this{number}; $data[$num] ||= {}; $data[$num]{"$_=$this{$_}"}=1 for keys %this; %last=%this } close META; add(); open INPUT, $ARGV[1]; while(<INPUT>){if(/^\s*TRACK\s+(\d+)/){$mt=$1}} close INPUT; die "No album in $ARGV[0] has $mt tracks (".join(", ", grep { $d2[$_]} 0..$#d2)." exist)" unless ref $d2[$mt]; @data=@{$d2[$mt]}; open INPUT, $ARGV[1]; while(<INPUT>){print unless /^    REM COMMENT/;if(/^\s*TRACK\s+(\d+)/){ print qq|    REM COMMENT "|.join(";;;",sort keys %{$data[$1]}).qq|"\n|}}' "$F" "$CUE" > newcue; then
			cp newcue "$CUE"
			echo "Patched $CUE"
		else
			echo "Patch failed on $CUE."
			J=$(expr $J + 1)
		fi
	else
		J=$(expr $J + 1)
		if [ -d "data/$CircleName" ]; then
			echo "Album: $CircleName - $AlbumName"
		else
			echo "Circle: $CircleName"
		fi
	fi
	echo "$J / $I skipped."
done

