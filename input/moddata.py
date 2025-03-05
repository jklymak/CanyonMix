import sys
import getopt

from tempfile import mkstemp
from shutil import move
from os import fdopen, remove

def replace_data(fname, param, value):
    fh, abs_path = mkstemp()
    print(abs_path)
    with fdopen(fh,'w') as new_file:
        with open(fname) as old_file:
            for line in old_file:
                if param+'=' in line:
                    new_file.write(' '+param+'='+value+',\n')
                else:
                    new_file.write(line)

    # Remove original file
    remove(fname)
    # Move new file
    move(abs_path, fname)

fname = './data'

# Get full command-line arguments
full_cmd_arguments = sys.argv

# Keep all but the first
argument_list = full_cmd_arguments[1:]

short_options = "se"
long_options = ["startTime=", "endTime=", "deltaT="]
arguments, values = getopt.getopt(argument_list, short_options, long_options)
for arg in arguments:
    replace_data(fname, arg[0][2:], arg[1])
