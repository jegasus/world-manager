# -*- coding: utf-8 -*-
"""
Created on Sat Mar 13 14:23:05 2021

@author: jegasus

"""

import os
import json
import re
import pathlib
import subprocess
import shlex
import warnings
import hashlib
import shutil
import imghdr
import argparse
import mimetypes
import hashlib

from bs4 import BeautifulSoup

# Command used to supress multiple warnings about trying to parse regular
# strings as HTML chunks.
warnings.filterwarnings('ignore')

def dict_walker(in_dict, pre=None):
    '''
    Function that walks through an indefinitely complex dictionary (can contain
    lists, tuples or other dictionaries), and iterates through all of the
    dictionary's "leaves". This works as an iterator that returns a big list
    that contains the full "address" of a leaf.

    Modified from https://stackoverflow.com/a/12507546/8667016

    INPUTS:
    -------
    in_dict (DICT) : A dictionary of arbitrary depth/complexity.

    RETURNS:
    --------
    iterated_output (LIST) : A list that contains the full address of the leaf
        in the dictionary.

    EXAMPLE:
    --------
    # Input:
    my_dict = {'part_1':[5,6,7],
               'part_2':[3,6,{'a':999,
                              'b':777,
                              'c':123}]}

    for this_full_address in dict_walker(in_dict=my_dict):
        print(this_full_address)

    # Output:
    # ['part_1', 0, 5]
    # ['part_1', 1, 6]
    # ['part_1', 2, 7]
    # ['part_2', 0, 3]
    # ['part_2', 1, 6]
    # ['part_2', 2, 'a', 999]
    # ['part_2', 2, 'b', 777]
    # ['part_2', 2, 'c', 123]
    '''

    pre = pre[:] if pre else []
    if isinstance(in_dict, dict):
        for key, value in in_dict.items():
            if isinstance(value, dict):
                for d in dict_walker(value, pre + [key]):
                    yield d
            elif isinstance(value, list) or isinstance(value, tuple):
                for i,v in enumerate(value):
                    for d in dict_walker(v, pre + [key,i]):
                        yield d
            else:
                yield pre + [key, value]
    else:
        yield pre + [in_dict]


def get_nested_dict_recursive(in_dict, dict_address):
    '''
    Function that allows you to access a specific "address" inside an
    arbitrarily-complex dictionary.

    INPUTS:
    -------
    in_dict (DICT) : Dictionary to be read.
    dict_address (LIST) : Address of the object being requested.

    RETURNS:
    --------
    output (any) : The output of this function is the actual item at the
        "address" inside the input dictionary.


    EXAMPLE:
    --------
    # Input:
    my_dict = {'part_1':[5,6,7],
               'part_2':[3,6,{'a':999,
                              'b':777,
                              'c':123}]}

    address_1 = ['part_1', 2]
    address_2 = ['part_2', 2]

    print(get_nested_dict_recursive(in_dict=my_dict, dict_address=address_1))
    print(get_nested_dict_recursive(in_dict=my_dict, dict_address=address_2))

    # Output:
    # 7
    # {'a': 999, 'b': 777, 'c': 123}
    '''
    if len(dict_address) == 1:
        return in_dict[dict_address[0]]
    else:
        return get_nested_dict_recursive(in_dict[dict_address[0]], dict_address[1:])

def edit_nested_dict_recursive(in_dict, dict_address, new_value):
    '''
    Function that allows you to edit a specific "address" inside an
    arbitrarily-complex dictionary and assign a new value/object to it.

    INPUTS:
    -------
    in_dict (DICT) : Dictionary to be read.
    dict_address (LIST) : Address of the object that will receive `new_value`.
    new_value (any) : New value to be stored in the input dictionary's "address".

    RETURNS:
    --------
    None

    EXAMPLE:
    --------
    # Input:
    my_dict = {'part_1':[5,6,7],
               'part_2':[3,6,{'a':999,
                              'b':777,
                              'c':123}]}

    my_address = ['part_1', 2]
    my_new_value = 'DOG'

    edit_nested_dict_recursive(my_dict, my_address, my_new_value)

    print(my_dict)

    # Output:
    # {'part_1': [5, 6, 'DOG'],
    #  'part_2': [3, 6, {'a': 999,
    #                    'b': 777,
    #                    'c': 123}]}
    '''
    if len(dict_address) == 1:
        in_dict[dict_address[0]] = new_value
    else:
        edit_nested_dict_recursive(in_dict[dict_address[0]], dict_address[1:],new_value)

