import os
import sys
from dotenv import dotenv_values
from jira import JIRA

this = sys.modules[__name__]

this._EPIC_LINK_FIELD_ = "customfield_10101"
this._EPIC_STATUS_FIELD_ = "customfield_10102"
this._verbose_ = False

def build_jira(verbose, jira_config):
    this._verbose_ = verbose
    token = _load_jira_token()
    jira = JIRA(token_auth=token, options={'server': jira_config.url})
    _init_custom_fields(jira)

    return jira

def _load_jira_token():
    env_values = {
        **dotenv_values("~/.env"),                      # Load env file from current directory
        **dotenv_values(os.path.expanduser("~/.env")),  # Override with env file from home directory
        **os.environ                                    # Override with environment variables
    }
    return env_values.get('jiraToken')

def _init_custom_fields(jira):
    all_fields = jira.fields()

    epic_link_field = next(filter(lambda f: f["name"] == "Epic Link", all_fields))
    this._EPIC_LINK_FIELD_ = epic_link_field["id"]
    if this._verbose_: print(f"Setting epic link field to {this._EPIC_LINK_FIELD_}")

    epic_status_field = next(filter(lambda f: f["name"] == "Epic Status", all_fields))
    this._EPIC_STATUS_FIELD_ = epic_status_field["id"]
    if this._verbose_: print(f"Setting epic status field to {this._EPIC_STATUS_FIELD_}")

class JiraQueries:
    def __init__(self,jira):
        self.jira = jira
        
    def search_for_issues(self, jql):
        if this._verbose_: print(f"search_for_issues jql: {jql}")
        return self.jira.search_issues(jql,expand="changelog", maxResults=1000)

    def get_project_epics(self, project_label):
        jql = f"project = DS AND issuetype = Epic and labels = {project_label} ORDER BY rank"
        return(self.search_for_issues(jql))

    def get_single_issue(self,issue_key):
        jql = f"key={issue_key}"
        return(self.search_for_issues(jql))

    def get_all_open_epics(self):
        jql = "project = DS and issueType = Epic and 'Epic Status' != Done order by rank"
        return(self.search_for_issues(jql))
    
    def get_resolved_issues(self, days):
        jql = f"project = DS and 'Epic Link' is not null and status in ('Done', 'Awaiting Demo') and resolved >= startOfDay(-{days}) order by resolved",
        return(self.search_for_issues(jql))

    def get_epic_stories(self, epic_key):
        #repeat of epic data class method
        jql = f"'Epic Link' = {epic_key} order by Status"
        return self.search_for_issues(jql)
