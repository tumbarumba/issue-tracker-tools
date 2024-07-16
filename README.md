# Issue Tracker Tools

A set of command line tools for interacting with an issue tracker (such as Jira) and extracting useful information.

The tools are:
* `it`: issue tracker reports and information
* `cfd`: cumulative flow diagram tool
* `git-tickets`: extract issue keys from git commit messages

These tools are described in more detail below.

## Installation

Clone the repository:

```commandline
git clone https://github.com/tumbarumba/issue-tracker-tools.git
cd issue-tracker-tools
```


Setup your Python environment (a virtualenv is preferred). For example, the standard `venv`
module can be set up like this:

```commandline
# Create a new virtual environment under the `.venv` directory
python -m venv .venv
# Activate the virtual environment for the current shell
. .venv/bin/activate
```

Install the dependencies:

```
pip install -e '.[dev,test]'
```

Once installed locally, you can build a wheel for downstream distribution:

```
hatch build
```

This will create a wheel file in the `dist` directory. This wheel can be
installed in other environments using the normal installation:

```
pip install $(find dist -name "*.whl")
```

## Configuration

The `it` and `cfd` scripts requires a configuration file, called `issuetracker.yml` by default.

### `issuetracker.yml`

The scripts will look for this file at `$HOME/issuetracker.yml` by default, although this can be overriden on the command line using the `-c` or `--config` option.

An example of the config file:

```yaml
provider: jira
report_dir: ~/jirareports
jira:
  url: https://url.of.jira/
  project_keys:
  - EJP1
  - EJP2
```

In this example:
* The back end issue tracker is "`jira`"
* The top level directory for report files will be "`~/jirareports`"
* The top level URL of the Jira server is "`https://url.of.jira`"
* The reports will be limited to just the Jira projects with project keys "`EJP1`" and "`EJP2`"

### Jira Authentication

Authentication to the Jira server is required. `issue-tracker-tools` supports two
alternative methods of authentication:
* A Personal Access Token (PAT). This method is available on on-prem instances of Jira
* An API key. This authentication method is available on Jira cloud instances.

Only one authentication method should be used. See details below on how to do this.

The scripts will look for authentication values in the environment. This is done using an environment variable called `jiraToken`.

There are 2 ways this can be done:
* Set the environment variables in your `.bashrc`, `.zshrc`, or equivalent.
* Create a file called `.env`, and store it in either the current directory, or your home directory. This method is preferred, as you have better control over the access of the authentication secrets.

The `.env` file is loaded using Python's `dotenv` module. See below for examples.

#### Personal Access Token (PAT)

To create a PAT, navigate from your profile picture in Jira (in the top right corner), select "Personal Access Tokens", and click "Create Token".
Save the value of the token in an environment variable called `jiraToken`. The `.env` file will look similar to this:

```properties
jiraToken=xxxxxxxxxxxxxxxxxxxxx
```

(Of course, replace the x's with the value of your own PAT)

#### API Token

Instructions for creating API Tokens are here:
* [https://support.atlassian.com/atlassian-account/docs/manage-api-tokens-for-your-atlassian-account/](https://support.atlassian.com/atlassian-account/docs/manage-api-tokens-for-your-atlassian-account/)

Both the user and API token must be stored in the environment in the variables `jiraUser` and `jiraApiToken` respectively. The `.env` file will look similar to this:

```properties
jiraUser=xxxxx
jiraApiToken=yyyyy
```

(Of course, replace the x's and y's with your own values)

## Usage

### Issue Tracker

```
➜ it -h
Usage: it [OPTIONS] COMMAND [ARGS]...

  Issue tracker reports and information

Options:
  -v, --verbose
  -c, --config PATH  Location of config file (default: ~/issuetracker.yml)
  -h, --help         Show this message and exit.

Commands:
  epic-summary  Report on stories within epics.
  in-progress   Report on issues currently in progress.
  issue         Report on issue detail.
  jql-label     Generate jql to search issues for epics with a given label
  project       Report on progress for a project.
  release       Describes a list of tickets as release notes
  resolved      Report on recently closed issues.
```

See below for more details on the issue tracker subcommands.

### Issue Tracker: Epic Summary

```
➜ it epic-summary -h
Usage: it epic-summary [OPTIONS]

  Report on stories within epics.

Options:
  -s, --subject TEXT
  -h, --help          Show this message and exit.
```

### Issue Tracker: In Progress

```
➜ it in-progress -h
Usage: it in-progress [OPTIONS]

  Report on issues currently in progress.

Options:
  -g, --group  Group issues by epic
  -h, --help   Show this message and exit.

```

### Issue Tracker: Issue Detail

```
➜ it issue -h
Usage: it issue [OPTIONS] [ISSUE_KEYS]...

  Report on issue detail.

Options:
  -o, --open                     Open issue in a web browser
  -f, --update-fix-version TEXT  Update issue with specified fix version
  -h, --help                     Show this message and exit.
```

If no options are specific, this report will show detailed information on a issue.

If the `-f` option is specified, each issue will be updated instead, and message printed to show that the issue was
updated.

### Issue Tracker: Project

```
➜ it project -h
Usage: it project [OPTIONS] PROJECT

  Report on progress for a project.

Options:
  -h, --help  Show this message and exit.
```

### Issue Tracker: Release Notes

```
➜ it release -h
Usage: it release [OPTIONS] [ISSUE_KEYS]...

  Describes a list of tickets as release notes

Options:
  -f, --fix-version TEXT  Include all issues with this fix version
  -t, --no-tasks          Exclude tasks
  -m, --markdown          Output report as markdown
  -h, --help              Show this message and exit.
```

The issue keys can be specified directly on the command line. Alternatively, the `-f` option can be specified, and
the Jira will be queried to find all issue keys with that specific fix version.

### Issue Tracker: Resolved

```
➜ it resolved -h
Usage: it resolved [OPTIONS]

  Report on recently closed issues.

Options:
  -d, --days INTEGER     include issues resovled this many days prior to today
  -f, --from [%Y-%m-%d]  include resolved issues from this date onwards
  -t, --to [%Y-%m-%d]    include issues resolved before this date
  -h, --help             Show this message and exit.
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

### Cumulative Flow Diagram

```
➜ cfd -h
Usage: cfd [OPTIONS] PROJECT

  Create a cumulative flow diagram for a given project

  Requires a project progress file (progress.csv) in the project directory.
  This is normally generated by the `it project` command

Options:
  -v, --verbose
  -c, --config PATH
  -o, --open-graph        Open the graph after generation
  -t, --today [%Y-%m-%d]  Override today's date
  -h, --help              Show this message and exit.
```