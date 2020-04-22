<!-- markdown-toc start - Don't edit this section. Run M-x markdown-toc-generate-toc again -->
**table of contents**

- [overview](#overview)
- [usage](#usage)
    - [local config files](#local-config-files)
    - [logging into a router](#logging-into-a-router)
- [installation](#installation)
- [setup](#setup)
- [CSV contents](#csv-contents)

<!-- markdown-toc end -->


# overview
`check-config.py` will parse a configuration (locally or on a router) and generate a list of the commands which are currently in use that will be deprecated in the 4.23 release.  

this script can be used to do a batch analysis of configurations or (if eapi is enabled) log into a device and provide a report on deprecated commands based on the running configuration.

# usage

``` text
usage: check-config.py [-h] [-s] [-v] [-t] -c CSV_FILE [-f CONFIG_FILE]
                       [-a CREDENTIALS_FILE] [-r ROUTER] [-u API_USERNAME]
                       [-p API_PASSWORD] [-e ENABLE_PASSWORD] [--nossl]

mandatory arguments:

  you must provide either a router configuration file (-f) or a router
  (-r) with the necessary credentials (see: credentials).  if your
  configuration file does not have login information, you will need to
  provide credentials on the commandline using the -u and the -p
  arguments.

arguments:

-h help

-c CSV_FILE - pointer to the CSV file with the CLI change information

-f CONFIG_FILE - pointer to the router configuration file to parse in
   offline mode.

-r ROUTER - hostname/IP address of the router to review when logging
   into the device via eAPI.

-a CREDENTIALS_FILE - pointer to the YAML formatted file with the API
   credentials to be used if you're logging into the device via eAPI.
   default: ~/.config/router-creds.yml

-u USERNAME - username for logging into the router.  overrides the
   CREDENTIALS_FILE contents.

-p PASSWORD - password for logging into the router. overrides the
   CREDENTIALS_FILE contents.

-e enable - enable password for users which log into the router
   without priv level-15. overrides the CREDENTIALS_FILE contents.

-s generates a summary report instead of emitting an entry for each
   occurrence of the command in the configuration.

-v inserts a listing of all instances of the given command in the
   summary report output.

-t optimization to skip to the running config in show-tech output.

--nossl - why you no like ssl/tls?  triggers the use of http to
          connect to the router.  only to be used in conjunction with
          the -r option.

```

## local config files

**example**  
the default operation of the `check-config.py` script will generate a message for each command it encounters and provide the replacement command. 

``` text
elmo(eos-cli-migrate) % ./check-config.py -c ./cli-changes.csv -f sample-7010t-config.txt
[13] old cmd: no errdisable detect cause link-flap
     new cmd: errdisable detect cause link-change (interface mode) (config mode)
[26] old cmd: ntp source Loopback0
     new cmd: ntp local-interface (config mode)
[38] old cmd: snmp-server source-interface Loopback0
     new cmd: snmp-server local-interface (config mode)
[53] old cmd: aaa authorization console
     new cmd: aaa authorization serial-console (config mode)
[59] old cmd: enable secret 5 <removed>
     new cmd: enable password (config mode)
[522] old cmd: lacp rate fast
      new cmd: lacp timer (interface mode)
[528] old cmd: lacp rate fast
      new cmd: lacp timer (interface mode)
[558] old cmd: vrrp 1 priority 150
      new cmd: vrrp <vrrp_id> priority-level (interface mode)
[559] old cmd: vrrp 1 ip 10.39.136.62
      new cmd: vrrp <vrrp_id> ipv4 (interface mode)
[560] old cmd: vrrp 1 track Vlan103Ethernet52 decrement 100
      new cmd: vrrp <vrrp_id> tracked-object (interface mode)
[561] old cmd: vrrp 2 priority 150
      new cmd: vrrp <vrrp_id> priority-level (interface mode)
[564] old cmd: vrrp 2 track Vlan103Ethernet52 decrement 100
      new cmd: vrrp <vrrp_id> tracked-object (interface mode)
[850] old cmd: control-plane
      new cmd: system control-plane (config mode)
[860] old cmd: policy-map type qos REWRITE
      new cmd: policy-map type quality-of-service (config mode)
[894] old cmd: neighbor IBGP peer-group
      new cmd: neighbor <neighbor_id> peer group (router bgp mode)
[901] old cmd: neighbor IBGP-V6 peer-group
      new cmd: neighbor <neighbor_id> peer group (router bgp mode)
[908] old cmd: neighbor UPSTREAM peer-group
      new cmd: neighbor <neighbor_id> peer group (router bgp mode)
[913] old cmd: neighbor UPSTREAM-V6 peer-group
      new cmd: neighbor <neighbor_id> peer group (router bgp mode)
[918] old cmd: neighbor 198.51.100.226 peer-group IBGP
      new cmd: neighbor <neighbor_id> peer group (router bgp mode)
[920] old cmd: neighbor 198.51.100.225 peer-group UPSTREAM
      new cmd: neighbor <neighbor_id> peer group (router bgp mode)
[922] old cmd: neighbor 2607:f8b0:c000:1862::1 peer-group UPSTREAM-V6
      new cmd: neighbor <neighbor_id> peer group (router bgp mode)
[924] old cmd: neighbor 2001:db8:c000:1a60::2 peer-group IBGP-V6
      new cmd: neighbor <neighbor_id> peer group (router bgp mode)
```

**example: summary output**

for very large configurations it can be difficult to see the individual deprecated commands which are in use.  the summary output mode of operation (`-s` argument) will generate a shorter list of the depecated commands in the configuration as well as listing the lines in the configuration where the deprecated commands can be found.

``` text
elmo(eos-cli-migrate) % ./check-config.py -s -c ./cli-changes.csv -f sample-7010t-config.txt 

       old cmd: errdisable detect cause link-flap
       new cmd: errdisable detect cause link-change
line number(s): 13

       old cmd: ntp source
       new cmd: ntp local-interface
line number(s): 26

       old cmd: snmp-server source-interface
       new cmd: snmp-server local-interface
line number(s): 38

       old cmd: aaa authorization console
       new cmd: aaa authorization serial-console
line number(s): 53

       old cmd: enable secret
       new cmd: enable password
line number(s): 59

       old cmd: lacp rate
       new cmd: lacp timer
line number(s): 522, 528

       old cmd: vrrp <vrrp_id> priority
       new cmd: vrrp <vrrp_id> priority-level
line number(s): 558, 561

       old cmd: vrrp <vrrp_id> ip
       new cmd: vrrp <vrrp_id> ipv4
line number(s): 559

       old cmd: vrrp <vrrp_id> track
       new cmd: vrrp <vrrp_id> tracked-object
line number(s): 560, 564

       old cmd: control-plane
       new cmd: system control-plane
line number(s): 850

       old cmd: policy-map type qos
       new cmd: policy-map type quality-of-service
line number(s): 860

       old cmd: neighbor <neighbor_id> peer-group
       new cmd: neighbor <neighbor_id> peer group
line number(s): 894, 901, 908, 913, 918, 920, 922, 924

```

you may optionally use the `-v` flag to output the occurrence of the commands in the summary output.

**show-tech optimization**  
if you're parsing through show-tech output, you should really use the `-t` flag to make your life tolerable.  this skips directly to the `show running-config sanitized` portion of the configuration bypassing all of the uninteresting (for this exercise) stuff.

## logging into a router

if your devices have [eapi](https://www.arista.com/en/um-eos/eos-section-2-5-session-management-commands#ww1129836) enabled you can log into a running router and determine which command configuration elements have been deprecated.

``` text
elmo(eos-cli-migrate) % ./check-config.py -c cli-changes.csv -r 192.168.1.21
[12] old cmd: ntp source Loopback0
     new cmd: ntp local-interface (config mode)
```

note, this requires additional configuration.  see below re: setup

# installation

- clone the repo to your host
- this tool requires `python3.6` or better
- install the following libraries. 
  - [pyyaml](https://pyyaml.org/wiki/PyYAMLDocumentation)
  - [jsonrpclib-pelix](https://jsonrpclib-pelix.readthedocs.io/en/latest/)

these libraries can be installed through the use of `pipenv` or with the standard `pip` tool.  **pip** `pip install -r requirements.txt` - will install the associated dependencies.

**pipenv**  
`pipenv install` - if you use pipenv this will install the necessary libraries and generate the virtualenv for your use.

# setup

if you plan on logging into routers in order to collect configuration information it is suggested that you edit the `router-creds.yml` file and put it in `~/.config/router-creds.yml` if you need to override the username or password for a particular device you can provide these via the `-u` and the `-p` flags.

if you'd prefer to put this file in a different location, you will need to provide the location using the `-a <path_to_creds_file_here>` argument.

protect this file as appropriate.

# CSV contents

the CSV file contains the following fields: 

- **cmd_id:** unique integer index for the command 
- **src_regex:** the regular expression used to match this particular command. the script will attempt to parse various prefixes (white space, no, etc.) to account for instances of the configuration command being disabled, etc.
- **dep_command:** a more readable form of the deprecated command to be used in
  summary command output.
- **rep_command:** the new/replacement command.
- **cmd_mode:** the section in the configuration where the command occurs


