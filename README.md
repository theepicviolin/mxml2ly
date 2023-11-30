# mxml2ly
Convert MusicXML files to LilyPond files. 

Frescobaldi already has a plugin to do this, but it includes all the beaming directions which I don't like, and I also generally don't like the format of the outputted LilyPond code with that, which is why I made this. 

Run the python script `mxml2ly` and select the MusicXML file that you want to convert. Then, select where you want the output LilyPond file to be and what you want it to be called. 

You can call it from the command line too, and provide the following arguments:
- `-i` `--input` The input MusicXML file (default: prompt with a file dialog)
- `-o` `--output` The output LilyPond file (default: prompt with a file dialog)
- `-p` `--parts` Whether the parts should be extracted into separate files, or kept in one file. Can be `separate` or `together`. The code to generate both is included, but this option selects which one will be left uncommented. (default: `together`)
- `-d` `--debug` Whether to print debug messages (default: `False`) 

Example: `python mxml2ly.py -i song.musicxml --output song.ly -p separate -d true`

You can set the following values in the `preferences.ini` file: 
- `Arranger`  Your name, which will be automatically added to the score as the arranger
- `DefaultInputDir` The default directory to search for MusicXML input files
- `DefaultOutputDir` The default directory in which LilyPond output files will be saved
- `Version` The version of the LilyPond you are using
