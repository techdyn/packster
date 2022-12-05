# Packster - Simple Packing Tool

A simple packing tool built in [Python](https://www.python.org/) to produce archives as defined in `packster.json`.

Working relative to the current working directory, files and folders can be defined and excluded in the `packster.json` file, and multiple zip files can be produced for things like deploying sections of projects, or for back up purposes.

This was built with 2 use cases in mind:
- Building AWS Elastic Beanstalk application zips for uploading to an environment.
- Building deployable archives for upload to multiple AWS Lambda Functions.

The `packster.json` config file can be committed to a code repository.

## Installation

1. Clone the repository

```bash
git clone https://github.com/techdyn/packster.git
cd packster
```

2. Install a symbolic link to the tool

```bash
 sudo ln -s $PWD/packster /usr/local/bin/
```

3. Test installation

```bash
/usr/local/bin/packster --version
```

## Usage

1. Create `packster.json` in the folder you wish to act as your root (usually project root, but may vary)

```bash
# create packster.json
packster --init
```

**Example**

This is an example for packing a Symfony project for upload to AWS Elastic Beanstalk.
It is assumed the `packster.json` is in the project root (eg the folder containing `/src`).

```json
{
    "packages": {
        "SymfonyProject": {
	        "outDir": "dist",
            "dirs": [
                ".ebextensions",  
                ".platform",  
                "assets",  
                "app",  
                "bin",  
                "config",  
                "migrations",  
                "public",  
                "src",  
                "templates",  
                "tests",  
                "translations"  
            ],
            "files": [
                "*"  
            ],
            "exclude": [
                "*.md",  
                "*.pdf",  
                "*.dev",  
                "*.test",  
                "*.dev-example",  
                "*.zip"  
            ]  
        }
    }
}
```

2. Run `packster` in your project root folder

```bash
packster
```

**Output** 

```
$ packster

    ____                __          __
   / __ \ ____ _ _____ / /__ _____ / /_ ___   _____
  / /_/ // __ `// ___// //_// ___// __// _ \ / ___/
 / ____// /_/ // /__ / ,<  (__  )/ /_ /  __// /
/_/     \__,_/ \___//_/|_|/____/ \__/ \___//_/  v0.1.0
                                                by TechDyn


Working in:   /path/to/current/working/directory
Processing:   SymfonyProject
Output to:    dist/SymfonyProject_20221204052756.zip
```


### Options

- `--init`
	Create a basic `packster.json` file in the current working directory.

- `--dir DIR`
	By default, Packster will search for `packster.json` in the current working directory, this option will change the working directory for the execution of the tool, for instances where the packing root is nested under your project root.

- `--package PACKAGE`
	Specify a particular package.

- `--verbose`
	Output additional log information.

- `--quiet` 
	Suppress log output, except for errors.

- `--version`
	Output current version information.

### JSON: packster.json

- packages *(root)*
	- `outDir` ***(optional)*** 
		Target output directory relative to the current working directory.
		(**default**: `dist`)

	- `dirs` *(array)*
		Directories to include, relative to the current working directory.
		*Will include all files within directories, filtered by `exclude`.*

	- `files` *(array)*
		Files to include, relative to the current working directory.
		_Supports `*` wildcards._
		Files are filtered by `exclude`.

		`["*"]` is not recursive, and will only package the **files** in the working directory.

	- `exclude` *(array)*
		Exclude file patterns.
		_Supports `*` wildcards._