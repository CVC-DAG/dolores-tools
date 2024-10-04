#!/bin/bash

# $1 argument: root path to the collection of packs

WATCHLIST=/tmp/watchlist

echo "Files to be watched:"
echo "===================="
find "$1" -regex ".+\.mscz"
echo "===================="

find "$1" -regex ".+\.mscz" > "$WATCHLIST"

# -e modify -e delete_self -e close_write -e attrib
entr -ar inotifywait -m -r -q -e modify -e delete_self --format '%w %e' --fromfile /_ <<< "${WATCHLIST}" | while read FILE EVENT
do
  echo "Triggered $EVENT event on file: $FILE"
  case "$EVENT" in
    # We assume that deleting the file means overwriting, so we make sure to reset the file for inotify
    "DELETE_SELF") echo "$FILE" >> "$WATCHLIST"; python3 ./validation_tools/validate_and_convert.py --mscz "$FILE" --overwrite ;;
    "MODIFY") python3 ./validation_tools/validate_and_convert.py --mscz "$FILE" --overwrite ;;
    *) echo "Event not processed." ;;
  esac
done