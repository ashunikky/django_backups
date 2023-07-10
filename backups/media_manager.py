import os
import shutil
from zipfile import ZipFile
from django.conf import settings


def compress_media_file():
    # Get the file name and extension
    parent_dir= os.path.join(settings.MEDIA_ROOT,'backups')
    new_path=os.path.join(settings.MEDIA_ROOT,'media_backup')

    if os.path.exists(new_path):
        print("File already exists!! plz 'rename' or 'delete' the existing one first")
    else:
        shutil.make_archive(new_path, 'zip', parent_dir)
        
        # shutil.rmtree(parent_dir)
        basename2=os.path.basename(new_path)
        dir_name= ".zip"
        new_dir_name2= basename2+dir_name
        new_path2 = os.path.join(new_path, new_dir_name2)
        if os.path.exists(new_path2):
            print("ZIP folder created")
        else:
            print("ZIP folder not created")
        
    return relative_file_path(new_path2)

def relative_file_path(new_path2):
    
    relative_path = os.path.basename(new_path2)
    return relative_path
  
def restore_media_file():
    parent_dir= os.path.join(settings.MEDIA_ROOT,'media_backup.zip')
    print(parent_dir)
    if os.path.exists(parent_dir):
            with ZipFile(parent_dir, 'r') as zObject:
                dir_name= os.path.dirname(parent_dir)
                new_path = os.path.join(dir_name,'restored_media')
                zObject.extractall(new_path)
                # os.remove(parent_dir)
                print("file uncompressed successfully ")
                return new_path
    else:
            print("please give path to ZIP file")