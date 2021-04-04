# -*- coding: utf-8 -*-
"""
Created on Sat Mar 13 15:47:39 2021

@author: jegasus
"""

import warnings
import argparse
import os
import sys

# Path to the folder that contains the jegasus_world_manager.py file
#world_ref_tool_location = r'D:\Dropbox\Foundry\dev_data_github\world-manager'
world_manager_location = __file__
sys.path.append(world_manager_location)

# Importing the tool
import jegasus_world_manager as jwm 

# Getting username for default folder path
username = os.getlogin()

# Setting the default folder paths
if sys.platform[:3].lower() == 'win':
    default_user_data_folder = f'C:/Users/{username}/AppData/Local/FoundryVTT/Data'
    default_core_data_folder = 'C:/Program Files/FoundryVTT/resources/app/public'
    default_ffmpeg_location  = 'C:/Program Files/ffmpeg/ffmpeg.exe'
elif sys.platform.lower() == 'linux':
    default_user_data_folder = f'/home/{username}/foundrydata/Data'
    default_core_data_folder = f'/home/{username}/foundryvtt/resources/app/public'
    default_ffmpeg_location  = '/usr/bin/ffmpeg'

# Command used to supress multiple warnings about trying to parse regular 
# strings as HTML chunks. 
warnings.filterwarnings('ignore')

# Setting up the argparse variables.
# These commands/statements are needed to run the tool from the command line.
parser = argparse.ArgumentParser(description="Jegasus' World Manager - Tool that can be used to compress FoundryVTT worlds.")
parser.add_argument('-u','--user-data-folder', type=str, metavar='', 
                    help=f'Foundry User Data folder. Ex: "{default_user_data_folder}"',
                    default=default_user_data_folder)
parser.add_argument('-w','--world-folder', type=str, metavar='', 
                    help=r'Foundry World folder. Ex: "worlds\kobold-cauldron", "worlds\porvenir"',
                    default="")
parser.add_argument('-c','--core-data-folder', type=str, metavar='', 
                    help=f'Foundry Core folder. Ex: "{default_core_data_folder}"',
                    default=default_core_data_folder)
parser.add_argument('-f','--ffmpeg-location', type=str, metavar='', 
                    help=f'Location of the FFMPEG application/executable. Ex: "{default_ffmpeg_location}"',
                    default=default_ffmpeg_location)
parser.add_argument('-d','--delete-unreferenced-images', type=str, metavar='', 
                    help=r'Flag that determines whether or not to delete unreferenced images. Should be "y" or "n".', 
                    default='n')
args = parser.parse_args()

# Main function - this function is run automatically when this script is run.
if __name__ == '__main__':
    # Running the tool to compress the world
    my_world_refs = jwm.one_liner_compress_world(
            user_data_folder=args.user_data_folder,
            world_folder=args.world_folder,
            core_data_folder=args.core_data_folder,
            ffmpeg_location=args.ffmpeg_location, 
            delete_unreferenced_images=args.delete_unreferenced_images)