class img_ref:
    '''
    Class that encapsules one single image reference inside the Foundry world.
    This class contains several helpful methods and attributes that make it easy
    to understand the image reference.
    Mainly, the `img_ref` object contains information about where this image
    reference is located in the world.
    For example, if there is a journal entry that makes a reference to
    "worlds/porvenir/handouts/ScytheOfTheHeadlessHorseman.webp", an `img_ref`
    instance can be created to indicate exactly where in the world folder this
    reference can be found: inside the 4th line of the "worlds/myworld/data/journal.db"
    file, at the following "address": ['img', 'worlds/porvenir/handouts/ScytheOfTheHeadlessHorseman.webp'].
    Among many other things, this object also includes an attribute that indicates
    the image's filetype/extension (JPG, PNG, WEBP), and an attribute that helps
    determine whether the image was actually encoded using its filename's
    extension's protocols.

    Main attributes:
        Attributes that never change:
        -----------------------------
        self.world_folder (STR) : Folder path of the current world
        self.core_data_folder (STR) : Folder path of the Foundry installation
        self.ref_file_path (STR) : Indicates the filepath to the file that contains
            this image reference. For example, if an image reference is made
            inside the world's "journal.db" file, the `ref_file_path` would be
            something like "worlds/myworld/data/journal.db"
        self.ref_file_type (STR) : Type of file in which this reference was found.
            Can be either "json" or "db".
        self.ref_file_line (INT or None): For '.db' reference files, there are multiple
            JSON-like dictionaries per row. The `ref_file_line` argument indicates
            which line in the ".db" file this particular `img_ref` can be found.
            For example, if the reference to the image is on the 5th line of the
            "journal.db" file, then `ref_file_line` will equal 4. In cases where
            the reference was found in a ".json" file, this attribute is instead
            set to None.
            NOTE: As with everything else in Python, this line number is zero-indexed.
        self.json_address (LIST) : Full "address" of the reference inside the "db"
            or "json" file.
        self.world_references_owner_obj (world_refs) : Object that "owns"
            this reference. This is a collection of `img_ref`s.
        self.img_ref_content_is_html (BOOL) : Indicates whether this reference is
            just a simple STRING or if it's an HTML chunk.

        Attributes that are mutable:
        ----------------------------
        self.ref_img_in_world_folder (BOOL) : Indicates whether or not this
            reference tries to point to an image file on disk that is inside
            the world folder.
        self.img_path_on_disk (STR) : File path on disk to which this reference
            points. The difference between this and the `ref_file_path` attribute
            is that if the image being referenced is inside the Foundry Core folder,
            the `img_path_on_disk` attribute will have the full absolute path to
            the image on disk. The `ref_file_path` attibute, however, will only have
            the "stem" of the path (i.e., the image path relative to the Foundry
            Core folder).
            Furthermore, in cases where the image does not exist on disk, the
            `the img_path_on_disk` attribute is set to an error value.
        self.img_exists (BOOL) : Indicates whether or not this file actually exists
            on disk
        self.img_encoding (STR) : Type of encoding used for the image. Expected
            values can be "png", "jpeg" or "webp".
        self.correct_extension (BOOL) : Indicates whether or not the encoding
            actually matches the file extension. For example, if a file is named
            "my_img.jpeg", but it was encoded using "png", the `correct_extension`
            attribute will be False.
        self.img_hash (STR) : Hash of the image file on disk. Used for de-duplication.
        self.is_webp (BOOL) : Indicates whether or not the file extension is ".webp"
        self.webp_img_path_for_ref (STR) : File path for the ".webp" version of
            this image (regardless of whether or not the ".webp" version exists).
        self.webp_copy_exists (BOOL) : Indicates whether or not the ".webp" version
            of this image exists on disk
        self.img_ref_external_web_link (BOOL) : Indicates whether or not this
            image reference is actually a hyperlink to an external file on
            the web.
        self.trash_folder_location (STR) : Indicates the folder location of where
            this file needs to go if it needs to be moved to the trash

    '''

    def __init__(self, ref_file_type=None, ref_file_path=None, ref_file_line=None,
                 full_json_address=None, img_path_for_ref=None,
                 world_refs_obj=None):
        '''
        Function used to instantiate new objects from the `img_ref` class.

        INPUTS:
        -------
        ref_file_type (STR) Indicates the file type of the location where this
            image reference is stored. Can only take two values: 'json' or 'db'.
        ref_file_path (STR) : Indicates the filepath to the file that contains
            this image reference. For example, if an image reference is made
            inside the world's "journal.db" file, the `ref_file_path` would be
            something like "worlds/myworld/data/journal.db"
        ref_file_line (INT or None): For '.db' reference files, there are multiple
            JSON-like dictionaries per row. The `ref_file_line` argument indicates
            which line in the ".db" file this particular `img_ref` can be found.
            For example, if the reference to the image is on the 5th line of the
            "journal.db" file, then `ref_file_line` will equal 4. In cases where
            the reference was found in a ".json" file, this attribute is instead
            set to None.
            NOTE: As with everything else in Python, this line number is zero-indexed.
        full_json_address (LIST) : Full "address" of an image's reference inside
            the complex JSON dictionary.
        img_path_for_ref (STR) : Actual disk location/filepath of the image being
            referenced. Ex: "worlds/porvenir/handouts/ScytheOfTheHeadlessHorseman.webp"
        world_refs_obj (OBJECT) : This is an instance of the `world_refs` object
            (defined below). The `world_refs_obj` attribute points to the `world_refs`
            object to which this `img_ref` belongs, and inside of which all other
            image references can be found.
        ref_id (STR) : Unique string that can be used to identify each individual
            `img_ref` object

        RETURNS:
        --------
        img_ref (OBJECT) : The newly created `img_ref` object itself.

        EXAMPLE:
        --------
        # Input:
        my_ref = img_ref(ref_file_type='db',
                         ref_file_path='worlds/myworld/data/journal.db',
                         ref_file_line=4,
                         full_json_address=['img', 'worlds/porvenir/handouts/ScytheOfTheHeadlessHorseman.webp'],
                         img_path_for_ref='worlds/porvenir/handouts/ScytheOfTheHeadlessHorseman.webp',
                         world_refs_obj=my_world_refs)

        # Output:
        # None
        '''

        # Setting attributes that will never be updated
        self.world_folder = world_refs_obj.world_folder
        self.core_data_folder = world_refs_obj.core_data_folder
        self.ref_file_path = ref_file_path
        self.ref_file_type = ref_file_type
        self.ref_file_line = ref_file_line
        self.json_address  = full_json_address[:-1]
        self.world_references_owner_obj = world_refs_obj

        # Setting the unique ID for this `ref_img`
        string_to_hash = (self.world_folder + self.core_data_folder + self.ref_file_path +
                          self.ref_file_type + str(self.ref_file_line) + str(self.json_address)
                          + 'img_ref')

        self.ref_id = hashlib.sha256(string_to_hash.encode()).hexdigest()

        # Looks into the actual content of the reference. Sometimes it is just
        # a string with the filepath to the image. Other times it is a chunk of
        # HTML that links to an embedded image. In any case, this content needs
        # to be investigated to generate a bunch of the `img_ref`'s attributes.
        img_ref_content = full_json_address[-1]

        # Checking if the content of the reference is an HTML chunk.
        self.img_ref_content_is_html = True if BeautifulSoup(img_ref_content, 'html.parser').find() else False

        # Setting the attributes that might be edited later.
        self.set_editable_attributes(img_path_for_ref)

    def get_img_ref_content(self):
        '''
        Retrieves this `img_ref`'s content from the main world reference object

        INPUTS:
        -------
        None

        RETURNS:
        --------
        img_ref_content (STR) : The actual content of the reference. Sometimes
            it is just a string with the filepath to the image. Other times it
            is a chunk of HTML that links to an embedded image.

        EXAMPLE:
        --------
        # Input:
        print(my_ref.get_img_ref_content())

        # Output:
        # 'worlds/porvenir/handouts/ScytheOfTheHeadlessHorseman.webp'
        '''



        if self.ref_file_type == "db":
            this_ref_file_dict = self.world_references_owner_obj.db_files[self.ref_file_path][self.ref_file_line]
        elif self.ref_file_type == "json":
            this_ref_file_dict = self.world_references_owner_obj.json_files[self.ref_file_path]

        this_address = self.json_address

        img_ref_content = get_nested_dict_recursive(this_ref_file_dict,this_address)

        return img_ref_content


    def set_editable_attributes(self, img_path_for_ref=None):
        '''
        This is where several of the `img_ref`'s helper attributes get initially
        set, such as the attribute that determines whether the image was actually
        encoded using its filename's extension's protocols.

        INPUTS:
        -------
        img_path_for_ref (STR) : Actual disk location/filepath of the image
            being referenced. Ex: "worlds/porvenir/handouts/ScytheOfTheHeadlessHorseman.webp"

        RETURNS:
        --------
        None

        EXAMPLE:
        --------
        # Input:
        my_img_path_for_ref = my_ref.full_json_address[:-1]

        my_img_ref.set_editable_attributes(my_img_path_for_ref)

        '''

        self.img_path_for_ref = img_path_for_ref

        self.ref_img_in_world_folder = True if img_path_for_ref[:len(self.world_folder)] == self.world_folder else False

        if os.path.isfile(self.img_path_for_ref):
            self.img_path_on_disk = self.img_path_for_ref
            self.img_exists = True
        elif os.path.isfile(os.path.join(self.core_data_folder,self.img_path_for_ref)):
            self.img_path_on_disk = os.path.join(self.core_data_folder,self.img_path_for_ref).replace('\\','/')
            self.img_exists = True
        else:
            self.img_path_on_disk = 'ERROR!!! IMG REFERENCE NOT ON DISK!!!'
            self.img_exists = False
            self.img_encoding = None

        if self.img_exists:
            img_encoding_imghdr = imghdr.what(self.img_path_on_disk)

            img_encoding_mime_temp = mimetypes.guess_type(self.img_path_on_disk)[0]
            img_encoding_mime      = img_encoding_mime_temp.split('/')[1].lower() if img_encoding_mime_temp != None else None

            if img_encoding_imghdr:
                self.img_encoding = img_encoding_imghdr
            elif img_encoding_mime:
                self.img_encoding = img_encoding_mime
            else:
                self.img_encoding = None

        if self.img_encoding:

            self.img_encoding = self.img_encoding.lower()
            if self.img_encoding == 'jpeg':
                if pathlib.Path(self.img_path_on_disk).suffix[1:].lower() == 'jpeg' or pathlib.Path(self.img_path_on_disk).suffix[1:].lower() == 'jpg':
                    self.correct_extension = True
                else:
                    self.correct_extension = False
            else:
                self.correct_extension = pathlib.Path(self.img_path_on_disk).suffix[1:].lower() == self.img_encoding.lower()
        else:
            self.correct_extension = None
        self.img_hash = hashlib.md5(open(self.img_path_on_disk,'rb').read()).hexdigest() if (self.img_exists and self.ref_img_in_world_folder) else None
        self.is_webp = pathlib.Path(self.img_path_for_ref).suffix.lower() == '.webp'
        self.webp_img_path_for_ref =  (os.path.join(pathlib.Path(self.img_path_for_ref).parent,pathlib.Path(self.img_path_for_ref).stem) + '.webp').replace('\\','/')
        self.webp_copy_exists = None if self.is_webp else os.path.isfile(self.webp_img_path_for_ref)
        self.img_ref_external_web_link = True if (self.img_path_for_ref.find('http:') >= 0 or self.img_path_for_ref.find('https:') >= 0) else False

        if os.path.isfile(self.img_path_for_ref) and self.ref_img_in_world_folder:
            trash_folder_location = re.split('\\\\|/',self.img_path_on_disk)
            trash_folder_location.insert(2,'_trash')
            trash_folder_location = str(os.path.join(*trash_folder_location).replace('\\','/'))
            self.trash_folder_location = trash_folder_location
        else:
            self.trash_folder_location = 'ERROR!!! IMG REFERENCE NOT ON DISK!!!'

    def print_ref(self):
        '''
        Prints the `img_ref`'s main data to the screen.
        The data that is printed out are:
            -The file path for the referenced image
            -The image's encoding protocol (png, jpeg, webp)
            -The reference file that contains this specific reference and the
                line of the reference file that contains this specific reference
                Note: The line is only necessary for DB files. For JSON files,
                a "-1" will be printed instead.
            -The full JSON address of the reference
            -The first 255 characters of the content of the reference.
        Note: the multiple parts are separated by a "pipe" ( the | character).


        INPUTS:
        -------
        None

        RETURNS:
        --------
        None

        EXAMPLE:
        --------
        # Input:
        my_ref.printref()

        # Output:
        # worlds/porvenir/art/porvenir-banner.webp | webp | worlds/porvenir/world.json -1 | ['description'] | <img title="The Secret of the Porvenir" src="worlds/porvenir/art/porvenir-banner.webp" />The Secret of the Porvenir is a spooktacular game-ready adventure for 5th Edition.<blockquote>The Porvenir - missing for weeks, feared lost - has mysteriously returne |
        '''

        print_str = f'{self.img_path_for_ref} | '
        print_str = print_str + f'{self.img_encoding if self.img_encoding else "404 IMG NOT FOUND"} | '
        print_str = print_str + f'{self.ref_file_path} {self.ref_file_line if self.ref_file_type == "db" else "-1"} | '
        print_str = print_str + f'{self.json_address} | '
        print_str = print_str + f'{self.get_img_ref_content()[:255]} | '
        print(print_str)

    def create_webp_copy(self):
        '''
        Creates a compressed ".webp" copy of the image being referenced in the
        `img_ref` object.

        INPUTS:
        -------
        None

        RETURNS:
        --------
        subprocess_output.returncode (INT) : Indicates whether or not the conversion
            process terminated successfully. This value takes 0 if the conversion
            was successful. All other values indicate some sort of problem.

        EXAMPLE:
        --------
        # Input:
        my_ref.create_webp_copy()

        # Output:
        # None
        '''
        # The actual string that needs to be sent to the command line
        cmd_call_str = f'"{self.world_references_owner_obj.ffmpeg_location}" -y -i "{self.img_path_for_ref}" -c:v libwebp "{self.webp_img_path_for_ref}" -hide_banner -loglevel error'

        # Running terminal command (https://stackoverflow.com/a/48857230/8667016)
        # The exit code here is 0 if the conversion succeeded. If it is anything
        # else, it means the conversion process failed.
        subprocess_output = subprocess.run(shlex.split(cmd_call_str))

        # Some files have the incorrect extention. For example, an image that
        # was compressed using a JPEG protocol but had a PNG extension.
        # To fix this, I need to check if FFMPEG's conversion succeeds or not.
        # When FFMPEG fails to convert, I need to try converting it using another
        # protocol (jpeg or png - the opposite of what was used in the first call)
        # Note: The section below is commented out because I created a method
        # that tries to fix the jpeg/png file extension beforehand. Therefore,
        # this part of the code should be unnecessary.
        '''
        if subprocess_output.returncode != 0:
            # Check the extension/suffix of the current file and generates a
            # temporary copy of the file with the "opposite" extension
            original_suffix = str(pathlib.Path(self.img_path_for_ref).suffix)
            if original_suffix == '.jpg' or original_suffix == '.jpeg':
                new_suffix = '.png'
            else:
                new_suffix = '.jpg'
            temp_img_path = os.path.join(pathlib.Path(self.img_path_for_ref).parent,pathlib.Path(self.img_path_for_ref).stem).replace('\\','/') + new_suffix
            shutil.copyfile(self.img_path_for_ref, temp_img_path)

            # Run the FFMPEG call using the new filename
            new_cmd_call_str = f'"{self.ffmpeg_location}" -y -i "{temp_img_path}" -c:v libwebp "{self.webp_img_path_for_ref}"'
            new_subprocess_output = subprocess.run(shlex.split(new_cmd_call_str))

            # Delete the temporary file created
            os.remove(temp_img_path)

            # Checking if the new conversion process was successful
            if new_subprocess_output.returncode == 0:
                subprocess_output = new_subprocess_output
        '''
        return subprocess_output.returncode


    def push_updated_content_to_world(self, updated_content):
        ''''
        Pushes content from the `updated_content` string back into the
        `world_refs` object.

        INPUTS:
        -------
        updated_content (STR) : Content that will be pushed back into the
            `world_refs` object.

        RETURNS:
        --------
        subprocess_output.returncode (INT) : Indicates whether or not the conversion
            process terminated successfully. This value takes 0 if the conversion
            was successful. All other values indicate some sort of problem.

        EXAMPLE:
        --------
        # Input:
        my_ref.push_updated_content_to_world(updated_content)

        # Output:
        # None
        '''

        if self.ref_file_type == 'json':
            edit_nested_dict_recursive(self.world_references_owner_obj.json_files[self.ref_file_path],
                                       self.json_address,
                                       updated_content)
        elif self.ref_file_type == 'db':
            edit_nested_dict_recursive(self.world_references_owner_obj.db_files[self.ref_file_path][self.ref_file_line],
                                       self.json_address,
                                       updated_content)



