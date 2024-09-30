import dicom2nifti
import os
import subprocess
import numpy as np
from shutil import copyfile
from glob import glob
from pathlib import Path
from medpy.io import load, save

def dicom_to_nifti(TCGA_dcm_path, patients, p):
    if p in patients:
        for path in sorted(glob(os.path.join(TCGA_dcm_path, p)+"/*/*")):
            output_path = path.replace("TCGA-GBM", "TCGA-GBM[nii]")
            output_path = output_path.replace(" ", "_")
            if not os.path.exists(output_path):
                os.makedirs(output_path)
            try:
                print('converting dicoms to nifti : {}'.format(path))
                dicom2nifti.convert_directory(path, output_path)
            except exception as e:
                print('***error {} with file {}***'.format(e, path))
                pass
            
def bet(TCGA_nii_path, patients, p):
    if p in patients:
        for root, dirs, files in os.walk(os.path.join(TCGA_nii_path, p)):    
            for file in files:
                if file.endswith(".nii.gz"):
                    nii_input_path = os.path.join(root, file)
                    if "T1" in nii_input_path: # process only "T1" MRI images [modify according to need]
                        nii_output_path = nii_input_path.replace("TCGA-GBM[nii]", "TCGA-GBM[brain]")
                        nii_output_path = Path(nii_output_path.replace(".nii.gz", "_brain")).absolute()
                        if not os.path.exists(nii_output_path.parent):
                            os.makedirs(nii_output_path.parent)
                        try:
                            print('applying bet on {}'.format(nii_input_path))
                            subprocess.check_output(["/usr/local/fsl/bin/bet", nii_input_path, nii_output_path], 
                                                    env={'FSLDIR': "/usr/local/fsl", 'FSLOUTPUTTYPE': "NIFTI_GZ"}, stderr=subprocess.STDOUT)
                        except Exception as e:
                            print(e)
                            pass

def axes_correction(TCGA_brain_path, patients, p):
    if p in patients:
        for root, dirs, files in os.walk(os.path.join(TCGA_brain_path, p)):    
            for file in files:
                if file.endswith(".nii.gz"):
                    nii_input_path = os.path.join(root, file)
                    image_data, _ = load(nii_input_path)
                    nii_output_path = Path(nii_input_path.replace("brain", "brain_axes-corrected"))
                    if not os.path.exists(nii_output_path.parent):
                        os.makedirs(nii_output_path.parent)
                    try:
                        print('correcting axes : {}'.format(nii_input_path))
                        if min(image_data.shape) != image_data.shape[2]:
                            min_index = image_data.shape.index(min(image_data.shape))
                            image_data = np.swapaxes(image_data, min_index, 2)
                            save(image_data, str(nii_output_path))
                        else:
                            copyfile(nii_input_path, nii_output_path)
                    except Exception as e:
                        print('***error {} with file {}***'.format(e, nii_output_path))

def nifti_to_png(TCGA_brain_path, patients, p):
    if p in patients:
        for root, dirs, files in os.walk(os.path.join(p, TCGA_brain_path)):    
            for file in files:
                if file.endswith(".nii.gz"):
                    nii_input_path = os.path.join(root, file)
                    nii_output_file = Path(nii_input_path.replace("brain_axes-corrected", "axes-corrected_PNG"))
                    filename = nii_output_file.stem[:(nii_output_file.stem).rfind("_")] + ".png"
                    try:
                        print('converting nifti to png : {}'.format(nii_input_path))
                        os.makedirs(nii_output_file.parent, exist_ok=True)
                        subprocess.check_output(['med2image', '-i', nii_input_path, '-d', str(nii_output_file.parent), '-o', filename], stderr=subprocess.STDOUT)
                    except Exception as e:
                        print(e)
                        pass