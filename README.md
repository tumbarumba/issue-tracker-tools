# Jira Tools

A set of command line tools for interacting with a Jira server and extracting useful information

## Installation

Setup your Python environment, cd to the base directory, and run the command:

```
pip install -r requirements.txt
```

## Configuration

Before starting, access to the Jira server is required. This is done through setting up a Personal Access Token (PAT). In Jira, navigate from your profile picture (in the top right corner), select "Personal Access Tokens", and click "Create Token".

The token needs to be stored in a file called `~/.env`, as follows:

```
jiraToken=xxxxxxxxxxxxxxxxxxxxx
```

(Of course, replace the x's with the value of your own PAT)

The jira tool requires at least one configuration file. The default location for the file is `~/jiraconfig.yml`, although this can
be changed using the `--jira-config` command line option.

Look at [example/jiraconfig.yml](example/jiraconfig.yml) for an example of what this file looks like. The `url` value
will need to be changed to match your environment.

In addition to the jira configuration file, there can also be a separate project configuration file. Look at
[example/projectconfig.yml](example/projectconfig.yml) for an example of a project configuration.

By default, the project configuration file will be the same as the jira configuration file, although this can be changed
using the `--project-config` command line option.

## Usage

```
➜ jira -h
Usage: jira [OPTIONS] COMMAND [ARGS]...

Options:
  -v, --verbose
  -j, --jira-config PATH
  -p, --project-config PATH
  -h, --help                 Show this message and exit.

Commands:
  cumulative-flow  Creates a cumulative flow graph from the progress log.
  epic-summary     Report on stories within epics.
  issue-detail     Report on issue detail.
  progress         Report on progress for a project.
  resolved         Report on recently closed issues.
```
