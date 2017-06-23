#!/usr/bin/env python
# coding: utf-8

from jira import JIRA
import config
import sys
import requests
import re
import os
import sqlite3

# PARAMS RECEIVED FROM ZABBIX SERVER:
# sys.argv[1] = TO
# sys.argv[2] = SUBJECT
# sys.argv[3] = BODY


def jira_login():
    jira_server = {'server': config.jira_server}
    return JIRA(options=jira_server, basic_auth=(config.jira_user, config.jira_pass))


def create_issue(to, tittle, body, project, issuetype, priority):
    jira = jira_login()
    issue_params = {
            'project': {'key': project},
            'summary': tittle,
            'description': body,
            'issuetype': {'name': issuetype},
            'assignee': {'name': to},
            'priority': {'id': priority}
    }
    return jira.create_issue(fields=issue_params).key


def add_attachment(issue, attachment):
    jira = jira_login()
    jira.add_attachment(issue, attachment)


def close_issue(issue, status):
    jira = jira_login()
    jira.transition_issue(issue, status)


def add_comment(issue, comment):
    jira = jira_login()
    jira.add_comment(issue, comment)


class ZabbixAPI:
    def __init__(self, server, username, password):
        self.debug = False
        self.server = server
        self.username = username
        self.password = password
        self.proxies = {}
        self.verify = True
        self.cookie = None

    def login(self):

        data_api = {"name": self.username, "password": self.password, "enter": "Sign in"}
        req_cookie = requests.post(self.server + "/", data=data_api, proxies=self.proxies, verify=self.verify)
        cookie = req_cookie.cookies
        if len(req_cookie.history) > 1 and req_cookie.history[0].status_code == 302:
            print_message("probably the server in your config file has not full URL (for example "
                          "'{0}' instead of '{1}')".format(self.server, self.server + "/zabbix"))
        if not cookie:
            print_message("authorization has failed, url: {0}".format(self.server + "/"))
            cookie = None

        self.cookie = cookie

    def graph_get(self, itemid, period, title, width, height, tmp_dir):
        file_img = tmp_dir + "/{0}.png".format(itemid)

        title = requests.utils.quote(title)

        zbx_img_url = self.server + "/chart3.php?period={1}&name={2}" \
                                    "&width={3}&height={4}&graphtype=0&legend=1" \
                                    "&items[0][itemid]={0}&items[0][sortorder]=0" \
                                    "&items[0][drawtype]=5&items[0][color]=00CC00".format(itemid, period, title,
                                                                                          width, height)
        if self.debug:
            print_message(zbx_img_url)
        res = requests.get(zbx_img_url, cookies=self.cookie, proxies=self.proxies, verify=self.verify, stream=True)
        res_code = res.status_code
        if res_code == 404:
            print_message("can't get image from '{0}'".format(zbx_img_url))
            return False
        res_img = res.content
        with open(file_img, 'wb') as fp:
            fp.write(res_img)
        return file_img


def print_message(string):
    string = str(string) + "\n"
    filename = sys.argv[0].split("/")[-1]
    sys.stderr.write(filename + ": " + string)


def main():
    if not os.path.exists(config.zbx_tmp_dir):
        os.makedirs(config.zbx_tmp_dir)
    tmp_dir = config.zbx_tmp_dir

    # zbx_body = open('entry.txt', 'r').read()
    zbx_body = sys.argv[3]

    zbx = ZabbixAPI(server=config.zbx_server, username=config.zbx_api_user,
                    password=config.zbx_api_pass)

    if config.proxy_to_zbx:
        zbx.proxies = {
            "http": "http://{0}/".format(config.proxy_to_zbx),
            "https": "https://{0}/".format(config.proxy_to_zbx)
            }

    try:
        zbx_api_verify = config.zbx_api_verify
        zbx.verify = zbx_api_verify
    except:
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
    }

    trigger_desc = {
        "not_classified": {"name": "Not classified", "id": "5"},
        "information": {"name": "Information", "id": "5"},
        "warning": {"name": "Warning", "id": "4"},
        "average": {"name": "Average", "id": "3"},
        "high": {"name": "High", "id": "2"},
        "disaster": {"name": "Disaster", "id": "1"},
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

    trigger_ok = int(settings['zbx_ok'])
    trigger_id = int(settings['zbx_triggerid'])

    # print(os.path.join(os.path.dirname(__file__), 'test.db'))
    conn = sqlite3.connect(os.path.join(os.path.dirname(__file__), 'jirabix.db'))
    c = conn.cursor()
    c.execute('''CREATE TABLE if not exists events
             (trigger_id integer, issue_key text)''')
    conn.commit()
    c.execute('SELECT issue_key FROM events WHERE trigger_id=?', (trigger_id,))
    result = c.fetchall()
    # print(result)
    priority = "5"
    if not result and trigger_ok == 0:
        for i in trigger_desc.values():
            if i['name'] == settings['zbx_priority']:
                priority = i.get('id')

        issue_key = create_issue(sys.argv[1], sys.argv[2], '\n'.join(zbx_body_text), config.jira_project,
                                 config.jira_issue_type, priority)
        zbx.login()
        if not zbx.cookie:
            print_message("Login to Zabbix web UI has failed, check manually...")
        else:
            zbx_file_img = zbx.graph_get(settings["zbx_itemid"], settings["zbx_image_period"],
                                           settings["zbx_title"], settings["zbx_image_width"],
                                           settings["zbx_image_height"], tmp_dir)
            if not zbx_file_img:
                print_message("Can't get image, check URL manually")
            elif isinstance(zbx_file_img, str):
                add_attachment(issue_key, zbx_file_img)
                os.remove(zbx_file_img)
        c.execute("INSERT INTO events VALUES (?, ?);", (trigger_id, issue_key))
        conn.commit()
    elif not result and trigger_ok == 1:
        pass
    else:
        issue_key = result[0][0]
        add_comment(issue_key, '\n'.join(zbx_body_text))
        close_issue(issue_key, config.jira_close_status)
        c.execute('DELETE FROM events WHERE trigger_id=?', (trigger_id,))
        conn.commit()
        conn.close()


if __name__ == '__main__':
    main()