class world_refs:
    '''
    Container object that represents the Foundry World. This object contains
    several helper attributes and methods, such as a function that searches the
    world folder for all the image files, and an attribute that is a list of
    all the `img_ref`s inside the world.

    Main attributes:
        self.user_data_folder (STR) : String that describes the absolute path for
            the user data folder on disk. On Windows installations, this attribute
            should typically look something like this: "C:/Users/jegasus/AppData/Local/FoundryVTT/Data"
        self.world_folder (STR) : String that describes the relative path to the
            world folder to be scanned by the world reference tool. This path needs
            to be relative to the user data folder (i.e., the combination of the
            `user_data_folder` attribute and the `world_folder` represent the
            absolute path of the World folder to be scanned. This attribute should
            typically look like this: "worlds/porvenir", or "worlds/kobold-cauldron".
        self.core_data_folder (STR) : String that describes the absolute path to the
            Foundry Core Data folder. This attribute should typically look like
            this: "C:/Program Files/FoundryVTT/resources/app/public"
        self.ffmpeg_location (STR) : String that describes the absolute path to
            the ffmpeg executable. This attribute should typically look like this:
            "C:/Program Files (x86)/Audacity/libraries/ffmpeg.exe".
        self.trash_folder (STR): String that describes the relative path to the
            trash folder for this world. This path is relative to the path in the
            `user_data_folder` attribute. This attribute should typically look
            like this: "worlds/porvenir/_trash", or "worlds/kobold-cauldron_trash".
        self.trash_queue (SET) : Set of filenames that need to be moved to the
            trash folder.
        self.all_img_refs (LIST) : List of all the `img_ref` objects found in
            the world's JSON and DB files.
        self.all_img_refs_by_id (DICT) : Dictionary of all `img_ref` objects
            indexed by `ref_id`
        self.json_files (DICT) : Dictionary that holds the contents of all the
            JSON files inside the World folder. The structure of this dictionary
            is as follows:
                {'worlds/porvenir/world.json' : {json_dict_content},
                 'worlds/porvenir/descr.json' : {json_dict_content}}
        self.db_files (DICT) : Dictionary that holds the contents of all the
            DB files inside the World folder. The structure of this dictionary
            is as follows:
                {'worlds/porvenir/data/actors.db   : [{json_dict_content},
                                                      {json_dict_content},
                                                      {json_dict_content}],
                 'worlds/porvenir/data/folders.db' : [{json_dict_content},
                                                      {json_dict_content},
                                                      {json_dict_content}]
                 'worlds/porvenir/data/items.db'   : [{json_dict_content},
                                                      {json_dict_content},
                                                      {json_dict_content}] }

    '''

    def __init__(self,user_data_folder,world_folder,core_data_folder,ffmpeg_location):
        '''
        Function used to instantiate new objects from the `world_refs` class.

        INPUTS:
        -------
        user_data_folder (STR) : String that describes the absolute path for
            the user data folder on disk. On Windows installations, this attribute
            should typically look something like this: "C:/Users/jegasus/AppData/Local/FoundryVTT/Data"
        world_folder (STR) : String that describes the relative path to the
            world folder to be scanned by the world reference tool. This path needs
            to be relative to the user data folder (i.e., the combination of the
            `user_data_folder` attribute and the `world_folder` represent the
            absolute path of the World folder to be scanned. This attribute should
            typically look like this: "worlds/porvenir", or "worlds/kobold-cauldron".
        core_data_folder (STR) : String that describes the absolute path to the
            Foundry Core Data folder. This attribute should typically look like
            this: "C:/Program Files/FoundryVTT/resources/app/public"
        ffmpeg_location (STR) : String that describes the absolute path to
            the ffmpeg executable. This attribute should typically look like this:
            "C:/Program Files (x86)/Audacity/libraries/ffmpeg.exe".


        RETURNS:
        --------
        world_refs (OBJECT) : The newly created `world_refs` object itself.

        EXAMPLE:
        --------
        # Input:
        my_world_refs = world_refs(
                user_data_folder='C:/Users/jegasus/AppData/Local/FoundryVTT/Data',
                world_folder='worlds/porvenir',
                core_data_folder='C:/Program Files/FoundryVTT/resources/app/public',
                ffmpeg_location='C:/Program Files (x86)/Audacity/libraries/ffmpeg.exe')

        # Output:
        # None
        '''

        # Checking inputs
        checked_inputs = input_checker(user_data_folder,world_folder,
                                       core_data_folder,ffmpeg_location,'n')

        user_data_folder = checked_inputs['user_data_folder']
        world_folder = checked_inputs['world_folder']
        core_data_folder = checked_inputs['core_data_folder']
        ffmpeg_location = checked_inputs['ffmpeg_location']

        # Storing user, world and core folders and ffmeg location
        self.user_data_folder = user_data_folder.replace('\\','/')
        self.world_folder     = world_folder.replace('\\','/')
        self.core_data_folder = core_data_folder.replace('\\','/')
        self.ffmpeg_location  = ffmpeg_location.replace('\\','/')

        # Reading in the DB and JSON files inside the world
        self.load_db_and_json_files()

        # Making the trash folder. This is where all the images to be deleted
        # will go before they are actually deleted.
        trash_folder = str(os.path.join(world_folder,'_trash'))
        os.makedirs(trash_folder, exist_ok=True)
        self.trash_folder = trash_folder

        # Set of images that need to be moved to the trash
        self.trash_queue = set()

        # Finds all the `img_ref` objects inthe world
        self.find_all_img_references_in_world()

    def load_db_and_json_files(self):
        '''
        Function that scans the world folder and loads in the contents of the
        DB and JSON files. This function defines two important attributes from the
        `world_refs` object: self.json_files and self.db_files.

        Attributes set by this function:
            self.json_files (DICT) : Dictionary that holds the contents of all the
                JSON files inside the World folder. The structure of this dictionary
                is as follows:
                    {'worlds/porvenir/world.json' : {json_dict_content},
                     'worlds/porvenir/descr.json' : {json_dict_content}}
            self.db_files (DICT) : Dictionary that holds the contents of all the
                DB files inside the World folder. The structure of this dictionary
                is as follows:
                    {'worlds/porvenir/data/actors.db   : [{json_dict_content},
                                                          {json_dict_content},
                                                          {json_dict_content}],
                     'worlds/porvenir/data/folders.db' : [{json_dict_content},
                                                          {json_dict_content},
                                                          {json_dict_content}]
                     'worlds/porvenir/data/items.db'   : [{json_dict_content},
                                                          {json_dict_content},
                                                          {json_dict_content}] }

        INPUTS:
        -------
        None

        RETURNS:
        --------
        None

        '''
        world_folder = self.world_folder

        list_of_db_files   = [str(this_path).replace('\\','/') for this_path in pathlib.Path(world_folder).rglob('*.db')]
        list_of_json_files = [str(this_path).replace('\\','/') for this_path in pathlib.Path(world_folder).rglob('*.json')]


        self.db_files = {}
        for this_db_file  in list_of_db_files:

            # Need to avoid the `settings.db` file
            if this_db_file != str(pathlib.Path(os.path.join(world_folder,'data/settings.db'))).replace('\\','/'):
                pass
                this_db_file_lines = []
                # Reading the DB file
                with open(this_db_file,'r',encoding="utf-8") as fp:

                    # Initializing process to scan all lines in DB file
                    line_count = 0
                    line = fp.readline()

                    # Scanning all lines in DB file
                    while line:

                        # Transforming JSON-like string into a python dict
                        #line_dict = json.loads(line)
                        this_db_file_lines.append(json.loads(line))

                        # Preparing for next row
                        line_count += 1
                        line = fp.readline()

                # Adding this DB file's list of dictionaries into the main object
                self.db_files[this_db_file] = this_db_file_lines


        self.json_files = {}
        for this_json_file in list_of_json_files:
            with open(this_json_file,'r',encoding="utf-8") as fp:
                self.json_files[this_json_file] = json.load(fp)


    def find_all_img_references_in_world(self, return_result=False):
        '''
        Scans the DB and JSON files inside the world and creates `img_ref`
        objects for each and every reference to image files. All of the `img_ref`
        objects that are created in this process are appended to a list. This
        list of `img_ref`s is added as an attribute of the `world_refs` object.

        Attributes set by this function:
            self.all_img_refs (LIST) : List of all the `img_ref` objects found in
                the world's JSON and DB files.

        INPUTS:
        -------
        return_result (BOOL) : Indicates whether or not the function should return
            the `all_img_refs` list at the end of the process.

        RETURNS:
        --------
        all_img_refs (LIST) :  List of all the `img_ref` objects found in
            the world's JSON and DB files.

        '''
        # List of ALL images referenced in world
        self.all_img_refs = []

        self.all_img_refs_by_id = {}

        # Scanning all JSON files for references to images
        for this_json_file in self.json_files:
            this_json_file_content = self.json_files[this_json_file]
            self.traverse_dict_and_find_all_refs(dict_content=this_json_file_content,
                                                 ref_file_path=this_json_file,
                                                 json_or_db='json')

        # Scanning all DB files for references to images
        for this_db_file in self.db_files:
            for this_db_file_line,this_db_file_line_content in enumerate(self.db_files[this_db_file]):
                self.traverse_dict_and_find_all_refs(dict_content=this_db_file_line_content,
                                                     ref_file_path=this_db_file,
                                                     json_or_db='db',
                                                     ref_file_line=this_db_file_line)
        if return_result:
            return self.all_img_refs


    def traverse_dict_and_find_all_refs(self, dict_content=None, ref_file_path=None,
                                        json_or_db=None, ref_file_line=None):
        '''
        Function that traverses a JSON-like dictionary looking for references
        to images. For each reference that is found, an `img_ref` object is created
        and appended to the `self.all_img_refs` list.

        INPUTS:
        -------
        dict_content (DICT) : JSON-like content of the DB or JSON file.
        ref_file_path (STR) : Relative file path to the reference file that is
            being traversed. For example: 'worlds/porvenir/world.json' or
            'worlds/porvenir/data/actors.db'.
        json_or_db (STR) : String that describes whether the reference file being
            traversed is a DB file or a JSON file. The acceptable/valid values
            for this variable are exclusively "json" or "db".
        ref_file_line (INT or None): For '.db' reference files, there are multiple
            JSON-like dictionaries per row. The `ref_file_line` argument indicates
            which line in the ".db" file this particular `img_ref` can be found.
            For example, if the reference to the image is on the 5th line of the
            "journal.db" file, then `ref_file_line` will equal 4. In cases where
            the reference was found in a ".json" file, this attribute is instead
            set to None.
            NOTE: As with everything else in Python, this line number is zero-indexed.

        RETURNS:
        --------
        None

        '''
        # Regular Expression used to find image files
        #regex_img_exp = re.compile('.*\.webp|.*\.jpg|.*\.jpeg|.*\.png')
        #regex_img_exp = re.compile('.*\.webp.*|.*\.jpg.*|.*\.jpeg.*|.*\.png.*')
        regex_img_exp = re.compile('\.webp|\.jpg|\.jpeg|\.png')

        # Within each leaf of the dict tree, see if there is a
        # reference to an image.
        for i,this_item in enumerate(dict_walker(dict_content)):

            this_item_content = this_item[-1]
            if type(this_item_content) == str:

                # If an image extension is found, extract the full file path
                if regex_img_exp.findall(this_item_content):
                    this_img_ref_content = this_item_content

                    # Check if leaf is an HTML block
                    if BeautifulSoup(this_img_ref_content, 'html.parser').find():

                        # If it is an HTML block, search for images
                        img_html_matches = BeautifulSoup(this_img_ref_content, 'html.parser').findAll("img")
                        unique_img_refs_in_html = {}
                        for this_match in img_html_matches:
                            if this_match['src'] not in unique_img_refs_in_html:
                                unique_img_refs_in_html[this_match['src']] = 1
                            else:
                                unique_img_refs_in_html[this_match['src']] += 1

                        # For every image found, generate a reference_dict
                        for this_img_ref in unique_img_refs_in_html:
                            this_ref_obj = img_ref(ref_file_type=json_or_db,
                                                   ref_file_path=ref_file_path,
                                                   ref_file_line=ref_file_line if json_or_db == 'db' else None,
                                                   full_json_address=this_item,
                                                   img_path_for_ref=this_img_ref,
                                                   world_refs_obj=self)
                            self.all_img_refs.append(this_ref_obj)
                            self.all_img_refs_by_id[this_ref_obj.ref_id] = this_ref_obj

                    # If the leaf is not an HTML chunk, it's an img reference,
                    # so we just need to add it to the list of references.
                    else:
                        this_ref_obj = img_ref(ref_file_type=json_or_db,
                                               ref_file_path=ref_file_path,
                                               ref_file_line=ref_file_line if json_or_db == 'db' else None,
                                               full_json_address=this_item,
                                               img_path_for_ref=this_img_ref_content,
                                               world_refs_obj=self)
                        self.all_img_refs.append(this_ref_obj)
                        self.all_img_refs_by_id[this_ref_obj.ref_id] = this_ref_obj

    def fix_incorrect_file_extensions(self):
        '''
        Looks into the world's `img_ref`s and checks if their encoding matches
        the one in their respective file extensions.
        For example, consider that an `img_ref` points to a file on disk called
        "worlds/myworld/myimg.jpeg", but the actual encoding used for the image
        is "PNG". In that case, this function renames the file on disk to be
        "worlds/myworld/myimg.png", updates all the `img_ref` objects that point
        to that image and updates the `world_refs` object.
        NOTE: This mehtod does not belong to the `img_ref` class on purpose!
        That's because one single image on disk can have multiple references in
        the world.

        INPUTS:
        -------
        None

        RETURNS:
        --------
        None

        '''
        refs_indexed_by_img = self.get_refs_indexed_by_img()

        # Looping over every image found in references
        for img_counter, this_img_path in enumerate(refs_indexed_by_img):
            temp_ref = refs_indexed_by_img[this_img_path][0]

            # Ensuring that we only try to "fix" extensions for images that are
            # inside the world folder and that actually exist on disk
            if temp_ref.img_exists and temp_ref.ref_img_in_world_folder and not temp_ref.correct_extension:
                old_content = temp_ref.get_img_ref_content()
                old_img_path_for_ref = temp_ref.img_path_for_ref

                new_extension = temp_ref.img_encoding
                new_img_path_for_ref = os.path.join(pathlib.Path(old_img_path_for_ref).parent,pathlib.Path(old_img_path_for_ref).stem) + '.' + new_extension
                new_content = old_content.replace(old_img_path_for_ref,new_img_path_for_ref)

                os.rename(old_img_path_for_ref,new_img_path_for_ref)

                # After the file on disk was fixed, all the `img_ref`s that
                # pointed to the old image need to be updated
                for ref_counter, this_ref in enumerate(refs_indexed_by_img[this_img_path]):
                    this_ref.set_editable_attributes(new_img_path_for_ref)
                    this_ref.push_updated_content_to_world(new_content)


    def find_all_images_in_world_folder(self):
        '''
        Returns a list containing all of the images inside the World folder.

        INPUTS:
        -------
        None

        RETURNS:
        --------
        all_images_in_world_folder (LIST) : List containing all of the images
            inside the World folder.

        '''
        # Using rglob to find multiple patterns:
        types = ('*.jpg','*.jpeg','*.png','*.webp')
        all_images_in_world_folder = []
        for this_type in types:
            all_images_in_world_folder.extend(list(pathlib.Path(self.world_folder).rglob(this_type)))

        # Fixing double backslash into forward slash
        for i,this_img in enumerate(all_images_in_world_folder):
            all_images_in_world_folder[i] = str(this_img).replace('\\','/')

        return all_images_in_world_folder

    def get_all_unused_images_in_world_folder(self):
        '''
        INPUTS:
        -------
        Searches the world folder for all image files and compares it to the
        images being referenced in all of the `img_ref` objects.
        In the end, the function returns the list of unused images.

        RETURNS:
        --------
        unused_images_in_world_folder (LIST) : list of all the unused images
            inside the world folder.

        '''
        # Getting a list of all images on disk inside the World folder.
        all_images_in_world_folder = self.find_all_images_in_world_folder()

        # Making a counter for each image inside the World folder.
        all_images_in_world_folder_dict = {}
        for this_img_in_folder in all_images_in_world_folder:
            all_images_in_world_folder_dict[this_img_in_folder] = 0

        # Looping over every `img_ref`. For each image found, we increment the
        # respective counter.
        for this_ref in self.all_img_refs:
            if this_ref.img_path_for_ref in all_images_in_world_folder_dict:
                all_images_in_world_folder_dict[this_ref.img_path_for_ref] += 1

        # Fishing out only images whose counters remain at zero.
        unused_images_in_world_folder = []
        for this_img_in_folder in all_images_in_world_folder_dict:
            if all_images_in_world_folder_dict[this_img_in_folder] == 0:
                unused_images_in_world_folder.append(this_img_in_folder)

        return unused_images_in_world_folder


    def add_unused_images_to_trash_queue(self):
        '''
        INPUTS:
        -------
        Scans the World folder for unused images and adds them all to the trash
        queue.

        RETURNS:
        --------
        None

        '''
        # Getting the list of unised images in World folder
        unused_images_in_world_folder = self.get_all_unused_images_in_world_folder()

        # Adding all of them to the `trash_queue`
        for this_img in unused_images_in_world_folder:
            self.trash_queue.add(this_img.replace('\\','/'))

    def get_broken_refs(self):
        '''
        INPUTS:
        -------
        Scans the World and finds references to images that do not exist on disk.
        In the end, the list of broken references is returned.

        RETURNS:
        --------
        broken_refs (LIST) : List of `img_ref` objects containing references to
            images that do not exist on disk.

        '''
        broken_ref_count = 0
        broken_refs = []

        # Looping over every `img_ref` object searching for references to files
        # that don't exist in disk or that have already been added to the trash queue.
        for this_ref in self.all_img_refs:
            if ((this_ref.img_path_on_disk == 'ERROR!!! IMG REFERENCE NOT ON DISK!!!')
                and (not this_ref.img_ref_external_web_link)) or (
                        this_ref.img_path_for_ref in self.trash_queue):
                broken_ref_count += 1
                broken_refs.append(this_ref)
        return broken_refs

    def try_to_fix_one_broken_ref(self, img_ref_to_fix):
        '''
        Some older Foundry worlds pointed to the "modules" folder instead of the
        "worlds" folder. This function takes one single `img_ref` object that points
        to a file on disk that does not exist and checks if it points to an image
        inside the "modules" folder instead. If it does, it tries to search for
        a file on disk with the same file path, but substituting "modules" with
        "worlds". If this new file path points to an image that actually exists,
        the `img_ref` is updated accordingly.

        INPUTS:
        -------
        img_ref_to_fix (OBJECT) : An `img_ref` object whose file on disk will be
            investigated for potential substitution from the "modules" folder
            to the "worlds" folder.

        RETURNS:
        --------
        broken_ref_fixed (BOOL) : Indicates whether or not the `img_ref` object
            being evaluated was fixed.

        '''
        # The default value below assumes that the broken ref will remain broken
        broken_ref_fixed = False

        # Checks if the `img_ref` points to the "modules" folder
        if img_ref_to_fix.img_path_for_ref[:7] == 'modules':

            # If it does, we try to swap the "modules" folder for the "world"
            # folder and see if this new file exists on disk. If so, the reference
            # is fixed!
            new_img_path_for_ref = img_ref_to_fix.img_path_for_ref.replace('modules','worlds')
            if os.path.isfile(new_img_path_for_ref):
                new_img_content = img_ref_to_fix.get_img_ref_content().replace(img_ref_to_fix.img_path_for_ref,new_img_path_for_ref)
                img_ref_to_fix.set_editable_attributes(new_img_path_for_ref)
                img_ref_to_fix.push_updated_content_to_world(new_img_content)
                broken_ref_fixed = True
        return broken_ref_fixed

    def try_to_fix_all_broken_refs(self):
        '''
        Some older Foundry worlds pointed to the "modules" folder instead of the
        "worlds" folder. This function scans all of the `img_ref`s in the World
        and tried to fix them all. See the `try_to_fix_one_broken_ref` mehtod
        for more info.

        INPUTS:
        -------
        None

        RETURNS:
        --------
        None

        '''
        broken_refs = self.get_broken_refs()
        #broken_ref_imgs = self.get_refs_indexed_by_img(broken_refs)
        #print(f'Number of broken references: {len(broken_refs)}\n'
        #      f'Number of images with broken references: {len(list(broken_ref_imgs.keys()))}\n')
        broken_ref_fixed_counter = 0
        for this_img_ref_to_fix in broken_refs:
            broken_ref_fixed_counter += self.try_to_fix_one_broken_ref(this_img_ref_to_fix)
        print(f'Fixed {broken_ref_fixed_counter} broken refs by pointing to'
              ' `worlds` folder instead of `modules` folder.')
        #broken_refs = self.get_broken_refs()
        #print(f'Number of broken references after fix: {len(broken_refs)}')

    def print_broken_ref_details(self):
        '''
        Prints main details regarding broken refs: how many broken refs there
        are and how many actual images have broken refs.

        INPUTS:
        -------
        None

        RETURNS:
        --------
        None
        '''
        broken_refs = self.get_broken_refs()
        broken_ref_imgs = self.get_refs_indexed_by_img(broken_refs)
        print(f'Number of broken references: {len(broken_refs)}\n'
              f'Number of images with broken references: {len(list(broken_ref_imgs.keys()))}\n')

    def get_refs_indexed_by_hash_by_img(self, input_ref_list=None):
        '''
        Searches all the `img_ref`s in the world and builds an index of all the
        references. The dictionary created by this function indexes the refeences
        by hash and by image file path.

        INPUTS:
        -------
        input_ref_list (LIST or None) : List of references to be indexes. When
            this input is left blank (equal to "None"), the default behavior is
            to just index all of the `img_ref`s in the `self.all_img_refs`
            attribute.

        RETURNS:
        --------
        refs_indexed_by_hash_by_img (DICT) : Dictionary that indexes all of the
            `img_ref` objects by their hashes and by the file paths of the images.
            Structure of output:
            refs_indexed_by_hash_by_img = {'hash_a':{'img_1':[ref_i,
                                                              ref_ii,
                                                              ref_iii],
                                                     'img_2':[ref_iv,
                                                              ref_v,
                                                              ref_vi,
                                                              ref_vii]}}
        '''
        # Preparing dictionary for indexing
        refs_indexed_by_hash_by_img = {}

        # Checking which ref_list to use
        if input_ref_list==None:
            ref_list = self.all_img_refs
        else:
            ref_list = input_ref_list

        # Looping over all of the `img_ref`s in `ref_list`
        for this_ref in ref_list:
            if this_ref.img_hash not in refs_indexed_by_hash_by_img:
                refs_indexed_by_hash_by_img[this_ref.img_hash] = {}

            if this_ref.img_path_for_ref not in refs_indexed_by_hash_by_img[this_ref.img_hash]:
                refs_indexed_by_hash_by_img[this_ref.img_hash][this_ref.img_path_for_ref] = []

            refs_indexed_by_hash_by_img[this_ref.img_hash][this_ref.img_path_for_ref].append(this_ref)

        return refs_indexed_by_hash_by_img

    def get_duplicated_images(self):
        '''
        Scans all of the `img_ref` objects and finds which ones are duplicates
        of each other. The results of this function are indexed by hash.

        INPUTS:
        -------
        None

        RETURNS:
        --------
        duplicated_images (DICT) : Dictionary that indexes the `img_ref` objects
            by hash and by image file.
            Structure of output:
            duplicated_images = {'hash_a':{'img_1':[ref_i,
                                                    ref_ii,
                                                    ref_iii],
                                           'img_2':[ref_iv,
                                                    ref_v,
                                                    ref_vi,
                                                    ref_vii]}}
        '''
        refs_indexed_by_hash_by_img = self.get_refs_indexed_by_hash_by_img()

        duplicated_images_count_by_hash = 0
        duplicated_images = {}
        for this_hash in refs_indexed_by_hash_by_img:
            if (len(refs_indexed_by_hash_by_img[this_hash]) > 1) and (this_hash != None):
                duplicated_images[this_hash] = refs_indexed_by_hash_by_img[this_hash]
                duplicated_images_count_by_hash += 1

        return duplicated_images

    def fix_one_set_of_duplicated_images(self, this_duplicated_img_dict=None):
        '''
        Given a set of duplicated images, this function "fixes" all of the
        references. Fixing them involves making all of the `img_ref` objects point
        to one single image, the new `img_ref` info is pushed to the world and
        the unreferenced images are added to the trash queue.

        INPUTS:
        -------
        this_duplicated_img_dict (DICT) : a dictionary of `img_ref`s that point
        to different files on disk but which are all duplicated images. The
        dictionary is indexed by file path.
            Structure of input:
            duplicated_images = {'img_1':[ref_i,
                                          ref_ii,
                                          ref_iii],
                                 'img_2':[ref_iv,
                                          ref_v,
                                          ref_vi,
                                          ref_vii]}

        RETURNS:
        --------
        None

        '''
        main_img = list(this_duplicated_img_dict.keys())[0]
        imgs_to_be_replaced = list(this_duplicated_img_dict.keys())[1:]

        for img_to_be_replaced in imgs_to_be_replaced:
            this_img_refs = this_duplicated_img_dict[img_to_be_replaced]
            for this_ref in this_img_refs:
                updated_content = this_ref.get_img_ref_content().replace(this_ref.img_path_for_ref,main_img)
                this_ref.set_editable_attributes(main_img)
                this_ref.push_updated_content_to_world(updated_content)

            self.trash_queue.add(img_to_be_replaced.replace('\\','/'))

    def fix_all_sets_of_duplicated_images(self):
        '''
        Scans all `img_ref`s in a world and fixes all of the sets of duplicated
        images.

        INPUTS:
        -------
        None

        RETURNS:
        --------
        None

        '''
        duplicated_images = self.get_duplicated_images()

        for this_hash in duplicated_images:
            this_duplicated_img_dict = duplicated_images[this_hash]
            self.fix_one_set_of_duplicated_images(this_duplicated_img_dict)

        duplicated_images = self.get_duplicated_images()

    def update_one_ref_to_webp(self, img_ref_to_update=None):
        '''
        Updates one single `img_ref` object such that it points to the ".webp"
        image on disk instead of whatever the original file type was.

        INPUTS:
        -------
        img_ref_to_update (OBJECT) : instance of the `img_ref` class that will
            be updated by this function.

        RETURNS:
        --------
        None
        '''
        old_img_path_for_ref = img_ref_to_update.img_path_for_ref
        old_img_ref_content  = img_ref_to_update.get_img_ref_content()

        new_img_path_for_ref = img_ref_to_update.webp_img_path_for_ref
        new_img_ref_content  = old_img_ref_content.replace(old_img_path_for_ref,
                                                           new_img_path_for_ref)

        img_ref_to_update.set_editable_attributes(new_img_path_for_ref)
        img_ref_to_update.push_updated_content_to_world(new_img_ref_content)

    def get_refs_indexed_by_img(self, input_ref_list=None):
        '''
        Creates a dictionary that indexes all of the `img_ref` objects inside a
        Foundry World by file path.

        INPUTS:
        -------
        input_ref_list (LIST or None) : List of references to be indexes. When
            this input is left blank (equal to "None"), the default behavior is
            to just index all of the `img_ref`s in the `self.all_img_refs`
            attribute.

        RETURNS:
        --------
        refs_indexed_by_img (DICT) : dictionary that indexes `img_ref` objects
            by the image file paths.
            Structure of output:
            refs_indexed_by_img = {'img_1':[ref_i,
                                            ref_ii,
                                            ref_iii],
                                   'img_2':[ref_iv,
                                            ref_v,
                                            ref_vi,
                                            ref_vii]}
        '''
        # Preparing dictionary for output
        refs_indexed_by_img = {}

        # Checking which ref_list to use
        if input_ref_list==None:
            ref_list = self.all_img_refs
        else:
            ref_list = input_ref_list

        # Looping all the `img_ref`s in `ref_list`
        for this_ref in ref_list:
            if this_ref.img_path_for_ref not in refs_indexed_by_img:
                refs_indexed_by_img[this_ref.img_path_for_ref] = []
            refs_indexed_by_img[this_ref.img_path_for_ref].append(this_ref)
        return refs_indexed_by_img

    def convert_all_images_to_webp_and_update_refs(self):
        '''
        Converts all of the images referenced in a Foundry World into a ".webp"
        format, updates all of the `img_ref` objects and pushes all of the
        updated data back into the `world_refs` object.

        INPUTS:
        -------
        None

        RETURNS:
        --------
        None

        '''
        refs_indexed_by_img = self.get_refs_indexed_by_img()

        printed_percentages = {}

        for img_counter, this_img_path in enumerate(refs_indexed_by_img):
            temp_ref = refs_indexed_by_img[this_img_path][0]
            temp_path_for_deletion = this_img_path
            percent_imgs_checked = int(100*img_counter/len(refs_indexed_by_img))
            if (percent_imgs_checked % 10 == 0) & (percent_imgs_checked not in printed_percentages):
                printed_percentages[percent_imgs_checked] = True
                print(f'Scanned {percent_imgs_checked}% of all images.')
            if (not temp_ref.is_webp) and (temp_ref.img_exists) and (temp_ref.ref_img_in_world_folder):
                conversion_return_code = 0
                if (not os.path.isfile(temp_ref.webp_img_path_for_ref)):
                    conversion_return_code = temp_ref.create_webp_copy()
                if (conversion_return_code == 0) and (os.path.isfile(temp_ref.webp_img_path_for_ref)):
                    for ref_counter, this_ref in enumerate(refs_indexed_by_img[this_img_path]):
                        self.update_one_ref_to_webp(this_ref)
                self.trash_queue.add(temp_path_for_deletion.replace('\\','/'))
        print('Scanned 100% of all images.')

    def export_all_json_and_db_files(self):
        '''
        Creates a backup of the ".json" & ".db" files on disk and exports the
        data inside the `world_refs` object into new ".json" & ".db" files onto
        the disk.

        INPUTS:
        -------
        None

        RETURNS:
        --------
        None

        '''
        # Scanning all JSON files for references to images
        for this_json_file in self.json_files:
            # Backing up current JSON file
            shutil.copyfile(this_json_file, this_json_file+'bak')

            this_json_file_content = self.json_files[this_json_file]
            # Writing JSON files to disk
            with open(this_json_file,'w',encoding="utf-8") as fout:
                new_line = json.dumps(this_json_file_content,separators=(',', ':'),ensure_ascii=False) + '\n'
                fout.writelines([new_line])

        for this_db_file in self.db_files:
            # Backing up current DB file
            shutil.copyfile(this_db_file, this_db_file+'bak')

            # Writing DB files to disk, line by line
            with open(this_db_file,'w',encoding="utf-8") as fout:
                for this_db_file_line,this_db_file_line_content in enumerate(self.db_files[this_db_file]):
                    new_line = json.dumps(this_db_file_line_content,separators=(',', ':'),ensure_ascii=False) + '\n'
                    fout.writelines([new_line])

    def find_refs_by_img_path(self, img_path_to_search=None):
        '''
        Gets a list of all the `img_ref` objects that point to a specific file
        on disk.

        INPUTS:
        -------
        img_path_to_search (STR) : string that describes the file path of the
            image being searched.

        RETURNS:
        --------
        found_refs (LIST) : list of `img_ref` objects that all point to the same
            image file on disk.

        '''
        found_refs = []
        for this_ref in self.all_img_refs:
            if this_ref.img_path_for_ref == img_path_to_search:
                found_refs.append(this_ref)
        return found_refs

    def move_all_imgs_in_trash_queue_to_trash(self):
        '''
        Function used to actually move the files from the `trash_queue` into the
        "_trash" folder inside the world.

        INPUTS:
        -------
        None

        RETURNS:
        --------
        None

        '''
        for this_file in self.trash_queue:

            # Making sure that the file exists and that it is actually inside
            # the world folder. This is to prevent accidentally moving images
            # from the Foundry Core folder
            if (os.path.isfile(this_file) and
                re.match('.*' + self.world_folder + '.*', this_file)):
                temp = re.split('\\\\|/',this_file)
                temp.insert(2,'_trash')
                trash_name = os.path.join(*temp).replace('\\','/')
                os.makedirs(os.path.dirname(trash_name), exist_ok=True)
                os.rename(this_file,trash_name)

    def empty_trash(self,delete_unreferenced_images=False):
        '''
        Actually deletes the content inside the "_trash" folder inside the world.
        Careful when using this function!!! This function has no "undo"!!!!!

        INPUTS:
        -------
        delete_unreferenced_images_bool (BOOL) : indicates whether or not the
            files in the "_trash" folder should actually be deleted. When this
            input is set to "False", the function will simply terminate without
            deleting anything.

        RETURNS:
        --------
        None

        '''
        if delete_unreferenced_images:
            shutil.rmtree(self.trash_folder)

    def restore_bak_files(self):
        '''
        Restores the ".jsonbak" and "dbbak" files to ".json" and ".db" respectively.
        Note: this process overwrites whatever was in their places.

        INPUTS:
        -------
        None

        RETURNS:
        --------
        None
        '''
        list_of_dbbak_files   = [str(this_path).replace('\\','/') for this_path in pathlib.Path(self.world_folder).rglob('*.dbbak')]
        list_of_jsonbak_files = [str(this_path).replace('\\','/') for this_path in pathlib.Path(self.world_folder).rglob('*.jsonbak')]

        for this_dbbak_file in list_of_dbbak_files:
            this_dborig_file = this_dbbak_file[:-3]
            shutil.move(this_dbbak_file,this_dborig_file,)

        for this_jsonbak_file in list_of_jsonbak_files:
            this_jsonorig_file = this_jsonbak_file[:-3]
            shutil.move(this_jsonbak_file,this_jsonorig_file)

    def restore_trash_folder(self):
        '''
        Restores files that got sent to the "_trash" folder.

        INPUTS:
        -------
        None

        RETURNS:
        --------
        None
        '''

        trash_files_and_folders = os.listdir(self.trash_folder)

        for this_item in trash_files_and_folders:
            pass
            shutil.move(os.path.join(self.trash_folder,this_item),
                        os.path.join(self.world_folder,this_item))


