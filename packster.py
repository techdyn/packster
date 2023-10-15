#!/usr/bin/python
"""

    ____                __          __
   / __ \ ____ _ _____ / /__ _____ / /_ ___   _____
  / /_/ // __ `// ___// //_// ___// __// _ \ / ___/
 / ____// /_/ // /__ / ,<  (__  )/ /_ /  __// /
/_/     \__,_/ \___//_/|_|/____/ \__/ \___//_/  v{SCRIPT_VERSION}
                                                by TechDyn

"""

SCRIPT_VERSION = "0.1.1"

import os, argparse, glob, json, fnmatch
from pathlib import Path
from zipfile import ZipFile
from datetime import datetime

parsed_args = []
target_package = None
dist_name = None

def is_excluded(path, exclude_match):
    for m in exclude_match:
        if fnmatch.fnmatch(path, m):
            return True

    return False


def process_dir(directory, name_filter='*', exclude=None, skip=None, match=None, recurse=False, skip_dir=False):
    if match is None:
        match = []
    if skip is None:
        skip = []
    if exclude is None:
        exclude = []

    for path in Path(directory).rglob(name_filter) if recurse else Path(directory).glob(name_filter):
        if path not in skip:  # dedup
            if path not in match:  # dedup
                if skip_dir and os.path.isdir(path):
                    continue

                if not is_excluded(path, exclude):  # skip excluded
                    match.append(path)  # add for dedup
                    if get_arg('verbose'):
                        q_print('Found: ', path)
                    continue

        if path not in skip:
            skip.append(path)

    return match, skip


def zip_files(files, out_name='output.zip', out_path='dist'):
    try:
        if not os.path.exists(out_path):
            os.mkdir(out_path)
    except OSError as error:
        print("Failed to create output path.")
        return

    with ZipFile(os.path.join(out_path, out_name), 'w') as zipObj:
        for f in files:
            zipObj.write(f)


def process_packster(data, package):
    q_print('Processing:  ', package)

    if dist_name and len(data['packages']) > 1:
            print('Error: Must specify --package arg with --dist, exiting...')
            exit()

    pkg_data = data['packages'][package]
    exclude = pkg_data['exclude'] if 'exclude' in pkg_data else []

    match = []
    skip = []

    if 'dirs' in pkg_data:
        for directory in pkg_data['dirs']:
            process_dir(directory, '*', exclude, skip, match, True, False)

    if 'files' in pkg_data:
        for file in pkg_data['files']:
            process_dir('.', file, exclude, skip, match, False, True)

    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    output_fn = package + "_" + timestamp + '.zip' if not dist_name else dist_name
    
    output_dir = pkg_data['outDir'] if 'outDir' in pkg_data else 'dist'

    for f in skip:
        if get_arg('verbose'):
            q_print('Skipped:  ', f)

    q_print('Output to:   ', os.path.join(output_dir, output_fn))
    zip_files(match, output_fn, output_dir)


def get_arg(name):
    global parsed_args
    return getattr(parsed_args, name)


def q_print(*val):
    if not get_arg('quiet'):
        print(*val)


def set_dir_path(string):
    if os.path.isdir(string):
        return string
    else:
        raise OSError(string)


def set_target_package(string):
    global target_package
    target_package = string

def set_dist_name(string):
    global dist_name
    dist_name = string

def parse_args():
    global parsed_args
    parser = argparse.ArgumentParser(description="A simple packing tool to produce archives as defined in `packster.json`.")
    parser.add_argument('--init', required=False, default=False, action='store_true', help="create a basic `packster.json` file in the current working directory")
    parser.add_argument('--verbose', required=False, default=False, action='store_true', help="output additional log information")
    parser.add_argument('--quiet', required=False, default=False, action='store_true', help='suppress log output, except for errors')
    parser.add_argument('--version', required=False, default=False, action='store_true', help='output current version information')
    parser.add_argument('--dir', type=set_dir_path, help='specify the current working directory')
    parser.add_argument('--dist', type=set_dist_name, help='specify the dist filename')
    parser.add_argument('--package', type=set_target_package, help='specify a particular package')
    parsed_args = parser.parse_args()


def create_packster():
    if os.path.exists("packster.json"):
        print()
        print('Warning: packster.json already exists, exiting...')
        return

    base_packster = {
        "packages": {
            "Project": {
                "dirs": [
                    "*"
                ],
                "files": [
                    "*"
                ],
                "exclude": []
            }
        }
    }

    with open('packster.json', 'w') as outfile:
        outfile.write(json.dumps(base_packster, indent=4))

    q_print()
    q_print('Success: packster.json has been created.')

def main():
    parse_args()

    if get_arg('version'):
        print("v%s" % SCRIPT_VERSION)
        exit()

    q_print(__doc__.replace("{SCRIPT_VERSION}", SCRIPT_VERSION))
    _dir = get_arg('dir') or os.getcwd()
    q_print('Working in:  ', _dir)

    os.chdir(_dir)

    if get_arg('init'):
        create_packster()
        exit()

    if os.path.exists("packster.json"):
        with open("packster.json", 'r') as f:
            data = json.load(f)

            if target_package is not None:
                if target_package in data['packages']:
                    process_packster(data, target_package)
                else:
                    print('Error: packster.json does not reference package "%s", exiting...' % target_package)
                    exit()
            else:
                for package in data['packages'].keys():
                    process_packster(data, package)
    else:
        print()
        print('Error: No packster.json was found, exiting...')

if __name__ == "__main__":
    main()
