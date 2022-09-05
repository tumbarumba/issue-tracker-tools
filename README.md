# Jira Tools

A set of command line tools for interacting with a Jira server and extracting useful information

## Installation

Setup your Python environment, cd to the base directory, and run the command:

```
pip install -r requirements.txt
```

## Configuration

The `jira` script requires at least 1 configuration file, although this can be split into multiple files, depending upon needs. These are discussed below.

### `jiraconfig.yml`

`jiraconfig.yml` contains information about the Jira server. By default, the script will look for this file at `~/jiraconfig.yml`, although this can be overriden on the command line using the `-j` or `--jira-config` options.

An example of the Jira config file:

```yaml
jira:
  url: https://url.of.jira/
```

### `projectconfig.yml`

Some of the reports use the concept of a "project", which is generally a sub-set of issue that can be selected from a top level Jira server. By default, the project configuration file is the same as the Jira configuration file (described above), although the project configuration is storied in a different top level key. To allow for the case where there are multiple concurrent projects, the project configuration file can be specified on the command line using the `-p` or `--project-config` options.

An example of the project config file:

```yaml
project:
  name: Project Name
  label: project_label
  report_dir: ~/jirareports
  milestones:
  - name: Iteration 3 Demo
    date: 2022-08-31
```

In the case where the Jira config and project config are stored in the same file, this would look like this:

```yaml
jira:
  url: https://url.of.jira/
project:
  name: Project Name
  label: project_label
  report_dir: ~/jirareports
  milestones:
  - name: Iteration 3 Demo
    date: 2022-08-31
```

### Authentication

Authentication to the Jira server is required. This is done through setting up a Personal Access Token (PAT). In Jira, navigate from your profile picture (in the top right corner), select "Personal Access Tokens", and click "Create Token".

Once you have created the token, it needs to be made accessible from the script. This is done using an environment variable called `jiraToken`.

There are 2 ways this can be done:
* Set an environment variable call `jiraToken` in your `.bashrc` file or equivalent.
* Create a file called `.env`, and store it in either the current directory, or your home directory.

The `.env` file is loaded using Python's `dotenv` module. The format looks like this:

```
jiraToken=xxxxxxxxxxxxxxxxxxxxx
```

(Of course, replace the x's with the value of your own PAT)

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
  issue            Report on issue detail.
  progress         Report on progress for a project.
  resolved         Report on recently closed issues.
  working          Report on issues currently in progress.
```

### Cumulative Flow

```
➜ jira cumulative-flow -h
Usage: jira cumulative-flow [OPTIONS]

  Creates a cumulative flow graph from the progress log.

Options:
  -o, --open-graph  Open the graph after generation
  -h, --help        Show this message and exit.
```

### Epic Summary

```
➜ jira epic-summary -h   
Usage: jira epic-summary [OPTIONS]

  Report on stories within epics.

Options:
  -s, --subject TEXT
  -h, --help          Show this message and exit.
```

### Issue Detail

```
➜ jira issue -h
Usage: jira issue-detail [OPTIONS] ISSUE_KEY

  Report on issue detail.

Options:
  -h, --help  Show this message and exit.
```

### Progress

```
➜ jira progress -h    
Usage: jira progress [OPTIONS]

  Report on progress for a project.

Options:
  -g, --graph  Generate cumulative flow graph
  -h, --help   Show this message and exit.
```

### Resolved

```
➜ jira resolved -h
Usage: jira resolved [OPTIONS]

  Report on recently closed issues.

Options:
  -d, --days INTEGER  [default: 30]
  -h, --help          Show this message and exit.
```

### Working

```
➜ jira working -h
Usage: jira working [OPTIONS]

  Report on issues currently in progress.

Options:
  -h, --help  Show this message and exit.
```