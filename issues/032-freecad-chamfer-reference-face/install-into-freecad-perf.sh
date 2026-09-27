#!/usr/bin/env bash
# install-into-freecad-perf.sh [target] [revert]: the 032 chamfer pair for FreeCAD 1.1.1 (FreeCAD-perf), md5-guarded.
#   lib/_PartDesign.pyd   stock d71ee94f... -> 032 58a3c6df...  (fc111-chamfer mig111/chamfer c41ddba on 9e5873b)
#   lib/PartDesignGui.pyd stock 75896d6b... -> 032 ce9b6c9c...  (a PAIR: the GUI module reads the new Chamfer members)
# Stock copies go to <target>/_replaced/K-032/. Nothing is changed unless BOTH files are stock or ours. Close FreeCAD
# (or accept that a running one keeps the old modules until restarted: a mapped file is renamed aside, never overwritten).
set -u
T=${1:-C:/dev/FreeCAD-perf}; MODE=${2:-install}
S=C:/dev/freecad-kernel-fixes/build/variants801/chamfer/fc111
LIST="_PartDesign.pyd d71ee94f129178f016a5a4f6b530a8ee 58a3c6df139e535d19c60ee2420a052a
PartDesignGui.pyd 75896d6baba78aee74378d7bf0623268 ce9b6c9c6eb47a9b5322be36e2613181"
B=$T/_replaced/K-032
m() { md5sum "$1" 2>/dev/null | cut -c1-32; }
bad=0
while read -r n s o; do
  c=$(m "$T/lib/$n")
  [ "$c" = "$s" ] || [ "$c" = "$o" ] || { echo "REFUSE $n: md5 '$c' is neither stock $s nor ours $o"; bad=1; }
  if [ "$MODE" = revert ]; then [ "$(m "$B/$n")" = "$s" ] || [ "$c" = "$s" ] || { echo "REFUSE $n: no stock copy in $B"; bad=1; }
  else [ "$(m "$S/$n")" = "$o" ] || { echo "REFUSE $n: source md5 wrong"; bad=1; }; fi
done <<< "$LIST"
[ $bad = 0 ] || { echo "REFUSED - nothing changed"; exit 3; }
put() {  # put <src> <dst>: copy to .new, rename (a mapped dst is renamed aside first)
  rm -f "$2.new"; cp -f "$1" "$2.new" || return 1
  mv -f "$2.new" "$2" 2>/dev/null && return 0
  mkdir -p "$B/.inuse"; mv "$2" "$B/.inuse/$(basename "$2").$(date +%Y%m%d-%H%M%S)" && mv -f "$2.new" "$2"
}
mkdir -p "$B"
while read -r n s o; do
  c=$(m "$T/lib/$n")
  if [ "$MODE" = revert ]; then
    [ "$c" = "$s" ] && { echo "SKIP $n: already stock"; continue; }
    put "$B/$n" "$T/lib/$n" && [ "$(m "$T/lib/$n")" = "$s" ] && echo "RESTORED $n" || { echo "FAIL $n"; exit 5; }
  else
    [ "$c" = "$o" ] && { echo "SKIP $n: already ours"; continue; }
    [ -e "$B/$n" ] || cp -p "$T/lib/$n" "$B/$n"
    [ "$(m "$B/$n")" = "$s" ] || { echo "FAIL $n: backup md5 wrong"; exit 4; }
    put "$S/$n" "$T/lib/$n" && [ "$(m "$T/lib/$n")" = "$o" ] && echo "INSTALLED $n: $s -> $o" || { echo "FAIL $n"; exit 5; }
  fi
done <<< "$LIST"
echo DONE
