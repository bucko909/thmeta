#!/bin/bash

function fetch_page {
	givenurl="$1"
	case "$givenurl" in
		*cmd=edit*)
			echo "Non-existent page: $givenurl" >&2
			return 1
			;;
		*\?page=*)
			echo "Non-existent page: $givenurl" >&2
			return 1
			;;
		http*)
			url="$givenurl"
			;;
		/*)
			echo "Dodgy page: $givenurl" >&2
			url="http://www16.atwiki.jp$givenurl"
			;;
		*)
			echo "Bad url: $givenurl" >&2
			exit 1
			;;
	esac
	n="$(echo "$url"|tr '\/' '__')"
	if [ ! -e pages/"$n" ]; then
		echo "...get page $url" >&2
		wget -q --user-agent=Mozilla "$url" -O temp || exit 1
		mv temp pages/"$n"
		sleep 2
	fi
	cat pages/"$n"
}

function get_main() {
	perl -ne 'BEGIN{undef$/}/<div id="main">(.*)<\/td><\/tr><\/table>/s;print"$1"'
}

function read_circle() {
	CirclePage="$1"
	CircleName="$2"
	echo "Circle: $CircleName ($CirclePage)"
	CircleName="$(echo "$CircleName"|tr '\/' '__')"
	[ -d "data/$CircleName" ] || mkdir "data/$CircleName"
	[ -e "data/$CircleName/albums.txt" ] || fetch_page "$CirclePage" | get_main | perl -ne 'print "$1	$2\n" if m|<li>.*<a[^>]*href="([^"]*)"[^>]*>(.*?)</a|' | grep -v 'page=' > "data/$CircleName/albums.txt"
	a=
	while read AlbumPage AlbumName; do
		a=1
		if ! grep -q "$AlbumPage" data/circles.txt; then
			read_album "$CircleName" "$AlbumPage" "$AlbumName"
		else
			echo "Album $AlbumName ($AlbumPage) is an artist?"
		fi
	done < "data/$CircleName/albums.txt"
	if [ -z "$a" ]; then
		echo "==================================="
		echo "EMPTY CIRCLE: $CircleName"
		echo "==================================="
		echo "$CircleName" >> data/badcircles.txt
	fi
}

function read_album() {
	CircleName="$1"
	AlbumPage="$2"
	AlbumName="$3"
	echo "Album: $AlbumName ($AlbumPage)"
	AlbumName="$(echo "$AlbumName"|tr '\/' '__')"
	[ -e "data/$CircleName/$AlbumName.txt" ] || fetch_page "$AlbumPage" | get_main | perl -ne '($a,$c,@b,@l,@t,@d)=(1,0) if /<table>/; $a=0 if m|</table>|; if($a) {if($a==1 && m|<td[^>]*>(.*)</td>|) { push @t, $1; $c++ } elsif (m|<td[^>]*>(.*)</td>|) { push @d, $1; if (/rowspan="(\d+)"/) { $l[$c] = $1-1; $b[$c] = $d[$#d]; } $c++} while($l[$c]) {$l[$c]--; push @d, $b[$c]; $c++} if(m|</tr>|) { print join(";;;", map { "$t[$_]=$d[$_]" } 0..$#t)."\n" if @d; ($a,$c,@d)=(2,0) } }' > "data/$CircleName/$AlbumName.txt"
	if [ -z "$(cat "data/$CircleName/$AlbumName.txt")" ]; then
		if fetch_page "$AlbumPage" > /dev/null 2> /dev/null; then
			echo "==================================="
			echo "EMPTY ALBUM: $CircleName -> $AlbumName"
			echo "==================================="
			echo "$CircleName	$AlbumName" >> data/badalbums.txt
		fi
		rm "data/$CircleName/$AlbumName.txt"
	fi
}

[ -d pages ] || mkdir pages
[ -d data ] || mkdir data
[ -e data/circles.txt ] || fetch_page http://www16.atwiki.jp/toho/pages/11.html | get_main | perl -ne 'print "$1	$2\n" while m|<a[^>]*href="([^"#]*)"[^>]*>(.*?)<|g' | while read page_url page_content; do
	fetch_page "$page_url" | get_main | perl -ne 'print "$1	$2\n" while m|<li><a[^>]*href="([^"#]*)"[^>]*>(.*?)<|g' | grep -v 'page='
done > data/circles.txt
IFS='	'
while read CirclePage CircleName; do
	read_circle "$CirclePage" "$CircleName"
done < data/circles.txt

