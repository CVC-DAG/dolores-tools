#!/bin/bash

ROOT_PATH="$1/SET03"

mv "$ROOT_PATH"/CVCDOL.S03.P01/MUSESCORE/XAC_ACAN_SMIAU83_002.01.mscz  "$ROOT_PATH"/CVCDOL.S03.P01/MUSESCORE/XAC_ACAN_SMIAu83_002.01.mscz

mv "$ROOT_PATH"/CVCDOL.S03.P07/MUSESCORE/XAC_ACAN_SMIAu83_063.011.mscz "$ROOT_PATH"/CVCDOL.S03.P07/MUSESCORE/XAC_ACAN_SMIAu83_063.11.mscz
mv "$ROOT_PATH"/CVCDOL.S03.P07/MUSESCORE/XAC_ACAN_SMIAu83_063.010.mscz "$ROOT_PATH"/CVCDOL.S03.P07/MUSESCORE/XAC_ACAN_SMIAu83_063.10.mscz
mv "$ROOT_PATH"/CVCDOL.S03.P07/MUSESCORE/XAC_ACAN_SMIAu83_063.014.mscz "$ROOT_PATH"/CVCDOL.S03.P07/MUSESCORE/XAC_ACAN_SMIAu83_063.14.mscz
mv "$ROOT_PATH"/CVCDOL.S03.P07/MUSESCORE/XAC_ACAN_SMIAu83_063.013.mscz "$ROOT_PATH"/CVCDOL.S03.P07/MUSESCORE/XAC_ACAN_SMIAu83_063.13.mscz
mv "$ROOT_PATH"/CVCDOL.S03.P07/MUSESCORE/XAC_ACAN_SMIAu83_063.012.mscz "$ROOT_PATH"/CVCDOL.S03.P07/MUSESCORE/XAC_ACAN_SMIAu83_063.12.mscz

rm "$ROOT_PATH"/CVCDOL.S03.P04/QUADRADES-TREMOLO.png 

# Ensure everything went well
python3 ../validation_tools/validate.py "$ROOT_PATH"