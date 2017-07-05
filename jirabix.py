#!/usr/bin/python
# coding: utf-8

from jira import JIRA
import config
import sys
import requests
import re
import os
import json
import logging

# PARAMS RECEIVED FROM ZABBIX SERVER:
# sys.argv[1] = TO
# sys.argv[2] = SUBJECT
# sys.argv[3] = BODY

logging.basicConfig(filename='/tmp/jirabix.log', level=logging.ERROR,
                    format='%(asctime)s %(levelname)s %(name)s %(message)s')
logger=logging.getLogger(__name__)


def jira_login():
    jira_server = {'server': config.jira_server}
    proxies = {}
    try:
        proxies = {'http': config.proxy_to_jira, 'https': config.proxy_to_jira}
    except AttributeError:
        pass
    return JIRA(options=jira_server, basic_auth=(config.jira_user, config.jira_pass), proxies=proxies)


def create_issue(jira, to, tittle, body, project, issuetype):
    logger.info("creating jira ticket")
    issue_params = {
            'project': {'key': project},
            'summary': tittle,
            'description': body,
            'issuetype': {'name': issuetype},
            'duedate' : "2017-12-12",
            'labels': ["Monitoring"],
            'customfield_11100' : {"value":"DaaS-STG"}
    }
    return jira.create_issue(fields=issue_params).key


def add_attachment(jira, issue, attachment):
    logger.info("adding attachment")
    jira.add_attachment(issue, attachment)


def close_issue(jira, issue, status):
    logger.info("closing issue")
    jira.transition_issue(issue, status)


def add_comment(jira, issue, comment):
    jira.add_comment(issue, comment)


def msg_teams(jira, subject, trigger_id, item_id, priority_name, host, zbx_graph=None):
    logger.info("messaging teams")
    jira_url = config.jira_server + '/browse/' + jira
    zabbix_trigger_url = config.zbx_server + "/zabbix.php?action=problem.view&filter_triggerids%5B%5D=" + str(trigger_id) + "&filter_set=1"
    zabbix_history_url = config.zbx_server + "/history.php?action=showgraph&itemids%5B%5D=" + str(item_id)

    theme_color = None
    trigger_status = subject.split(":")[0]
    if "OK" in trigger_status:
        theme_color = '48d97a'
    elif "Information" in priority_name:
        theme_color = '5f7fff'
    elif "Warning" in priority_name:
        theme_color = 'ffbf3e'
    elif "Average" in priority_name:
        theme_color ='f88b3f'
    elif "High" in priority_name:
        theme_color ='dc5c41'
    elif "Disaster" in priority_name:
        theme_color = 'd53e42'

    proxies = {}
    try:
        proxies = {
            "http": "http://{0}/".format(config.proxy_to_teams),
            "https": "https://{0}/".format(config.proxy_to_teams)
            }
    except AttributeError:
        pass

    payload = {
          '@type': 'MessageCard',
          '@context': 'http://schema.org/extensions',
          'title': subject,
          'text': "New incident: " + jira,
          'themeColor': theme_color,
          "sections": [
              {
                  "activityTitle": "Incident notification for " + str(trigger_id),
                  "activityImage": "http://www.zabbix.com/img/newsletter/2016/icons/share-logo-z.png",
                  "facts": [
                      {
                          "name": "Severity",
                          "value": priority_name
                      },
                      {
                          "name": "Host",
                          "value": host
                      }
                  ]
              }
          ],
          'potentialAction': [
              {
                  '@type': 'OpenUri',
                  'name': 'Open jira',
                  'targets': [
                      { 'os': 'default', 'uri': jira_url }
                  ]
              },
              {
                  '@type': 'OpenUri',
                  'name': 'Zabbix trigger',
                  'targets': [
                      { 'os': 'default', 'uri': zabbix_trigger_url }
                  ]
              },
              {
                  '@type': 'OpenUri',
                  'name': 'Zabbix item history',
                  'targets': [
                      { 'os': 'default', 'uri': zabbix_history_url }
                  ]
              }
          ]

              }
    if zbx_graph:
        payload['sections'].append({"images": [{ "image":zbx_graph}]})
    headers = {'content-type': 'application/json'}
    response = requests.post(config.o365_webhook, data=json.dumps(payload), headers=headers, proxies=proxies)
    return response


class ZabbixAPI:
    def __init__(self, server, username, password):
        self.server = server
        self.username = username
        self.password = password
        self.proxies = {}
        self.verify = True
        self.cookie = None

    def login(self):
        data_api = {"name": self.username, "password": self.password, "enter": "Sign in"}
        r = requests.post(self.server + "/", data=data_api, proxies=self.proxies, verify=self.verify)
        if r.status_code != 200:
            logger.error("probably the server in your config file has not full URL (for example "
                          "'{0}' instead of '{1}')".format(self.server, self.server + "/zabbix"))
            logger.error(r.status_code)
            logger.error(r.text)
        else:
            if r.cookies['zbx_sessionid']:
                self.cookie = r.cookies

    def graph_get(self, itemid, period, title, width, height, tmp_dir):
        file_img = tmp_dir + "/{0}.png".format(itemid)

        zbx_img_url = self.server + "/chart3.php?period={1}" \
                                    "&width={2}&height={3}&graphtype=0&legend=1" \
                                    "&items[0][itemid]={0}&items[0][sortorder]=0" \
                                    "&items[0][drawtype]=5&items[0][color]=00CC00".format(itemid, period, width, height)
        res = requests.get(zbx_img_url, cookies=self.cookie, proxies=self.proxies, verify=self.verify, stream=True)
        res_code = res.status_code
        if res_code == 404:
            logger.error("can't get image from '{0}'".format(zbx_img_url))
            return False
        res_img = res.content

        try:
            fp = open(file_img, 'wb')
            try:
                fp.write(res_img)
            finally:
              fp.close()
        except IOError:
            logger.error("Error writing graph image")
            return zbx_img_url, None

        return zbx_img_url, file_img


