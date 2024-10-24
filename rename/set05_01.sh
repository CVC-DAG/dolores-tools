#!/bin/bash

ROOT_PATH="$1/SET05-12/CVC.01"

mv "$ROOT_PATH"/CVC.S06.P06/MUSESCORE/XAC_aCGAX_SEOAu458.13_025.01.mscz  "$ROOT_PATH"/CVC.S06.P06/MUSESCORE/XAC_ACGAX_SEOAu458.13_025.01.mscz   
mv "$ROOT_PATH"/CVC.S05.P01/MUSESCORE/XAC_ACGAX_SEOAU458.09_004.02.mscz  "$ROOT_PATH"/CVC.S05.P01/MUSESCORE/XAC_ACGAX_SEOAu458.09_004.02.mscz        
mv "$ROOT_PATH"/CVC.S05.P01/MUSESCORE/XAC_ACGAX_SEOAU458.09_004.04.mscz  "$ROOT_PATH"/CVC.S05.P01/MUSESCORE/XAC_ACGAX_SEOAu458.09_004.04.mscz        
mv "$ROOT_PATH"/CVC.S06.P06/MUSESCORE/XAC_ACUR_TagFau127_015.06.mscz     "$ROOT_PATH"/CVC.S06.P06/MUSESCORE/XAC_ACUR_TagFAu127_015.06.mscz   
mv "$ROOT_PATH"/CVC.S06.P06/MUSESCORE/XAC_ACUR_TAgFAu127_015.02.mscz     "$ROOT_PATH"/CVC.S06.P06/MUSESCORE/XAC_ACUR_TagFAu127_015.02.mscz   
mv "$ROOT_PATH"/CVC.S06.P06/MUSESCORE/XAC_ACUR_TAgFAu127_005.02.mscz     "$ROOT_PATH"/CVC.S06.P06/MUSESCORE/XAC_ACUR_TagFAu127_005.02.mscz     
mv "$ROOT_PATH"/CVC.S08.P03/MUSESCORE/UAB_LICEU_191815.012.03.mscz       "$ROOT_PATH"/CVC.S08.P03/MUSESCORE/UAB_LICEU_191851.012.03.mscz   
mv "$ROOT_PATH"/CVC.S08.P03/MUSESCORE/UAB_LICEU_191815.012.01.mscz       "$ROOT_PATH"/CVC.S08.P03/MUSESCORE/UAB_LICEU_191851.012.01.mscz   
mv "$ROOT_PATH"/CVC.S08.P03/MUSESCORE/UAB_LICEU_191815.012.02.mscz       "$ROOT_PATH"/CVC.S08.P03/MUSESCORE/UAB_LICEU_191851.012.02.mscz   
mv "$ROOT_PATH"/CVC.S08.P03/MUSESCORE/UAB_LICEU_191815.012.04.mscz       "$ROOT_PATH"/CVC.S08.P03/MUSESCORE/UAB_LICEU_191851.012.04.mscz   

# Ensure everything went well
python3 ../validation_tools/validate.py "$ROOT_PATH"