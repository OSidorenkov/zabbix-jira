from jira import JIRA
import config
import os


def create_issue(to, tittle, body):
    jira_server = {'server': config.jira_server}
    jira = JIRA(options=jira_server, basic_auth=(config.jira_user, config.jira_pass))
    issue_params = {
            'project': {'key': 'HTE'},
            'summary': tittle,
            'description': body,
            'issuetype': {'name': 'Error'},
            'assignee': {'name': to},
    }
    return jira.create_issue(fields=issue_params).key


def add_attachment(issue, attachment):
    jira_server = {'server': config.jira_server}
    jira = JIRA(options=jira_server, basic_auth=(config.jira_user, config.jira_pass))
    jira.add_attachment(issue=issue, attachment=attachment)


def main():
    issue_key = create_issue("JiraUser", "TestIssuePython", "Just Text")
    print(issue_key)
    add_attachment(issue_key, os.path.join(os.path.dirname(__file__), 'crit.jpeg'))

if __name__ == '__main__':
    main()