def main():
    if not os.path.exists(config.zbx_tmp_dir):
        os.makedirs(config.zbx_tmp_dir)
    tmp_dir = config.zbx_tmp_dir

    trigger_status = sys.argv[2].split(":")[0]
    zbx_body = sys.argv[3]

    zbx = ZabbixAPI(server=config.zbx_server, username=config.zbx_api_user,
                    password=config.zbx_api_pass)

    try:
        zbx.proxies = {
            "http": "http://{0}/".format(config.proxy_to_zbx),
            "https": "https://{0}/".format(config.proxy_to_zbx)
            }
    except AttributeError:
        pass

    try:
        zbx_api_verify = config.zbx_api_verify
        zbx.verify = zbx_api_verify
    except AttributeError:
        pass

    zbx_body = zbx_body.splitlines()
    zbx_body_text = []

    settings = {
        "zbx_itemid": "0",  # itemid for graph
        "zbx_triggerid": "0",  # uniqe trigger id of event
        "zbx_ok": "0",  # flag of resolve problem, 0 - no, 1 - yes
        "zbx_priority": None,  # zabbix trigger priority
        "zbx_title": None,  # title for graph
        "zbx_image_period": "3600",
        "zbx_image_width": "900",
        "zbx_image_height": "200",
    }
    settings_description = {
        "itemid": {"name": "zbx_itemid", "type": "int"},
        "triggerid": {"name": "zbx_triggerid", "type": "int"},
        "ok": {"name": "zbx_ok", "type": "int"},
        "priority": {"name": "zbx_priority", "type": "str"},
        "title": {"name": "zbx_title", "type": "str"},
        "graphs_period": {"name": "zbx_image_period", "type": "int"},
        "graphs_width": {"name": "zbx_image_width", "type": "int"},
        "graphs_height": {"name": "zbx_image_height", "type": "int"},
        "graphs": {"name": "tg_method_image", "type": "bool"},
        "eventid": {"name": "zbx_eventid", "type": "int"},
    }

    for line in zbx_body:
        if line.find(config.zbx_prefix) > -1:
            setting = re.split("[\s\:\=]+", line, maxsplit=1)
            key = setting[0].replace(config.zbx_prefix + ";", "")
            if len(setting) > 1 and len(setting[1]) > 0:
                value = setting[1]
            else:
                value = True
            if key in settings_description:
                settings[settings_description[key]["name"]] = value
        else:
            zbx_body_text.append(line)

    event_id = settings['zbx_eventid']
    zbx_body_text.append('eventid:{0}'.format(event_id))

    trigger_id = int(settings['zbx_triggerid'])
    if settings['zbx_title']:
        host = settings['zbx_title'].split(" ")[0]

    # Search for any existing non-closed ticket with matching eventid
    j = jira_login()
    tickets = j.search_issues('project = OPS AND status != closed AND labels = "Monitoring" AND text ~ "eventid:{0}"'.format(event_id))


    # Take action on new problem
    if not tickets and trigger_status == "PROBLEM":
        zbx_graph_url = None
        issue_key = create_issue(j, sys.argv[1], sys.argv[2], '\n'.join(zbx_body_text), config.jira_project,
                                 config.jira_issue_type)
        zbx.login()
        if not zbx.cookie:
            logger.error("Login to Zabbix web UI has failed, check manually...")
        else:
            zbx_graph_url, zbx_file_img = zbx.graph_get(settings["zbx_itemid"], settings["zbx_image_period"],
                                           settings["zbx_title"], settings["zbx_image_width"],
                                           settings["zbx_image_height"], tmp_dir)
            logger.info('Got graph url: {0}'.format(zbx_graph_url))
            logger.info('Got graph img: {0}'.format(zbx_file_img))
            if not zbx_file_img:
                logger.error("Can't get image, check URL manually")
            elif isinstance(zbx_file_img, str):
                add_attachment(j, issue_key, zbx_file_img)
                os.remove(zbx_file_img)
        if config.o365_webhook:
            teams_response = msg_teams(issue_key, sys.argv[2], trigger_id, settings['zbx_itemid'], settings['zbx_priority'], host, zbx_graph=zbx_graph_url)

    # Close open ticket
    if tickets and trigger_status == "OK":
        issue_key = tickets[0]
        add_comment(j, issue_key, '\n'.join(zbx_body_text))
        close_issue(j, issue_key, config.jira_close_status)


if __name__ == '__main__':
    main()