def input_checker(user_data_folder=None, world_folder=None,
                  core_data_folder=None,ffmpeg_location=None,
                  delete_unreferenced_images=False):
    '''
    Checks all of the inputs to make sure they are valid. For the folder inputs,
    it checks that the folders exist. For the FFMPEG input, it checks if the
    ".exe" executable file exists on disk. For the flag that determines whether
    or not files will actually be deleted, it checks if the input is "y" or "n".

    !!!Note: This is also where the working directory is set!

    !!!TODO: I need to update this function when I make the call to FFMPEG
    work across platforms (Linux & Mac).

    INPUTS:
    -------
    user_data_folder (STR) : String that describes the absolute path for
        the user data folder on disk. On Windows installations, this attribute
        should typically look something like this: "C:/Users/jegasus/AppData/Local/FoundryVTT/Data"
    world_folder (STR) : String that describes the relative path to the
        world folder to be scanned by the world reference tool. This path needs
        to be relative to the user data folder (i.e., the combination of the
        `user_data_folder` attribute and the `world_folder` represent the
        absolute path of the World folder to be scanned. This attribute should
        typically look like this: "worlds/porvenir", or "worlds/kobold-cauldron".
    core_data_folder (STR) : String that describes the absolute path to the
        Foundry Core Data folder. This attribute should typically look like
        this: "C:/Program Files/FoundryVTT/resources/app/public"
    ffmpeg_location (STR) : String that describes the absolute path to
        the ffmpeg executable. This attribute should typically look like this:
        "C:/Program Files (x86)/Audacity/libraries/ffmpeg.exe".
    delete_unreferenced_images (STR) : string that indicates whether or not the
        files that got placed in the "_trash" folder should actually be deleted
        at the end of the process. This attribute expects either "y" or "n".


    RETURNS:
    --------
    checked_inputs (DICT) : A dictionary containing the verified and modified
        inputs.

    EXAMPLE:
    --------
    # Input:
    checked_inputs = input_checker(user_data_folder = "C:/Users/jegasus/AppData/Local/FoundryVTT/Data",
                                   world_folder     = "worlds/porvenir",
                                   core_data_folder = "C:/Program Files/FoundryVTT/resources/app/public",
                                   ffmpeg_location  = "C:/Program Files (x86)\Audacity/libraries/ffmpeg.exe",
                                   delete_unreferenced_images="n")

    user_data_folder_checked = checked_inputs["user_data_folder"]
    world_folder_checked = checked_inputs["world_folder"]
    core_data_folder_checked = checked_inputs["core_data_folder"]
    ffmpeg_location_checked = checked_inputs["ffmpeg_location"]
    delete_unreferenced_images_checked = checked_inputs["delete_unreferenced_images_checked"]
    '''
    if type(user_data_folder) != str:
        raise AssertionError('The type of value supplied for the `user_data_folder` variable is not valid. Please provide a string value.')

    if type(world_folder) != str:
        raise AssertionError('The type of value supplied for the `world_folder` variable is not valid. Please provide a string value.')

    if type(core_data_folder) != str:
        raise AssertionError('The type of value supplied for the `core_data_folder` variable is not valid. Please provide a string value.')

    if type(ffmpeg_location) != str:
        raise AssertionError('The type of value supplied for the `ffmpeg_location` variable is not valid. Please provide a string value.')

    if type(delete_unreferenced_images) != str:
        raise AssertionError('The type of value supplied for the `delete_unreferenced_images` variable is not valid. Please provide a string value.')


    user_data_folder = os.path.normpath(user_data_folder).replace("\\","/")
    if not os.path.isdir(user_data_folder):
        raise NotADirectoryError(f'The `user_data_folder` supplied does not exist: {user_data_folder}')

    world_folder = os.path.normpath(world_folder).replace("\\","/")
    if not os.path.isdir(os.path.join(user_data_folder,os.path.normpath(world_folder))):
        raise NotADirectoryError(f'The `world_folder` supplied does not exist: {world_folder}')

    core_data_folder = os.path.normpath(core_data_folder).replace("\\","/")
    if not os.path.isdir(core_data_folder):
        raise NotADirectoryError(f'The `core_data_folder` supplied does not exist: {core_data_folder}')

    # !!! FIX HERE FOR CROSS-PLATFORM CHECKING
    ffmpeg_location = os.path.normpath(ffmpeg_location).replace("\\","/")
    if not os.path.isfile(ffmpeg_location):
        raise NotADirectoryError(f'The `ffmpeg_location` supplied does not exist: {ffmpeg_location}')

    if delete_unreferenced_images.lower() == 'y':
        delete_unreferenced_images_bool = True
    elif delete_unreferenced_images.lower() == 'n':
        delete_unreferenced_images_bool = False
    else:
        raise ValueError(f'The value supplied to the `delete_unreferenced_images` flag \
                         is not valid. Please type in either "y" or "n".')

    checked_inputs = {'user_data_folder':user_data_folder,
                      'world_folder':world_folder,
                      'core_data_folder':core_data_folder,
                      'ffmpeg_location':ffmpeg_location,
                      'delete_unreferenced_images':delete_unreferenced_images_bool}

    os.chdir(user_data_folder)

    return checked_inputs


