![GitHub All Releases](https://img.shields.io/github/downloads/jegasus/world-manager/total?label=Downloads+total)  

# Jegasus' World Manager
A Python-based tool that helps manage [FoundryVTT](https://foundryvtt.com/) Worlds. 
The main functionality implemented thus far is to compress all of a World's PNG and 
JPEG images to WEBP. The tool also helps with deduplication of image files.

# Warning

This tool edits, moves and deletes files on your disk, especially inside the 
Foundry World folder!!! 

So **PLEASE** make backups of your World folder **BEFORE** using this tool!

**DID YOU NOT HEAR ME??? GO BACK UP YOUR FILES RIGHT NOW!!!!**

Seriously, I cannot guarantee the integrity of the Worlds you edit using this 
tool. Back up your World before doing anything with this tool.

# Pre-requisites
## Python 3

You need to have Python 3 installed. This tool was built and tested using Python 
3.7, so preferrably use a version that is equal to or higher than that.

## Python libraries
Furthermore, you will also need to install the `beautifulsoup4` Python library. 
I strongly recommend installing [Anaconda](https://www.anaconda.com/products/individual) 
or [Miniconda](https://docs.conda.io/en/latest/miniconda.html). They will make 
installing & updating Python libraries much easier. Once either version of conda 
is installed, you can install `beautifulsoup4` by opening up your terminal and 
typing the following:

```
> conda install beautifulsoup4
```

## FFMPEG
Lastly, you will also need to have access to [FFMPEG](https://www.ffmpeg.org/download.html). 
I personally use the version recommended by Audacity, which can be downloaded 
[here](https://lame.buanzo.org/#lamewindl). 

# Compatibility

## Operating Systems
Currently, the tool only works on Windows. Compatibility for Linux and Mac users 
is one of the top items on the roadmap.

## Foundry
The tool has only been tested on Worlds built for Foundry 0.7.9. If you have 
Worlds built for any other version, please use the tool at your own risk.

# Instructions
Regardless of how you use this tool, the first step is to download it from 
Github and extract it to an empty folder.

## Using the tool from the command prompt
If you just want to compress your world's PNGs and JPEGs to WEBP, you can simply 
pass the main arguments to the program via command line. Here is a full example 
of how to do so. First, boot up your command prompt. Then, navigate to the folder 
where you extracted the tool by typing the following:
```
> cd /d "C:\path\to\the\tool"
```
Finally, type the following (making the appropriate substitutions, of course):
```
> python jwm_cli.py -u "C:\Users\jegasus\AppData\Local\FoundryVTT\Data" -w "worlds/porvenir" -c "C:\Program Files\FoundryVTT\resources\app\public" -f "C:\Program Files (x86)\Audacity\libraries\ffmpeg.exe" -d y
```
The main flags above are explained below:

- `-u` or `--user-data-folder`: Foundry User Data folder. Ex: "C:\Users\jegasus\AppData\Local\FoundryVTT\Data"
- `-w` or `--world-folder`: Foundry World folder. Ex: "worlds\kobold-cauldron", "worlds\porvenir"
- `-c` or `--core-data-folder`: Foundry Core folder. Ex: "C:\Program Files\FoundryVTT\resources\app\public"
- `-f` or `--ffmpeg-location`: Location of the FFMPEG application/executable. Ex: "C:\Program Files (x86)\Audacity\libraries\ffmpeg.exe
- `-d` or `--delete-unreferenced-images`: Flag that determines whether or not to delete unreferenced images. Should be "y" or "n".

When making the appropriate substitutions, make sure you point to the correct 
files and folders on your disk.

## Using this tool inside an interactive Python session
If you prefer, you can use this tool interactively to gain access to the tool's
internal functions and have more control over what the tool actually does. To do 
so, initiate a Python session and paste the following chunk of code (making the 
appropriate substitutions, of course):

```python
import sys

# Path to the folder that contains the jegasus_world_manager.py file
world_manager_location = "C:/path/to/folder/with/tool"
sys.path.append(world_manager_location)

# Importing the tool
import jegasus_world_manager as jwm 

# Defining the main file & folder paths 
user_data_folder = r'C:\Users\jegasus\AppData\Local\FoundryVTT\Data'
world_folder = r'worlds\porvenir'
core_data_folder = r'C:\Program Files\FoundryVTT\resources\app\public'
ffmpeg_location = r'C:\Program Files (x86)\Audacity\libraries\ffmpeg.exe'
delete_unreferenced_images = 'n'

# Running the tool to compress the world
my_world_refs = jwm.one_liner_compress_world(
  user_data_folder=user_data_folder,
  world_folder=world_folder,
  core_data_folder=core_data_folder,
  ffmpeg_location=ffmpeg_location, 
  delete_unreferenced_images=delete_unreferenced_images)

```
For an explanation of what the main arguments above represent, just look at the previous section.

## Using the tool beyond just compressing a Foundry World

TODO!!!!

# Changelog

## 0.0.1 - Released on 2021-04-03
Initial release! Hooray!!!!  

# Next steps / To-do list
- I need to ensure the process is cross-platform friendly. 
Currently, only windows is supported.
  - I need to generalize the call to FFMPEG subprocess so that the tool can be used
   on Windows, Mac and Linux. 
   Look into [this question/answer](https://stackoverflow.com/questions/377017/test-if-executable-exists-in-python) and 
   [this link](https://gist.github.com/techtonik/4368898) for more info.
- Change how db and json files are stored in the `world_ref` object. 
Currently, they are stored as separate attributes: `world_refs.json_files`
 and `world_refs.db_files`. They should both be in one single attribute 
 named "refs", which will be a dictionary with two keys: "db" and "json". 
- The `try_to_fix_all_broken_refs` method probably should be indexed by file
 path of the image being referenced. Right now, the function just looks at all
  of the `img_ref`s indiscriminately. Instead, I should create an index based
   on the file path and only check each unique file referenced once. 
- The `update_one_ref_to_webp` method should probably be owned by the `img_ref`
 class instead of the `world_refs` class.
- I need to look at these sites for better filetype investigation (to check 
file extension vs encoding):
  - https://github.com/lektor/lektor/issues/653
  - https://pypi.org/project/filetype/
  - https://pypi.org/project/puremagic/
- Convert all `os.path.join` statements to use the newer `Pathlib` library. 

