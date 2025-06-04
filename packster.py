#!/usr/bin/python
r'''

    ____                __          __
   / __ \ ____ _ _____ / /__ _____ / /_ ___   _____
  / /_/ // __ `// ___// //_// ___// __// _ \ / ___/
 / ____// /_/ // /__ / ,<  (__  )/ /_ /  __// /
/_/     \__,_/ \___//_/|_|/____/ \__/ \___//_/  v{SCRIPT_VERSION}
                                                by TechDyn

'''

import os, json

def get_script_version():
    pkg_json_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'package.json')
    if os.path.exists(pkg_json_path):
        try:
            with open(pkg_json_path, 'r') as f:
                data = json.load(f)
                return data.get('version', '0.0.0')
        except Exception:
            raise
    return '0.0.0'

SCRIPT_VERSION = get_script_version()

import argparse, glob, fnmatch, hashlib
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


def read_package_json():
    pkg_json_path = os.path.join(os.getcwd(), 'package.json')
    if os.path.exists(pkg_json_path):
        with open(pkg_json_path, 'r') as f:
            try:
                return json.load(f)
            except Exception:
                return {}
    return {}

def compute_hash(files, hash_type='sha256'):
    hash_types = {
        'sha256': hashlib.sha256,
        'sha1': hashlib.sha1,
        'md5': hashlib.md5
    }
    h = hash_types[hash_type]()
    for f in sorted(files, key=lambda x: str(x)):
        try:
            with open(f, 'rb') as fp:
                while True:
                    chunk = fp.read(8192)
                    if not chunk:
                        break
                    h.update(chunk)
        except Exception:
            continue
    return h.hexdigest()

def get_version_from_hash(package, files):
    """Determine version based on content hash tracking"""
    import time
    # Compute SHA256 hash for all files
    content_hash = compute_hash(files, 'sha256')
    
    # Ensure .packster directory exists
    packster_dir = Path('.packster')
    packster_dir.mkdir(exist_ok=True)
    
    # Version tracking file for this package
    version_file = packster_dir / f"{package}.versions.json"
    
    # Default version structure
    version_data = {
        "current": "0.1.0",
        "history": []
    }
    
    # Load existing version data if available
    if version_file.exists():
        try:
            with open(version_file, 'r') as f:
                version_data = json.load(f)
        except json.JSONDecodeError:
            q_print("Warning: Version file corrupted, starting fresh")
    
    # Check if this hash already exists
    for entry in version_data["history"]:
        if entry["hash"] == content_hash:
            # Return existing version for this hash
            return entry["version"]
    
    # New hash, increment version
    current = version_data["current"]
    major, minor, patch = map(int, current.split('.'))
    
    # Simple increment logic - always increment patch
    # More sophisticated logic could be added here
    patch += 1
    
    # Create new version
    new_version = f"{major}.{minor}.{patch}"
    version_data["current"] = new_version
    
    # Add to history
    timestamp = int(time.time())
    version_data["history"].append({
        "version": new_version,
        "hash": content_hash,
        "timestamp": timestamp,
        "date": datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")
    })
    
    # Save updated version data
    with open(version_file, 'w') as f:
        json.dump(version_data, f, indent=2)
    
    return new_version

def get_output_filename(package, pkg_data, dist_name=None, files=None):
    import re, time
    # Read package.json if present
    pkg_json = read_package_json()
    # Defaults
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    epoch = str(int(time.time()))
    package_name = package  # Always use the key from packster.json
    
    # Determine version
    if 'version' in pkg_data:
        if pkg_data['version'] is True:
            # Auto-versioning based on content hash
            version = get_version_from_hash(package, files)
            q_print(f"Auto-versioning: {version} (based on content hash)")
        elif isinstance(pkg_data['version'], (str, int, float)):
            # Use explicit version from packster.json
            version = str(pkg_data['version'])
            q_print(f"Using version from packster.json: {version}")
        else:
            # Use version from package.json
            version = pkg_json.get('version', '1')
    else:
        # Use version from package.json
        version = pkg_json.get('version', '1')
    
    out_name_tmpl = pkg_data.get('outName', '{TIMESTAMP}-{PACKAGE_NAME}')
    out_ext = pkg_data.get('outExt', 'zip')
    # If user provided --dist, override template
    if dist_name:
        out_name = dist_name
        if not out_name.endswith('.' + out_ext):
            out_name += '.' + out_ext
        return out_name
    # Compute all hashes only once if needed
    hash_cache = {}
    def get_hash(htype):
        if htype not in hash_cache:
            hash_cache[htype] = compute_hash(files, htype) if files else ''
        return hash_cache[htype]
    # Substitute hash patterns with optional length
    def hash_repl(match):
        htype = match.group(1).lower()
        length = match.group(2)
        value = get_hash(htype)
        if length:
            return value[:int(length)]
        return value
    # Regex for {SHA256}, {SHA256:8}, etc.
    pattern = r"\{(SHA256|SHA1|MD5)(?::(\d+))?\}"
    out_name = re.sub(pattern, hash_repl, out_name_tmpl)
    # Substitute other variables
    out_name = out_name.format(
        TIMESTAMP=timestamp,
        EPOCH=epoch,
        PACKAGE_NAME=package_name,
        VERSION=version
    )
    if not out_name.endswith('.' + out_ext):
        out_name += '.' + out_ext
    return out_name

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

    # Compute output filename with hashes if needed
    output_fn = get_output_filename(package, pkg_data, dist_name, files=match)
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