# Function that does all that is needed for world compression in one single command
def one_liner_compress_world(user_data_folder=None, world_folder=None,core_data_folder=None,
                             ffmpeg_location=None, delete_unreferenced_images=False):
    '''
    Main function to compress the Foudry World.

    INPUTS:
    -------
    user_data_folder (STR) : String that describes the absolute path for
        the user data folder on disk. On Windows installations, this attribute
        should typically look something like this: "C:/Users/jegasus/AppData/Local/FoundryVTT/Data"
    world_folder (STR) : String that describes the relative path to the
        world folder to be scanned by the world reference tool. This path needs
        to be relative to the user data folder (i.e., the combination of the
        `user_data_folder` attribute and the `world_folder` represent the
        absolute path of the World folder to be scanned. This attribute should
        typically look like this: "worlds/porvenir", or "worlds/kobold-cauldron".
    core_data_folder (STR) : String that describes the absolute path to the
        Foundry Core Data folder. This attribute should typically look like
        this: "C:/Program Files/FoundryVTT/resources/app/public"
    ffmpeg_location (STR) : String that describes the absolute path to
        the ffmpeg executable. This attribute should typically look like this:
        "C:/Program Files (x86)/Audacity/libraries/ffmpeg.exe".
    delete_unreferenced_images (STR) : string that indicates whether or not the
        files that got placed in the "_trash" folder should actually be deleted
        at the end of the process. This attribute expects either "y" or "n".

    RETURNS:
    --------
    None

    EXAMPLE:
    --------
    # Input:
    None

    # Output:
    # None
    '''
    checked_inputs = input_checker(user_data_folder,world_folder,core_data_folder,
                                   ffmpeg_location,delete_unreferenced_images)

    user_data_folder_checked = checked_inputs['user_data_folder']
    world_folder_checked = checked_inputs['world_folder']
    core_data_folder_checked = checked_inputs['core_data_folder']
    ffmpeg_location_checked = checked_inputs['ffmpeg_location']
    delete_unreferenced_images_checked = checked_inputs['delete_unreferenced_images']

    my_world_refs = world_refs(user_data_folder_checked,world_folder_checked,
                               core_data_folder_checked,ffmpeg_location_checked)

    #my_world_refs.find_all_img_references_in_world()
    my_world_refs.try_to_fix_all_broken_refs()
    my_world_refs.fix_incorrect_file_extensions()
    my_world_refs.fix_all_sets_of_duplicated_images()
    my_world_refs.convert_all_images_to_webp_and_update_refs()
    my_world_refs.fix_all_sets_of_duplicated_images()
    my_world_refs.export_all_json_and_db_files()
    my_world_refs.add_unused_images_to_trash_queue()
    my_world_refs.move_all_imgs_in_trash_queue_to_trash()
    my_world_refs.empty_trash(delete_unreferenced_images_checked)

    return my_world_refs
