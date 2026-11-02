#!/bin/sh
# Checks that the site version in VERSION matches the footer and every ?v= cache tag in index.html.
cd "$(dirname "$0")/.." || exit 1
v=$(tr -d '[:space:]' < VERSION)
echo "$v" | grep -Eq '^[0-9]{2}\.[0-9]{2}\.[0-9]{2}$' || { echo "VERSION '$v' is not XX.XX.XX"; exit 1; }
grep -q "Site v$v<" index.html || { echo "Footer doesn't show Site v$v"; exit 1; }
bad=$(grep -o '?v=[^"]*' index.html | grep -v "?v=$v\$")
[ -z "$bad" ] || { echo "Cache tags not matching $v:"; echo "$bad"; exit 1; }
echo "Site version $v OK"
