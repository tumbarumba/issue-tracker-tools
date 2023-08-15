# Jira Tools

A set of command line tools for interacting with a Jira server and extracting useful information

## Installation

Setup your Python environment, cd to the base directory, and run the command:

```
pip install -r requirements.txt
```

## Configuration

The `jira` script requires a configuration file called `issuetracker.yml` by default.

### `issuetracker.yml`

By default, the script will look for this file at `$HOME/issuetracker.yml`, although this can be overriden on the command line using the `-c` or `--config` option.

An example of the Jira config file:

```yaml
provider: jira
report_dir: ~/jirareports
jira:
  url: https://url.of.jira/
projects:
  - name: Project Name
    key: project_label
    milestones:
      - name: Iteration 3 Demo
        date: 2022-08-31
  - name: Another Project
    key: project_label_2
    milestones:
      - name: Project 2 Checkpoint
        date: 2023-09-30
      - name: Project 2 Delivery
        date: 2023-10-31
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

### Git Tickets

```
Usage: git-tickets <revision-range>

  Report on Jira tickets that can be seen in git commit messages
```

This is a small bash script that under the covers runs `git log` against a revision range, and matches strings that
looks like Jira tickets. For example:

`git-tickets 0.29.0..0.30.0` will show all tickets from commits after the `0.29.0` tag, and before and including the
`0.30.0` tag. This can be used to find all Jira issues that are part of a release, and then updating the issues in
Jira to specify the fix version. For example:

`git-tickets 0.29.0..0.30.0 | xargs jira issue --update-fix-version 0.30.0`

For more information about how to specify git revision ranges, see
[https://www.git-scm.com/docs/gitrevisions#_specifying_ranges](https://www.git-scm.com/docs/gitrevisions#_specifying_ranges)

### Issue Detail

```
Usage: jira issue [OPTIONS] [ISSUE_KEYS]...

  Report on issue detail.

Options:
  -o, --open                     Open issue in a web browser
  -f, --update-fix-version TEXT  Update issue with specified fix version
  -h, --help                     Show this message and exit.
```

If no options are specific, this report will show detailed information on a issue.

If the `-f` option is specified, each issue will be updated instead, and message printed to show that the issue was
updated.

### Progress

```
➜ jira progress -h    
Usage: jira progress [OPTIONS]

  Report on progress for a project.

Options:
  -g, --graph  Generate cumulative flow graph
  -h, --help   Show this message and exit.
```

### Release Notes

```
Usage: jira release [OPTIONS] [ISSUE_KEYS]...

  Describes a list of tickets as release notes

Options:
  -f, --fix-version TEXT  Include all issues with this fix version
  -t, --no-tasks          Exclude tasks
  -h, --help              Show this message and exit.
```

The issue keys can be specified directly on the command line. Alternatively, the `-f` option can be specified, and
the Jira will be queried to find all issue keys with that specific fix version.

### Resolved

```
Usage: jira resolved [OPTIONS]

  Report on recently closed issues.

Options:
  -d, --days INTEGER     include issues resovled this many days prior to today
  -f, --from [%Y-%m-%d]  include resolved issues from this date onwards
  -t, --to [%Y-%m-%d]    include issues resolved before this date
  -h, --help             Show this message and exit.
```

### Working

```
➜ jira working -h
Usage: jira working [OPTIONS]

  Report on issues currently in progress.

Options:
  -g, --group  Group issues by epic
  -h, --help   Show this message and exit.
```