from jira import JIRA
import config

# jira_server = {'server': config.jira_server}
# jira = JIRA(options=jira_server, basic_auth=(config.jira_user, config.jira_pass))
# issue = jira.issue('ZBX-2')
# transitions = jira.transitions(issue)
# [(t['id'], t['name']) for t in transitions]


def close_issue(issue, status):
    jira_server = {'server': config.jira_server}
    jira = JIRA(options=jira_server, basic_auth=(config.jira_user, config.jira_pass))
    jira.transition_issue(issue, status)

close_issue('ZBX-2', '41')  # ZBX-2: Project key, 41: transition id for closing issue
