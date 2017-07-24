# zabbix-jira
zabbix-jira is python module that allows you to create tasks in Jira with grafs by the trigger from Zabbix.

## Requirements: 
* python >= 2.7
* python libs: requests, jira

## Installation:
1. Copy this repo to your zabbix-server:
`git clone https://github.com/OSidorenkov/zabbix-jira.git` 
2. Copy `jirabix.py` to your Zabbix `AlertScriptsPath` directory (see your zabbix_server.conf) 
3. Create and configure `config.py` near `jirabix.py`. You can take as an example `config.py.example` from repo.  
4. Install python libs: `pip install requests jira`

## Configuration:
* Create new media type in Zabbix:  
<img width="762" alt="2017-06-02 11 33 21" src="https://cloud.githubusercontent.com/assets/12871885/26717811/6dd92522-4787-11e7-99fd-4e1e622b8c51.png">

If you use Zabbix 3.0 and higher, add this parameters:
```
{ALERT.SENDTO}
{ALERT.SUBJECT}
{ALERT.MESSAGE}
```

* Add this media to your read user in Zabbix
<img width="580" alt="2017-06-02 11 40 19" src="https://cloud.githubusercontent.com/assets/12871885/26718054/552e3656-4788-11e7-8807-efb9c7118597.png">

Add in "Send to" field jira username (see the profile user in Jira)

* Configure your Actions:
<img width="901" alt="2017-06-02 11 48 12" src="https://cloud.githubusercontent.com/assets/12871885/26718404/95c82900-4789-11e7-914b-a3b0465db11a.png">

Example message:  
```
Last value:{ITEM.VALUE1} ({TIME})
zbx;graphs
zbx;graphs_period=1800
zbx;itemid:{ITEM.ID1}
zbx;triggerid:{TRIGGER.ID}
zbx;title:{HOST.HOST} - {TRIGGER.NAME}
zbx;priority:{TRIGGER.SEVERITY}
Server: {HOSTNAME} ({HOST.IP})

Desc:
{TRIGGER.DESCRIPTION}
```
<img width="778" alt="2017-06-02 11 48 38" src="https://cloud.githubusercontent.com/assets/12871885/26718489/dd90aa00-4789-11e7-9121-51a75a042fd7.png">

Example recovery message:
```
Server: {HOSTNAME} ({HOST.IP})
zbx;triggerid:{TRIGGER.ID}
zbx;ok:1

Description:
Problem resolved!

Time of resolved problem: {DATE} {TIME}
```

### Annotations
```
zbx;graphs -- enables attached graphs
zbx;graphs_period=10800 -- set graphs period (default - 3600 seconds)
zbx;graphs_width=700 -- set graphs width (default - 900px)
zbx;graphs_height=300 -- set graphs height (default - 300px)
zbx;itemid:{ITEM.ID1} -- define itemid (from trigger) for attach
zbx;title:{HOST.HOST} - {TRIGGER.NAME} -- graph title
zbx;triggerid:{TRIGGER.ID} -- define triggerid to link problem and recovery of event
zbx;priority:{TRIGGER.SEVERITY} -- set priority task like as priority of trigger from Zabbix
zbx;ok:1 -- use this parameter only in RECOVERY message, if you don't want create a new task about recovery in Jira
```

You can use Jira format text in your actions: [https://jira.atlassian.com/secure/WikiRendererHelpAction.jspa?section=all](https://jira.atlassian.com/secure/WikiRendererHelpAction.jspa?section=all)

### Test script
You can use the following command to create a ticket in Jira from your command line:  
`python jirabix.py "jira_username" "ticket_subject" "ticket_desc"` where
* jira_username - username from Jira user profile 
* For `ticket_subject` and `ticket_desc` you may use "test" "test"
  * If you want to test real text from zabbix action message copy `test/entry.txt` from repo and change the contents of the file on your real data and change `jirabix.py` like this:  
  ![2017-06-02 12 18 41](https://cloud.githubusercontent.com/assets/12871885/26719581/c6ca9fac-478d-11e7-838c-362260f570d0.png)  
  And run:  
  `python jirabix.py "jira_username" "ticket_subject`
  
## Result
* See how creates the ticket with graf from Zabbix:  

![2017-06-02 12_31_18](https://cloud.githubusercontent.com/assets/12871885/26720057/70045c4c-478f-11e7-96ff-75efbaeabbae.gif)  


* When problem is going to OK, script convert the ticket to "Done" status with comment from zabbix recovery message:  

![2017-06-02 12_44_41](https://cloud.githubusercontent.com/assets/12871885/26720515/47da1d04-4791-11e7-969d-573eedd83bcf.gif)
