# mxml2ly
Convert MusicXML files to LilyPond files. 

Frescobaldi already has a plugin to do this, but it includes all the beaming directions which I don't like, and I also generally don't like the format of the outputted LilyPond code with that, which is why I made this. 

Run the python script `main.py` and select the MusicXML file that you want to convert. Then, select where you want the output LilyPond file to be and what you want it to be called. 

You can set the following values in the `preferences.ini` file: 
- `arranger`  Your name, which will be automatically added to the score as the arranger
- `defaultinputdir` The default directory to search for MusicXML input files
- `defaultoutputdir` The default directory in which LilyPond output files will be saved

