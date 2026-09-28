#!/bin/bash
cd /c/dev/occt8-mig/offset-034b2/rv3
REV="rev_a_off-2 rev_a_off-2.8 rev_a_thkbot-2 rev_n_off-2 rev_n_off-2.8 rev_n_thkbot-2 rev_w_off-2 rev_w_off-2.8 rev_w_thkbot-2 rev_a_off-0.8_ctl rev_a_off-2_int"
TRI="tri_a_off-3 tri_a_off-4 tri_a_thktop-3 tri_n_off-3 tri_n_off-4 tri_n_thktop-3 tri_w_off-3 tri_w_off-4 tri_w_thktop-3 tri_a_off-1.5_ctl tri_a_off-3_int"
OBL="obl_a_off-2 obl_a_off-3 obl_n_off-2 obl_n_off-3 obl_w_off-2 obl_w_off-3 obl_a_off-1_ctl obl_a_off-2_int"
BMP="bmp_a_off-2 bmp_a_off-2.8 bmp_n_off-2 bmp_n_off-2.8 bmp_w_off-2 bmp_w_off-2.8 bmp_a_off-1_ctl"
for RC in "$@"; do
  TMO=150 bash loop.sh $RC rev $REV
  TMO=150 bash loop.sh $RC tri $TRI
  TMO=150 bash loop.sh $RC obl $OBL
  TMO=150 bash loop.sh $RC bmp $BMP
done
echo ALLDONE
