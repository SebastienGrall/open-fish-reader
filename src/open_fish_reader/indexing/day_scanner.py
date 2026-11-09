from datetime import datetime
from pathlib import Path
from ..core.constants import VIDEO_FOLDER_NAME
from ..core.exceptions import InvalidStationFolderError
def find_day_folders(folder:Path)->list[Path]:
    if not folder.is_dir(): raise InvalidStationFolderError(f'Dossier introuvable : {folder}')
    result=[]
    for child in folder.iterdir():
        if not child.is_dir(): continue
        try: datetime.strptime(child.name,'%Y-%m-%d')
        except ValueError: continue
        if (child/VIDEO_FOLDER_NAME).is_dir(): result.append(child)
    return sorted(result,key=lambda p:p.name)
def find_video_part_json_files(day:Path)->list[Path]:
    videos=day/VIDEO_FOLDER_NAME
    return sorted(videos.glob('*.json')) if videos.is_dir() else []