def print_help():
    help_text = r'''
Packster - A simple packing tool to produce archives as defined in packster.json.

USAGE:
  packster [OPTIONS]

OPTIONS:
  --init           Create a basic packster.json file in the current working directory.
  --verbose        Output additional log information.
  --quiet          Suppress log output, except for errors.
  --version        Output current version information.
  --dir DIR        Specify the current working directory.
  --dist NAME      Specify the output filename (overrides template).
  --package NAME   Specify a particular package to pack (default: all in packster.json).
  --help           Show this help message and exit.

CONFIGURATION (packster.json):
  {
    "packages": {
      "MyPackage": {
        "dirs": ["src", "lib"],           // (required) Directories to include
        "files": ["README.md"],           // (required) Files to include
        "exclude": ["*.tmp", "*.log"],    // (optional) Glob patterns to exclude
        "outName": "{TIMESTAMP}-{PACKAGE_NAME}",  // Optional output filename template
        "outExt": "zip",                  // Optional output extension
        "outDir": "dist",                 // Optional output directory
        "version": true                   // Optional: true=auto-versioning, "1.2.3"=explicit version
      }
    }
  }

  Notes:
    - Both "outName" and "outExt" are optional per package. If omitted:
        outName defaults to: {TIMESTAMP}-{PACKAGE_NAME}
        outExt  defaults to: zip

  Template variables for outName:
    {PACKAGE_NAME}  - The package key from packster.json
    {VERSION}       - Version from package.json (or '1' if missing)
    {TIMESTAMP}     - Current timestamp (YYYYmmddHHMMSS)
    {SHA256}        - SHA256 hash of all included files (sorted, concatenated)
    {SHA1}          - SHA1 hash of all included files
    {MD5}           - MD5 hash of all included files
    {SHA256:N}      - First N chars of SHA256 hash (e.g. {SHA256:8})
    {SHA1:N}        - First N chars of SHA1 hash
    {MD5:N}         - First N chars of MD5 hash
    {EPOCH}         - Current UNIX timestamp (seconds since epoch)

  Version handling options:
    - No "version" field: use version from package.json
    - "version": true: enable auto-versioning based on content hashes
    - "version": "1.2.3": use explicit version string
  
  Auto-versioning creates a .packster folder with version history based on content hashes.
  Each unique content hash gets a new version number (0.1.0, 0.1.1, etc.).

EXAMPLES:
  packster --init
  packster --package MyPackage
  packster --dist release.zip
  packster --dir ./project --verbose
'''
    print(help_text)

def parse_args():
    global parsed_args
    parser = argparse.ArgumentParser(description="A simple packing tool to produce archives as defined in `packster.json`.", add_help=False)
    parser.add_argument('--init', required=False, default=False, action='store_true', help="create a basic `packster.json` file in the current working directory")
    parser.add_argument('--verbose', required=False, default=False, action='store_true', help="output additional log information")
    parser.add_argument('--quiet', required=False, default=False, action='store_true', help='suppress log output, except for errors')
    parser.add_argument('--version', required=False, default=False, action='store_true', help='output current version information')
    parser.add_argument('--dir', type=set_dir_path, help='specify the current working directory')
    parser.add_argument('--dist', type=set_dist_name, help='specify the dist filename')
    parser.add_argument('--package', type=set_target_package, help='specify a particular package')
    parser.add_argument('--help', action='store_true', help='show this help message and exit')
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

def create_init_file():
    """Create a basic packster.json file"""
    data = {
        "packages": {
            "my-package": {
                "dirs": ["src"],
                "files": ["*.md", "LICENSE"],
                "exclude": ["*.tmp"],
                "outName": "{PACKAGE_NAME}.{VERSION}",
                "outExt": "zip",
                "outDir": "dist",
                "version": True
            }
        }
    }
    with open('packster.json', 'w') as f:
        json.dump(data, f, indent=4)

def main():
    parse_args()

    # Show help if --help or no arguments
    import sys
    if get_arg('help'):
        print_help()
        exit()

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
        print('')
        print('Use `--help` for more information.')
        print()
        exit()

if __name__ == "__main__":
    main()
