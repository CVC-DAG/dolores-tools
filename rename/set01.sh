#!/bin/bash

# Root path to pack directory as argument
ROOT_PATH="$1/SET01"

mv "$ROOT_PATH"/CVCDOL.S01P06/MUSESCORE/XAC_\ ACUR_TagFAu128_005.01.mscz "$ROOT_PATH"/CVCDOL.S01P06/MUSESCORE/XAC_ACUR_TagFAu128_005.01.mscz

mv "$ROOT_PATH"/CVCDOL.S01P03/MUSESCORE/XAC_ACUR_TagFAu128_010.mscz "$ROOT_PATH"/CVCDOL.S01P03/MUSESCORE/XAC_ACUR_TagFAu128_010.01.mscz
mv "$ROOT_PATH"/CVCDOL.S01P03/MUSESCORE/XAC_ACUR_TagFAu128_026.mscz "$ROOT_PATH"/CVCDOL.S01P03/MUSESCORE/XAC_ACUR_TagFAu128_026.01.mscz
mv "$ROOT_PATH"/CVCDOL.S01P03/MUSESCORE/XAC_ACUR_TagFAu128_002.mscz "$ROOT_PATH"/CVCDOL.S01P03/MUSESCORE/XAC_ACUR_TagFAu128_002.01.mscz
mv "$ROOT_PATH"/CVCDOL.S01P03/MUSESCORE/XAC_ACUR_TagFAu128_018.mscz "$ROOT_PATH"/CVCDOL.S01P03/MUSESCORE/XAC_ACUR_TagFAu128_018.01.mscz

mv "$ROOT_PATH"/CVCDOL.S01P06/MUSESCORE/XAC_ACUR_TagFAu128_013.001.mscz "$ROOT_PATH"/CVCDOL.S01P06/MUSESCORE/XAC_ACUR_TagFAu128_013.01.mscz
mv "$ROOT_PATH"/CVCDOL.S01P07/MUSESCORE/XAC_ACUR_TagFAu128_063.010.mscz "$ROOT_PATH"/CVCDOL.S01P07/MUSESCORE/XAC_ACUR_TagFAu128_063.10.mscz

rm "$ROOT_PATH"/CVCDOL.S01P06/XAC_ACUR_TagFAu128_029\ CASELLES1i2.png
rm "$ROOT_PATH"/CVCDOL.S01P06/XAC_ACUR_TagFAu129_038_TREMOLO.png

# Ensure everything went well

python3 ../validation_tools/validate.py "$ROOT_PATH"