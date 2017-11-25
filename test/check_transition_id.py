from jira import JIRA
import config


def transit_id():
    jira_server = {'server': config.jira_server}
    jira = JIRA(options=jira_server, basic_auth=(config.jira_user, config.jira_pass))
    issue = jira.issue(config.jira_project + '-1')
    transitions = jira.transitions(issue)
    for t in transitions:
        if t['name'] == config.jira_transition:
            return t['id']

jid = transit_id()
print(jid)
