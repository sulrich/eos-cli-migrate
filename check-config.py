#!/usr/bin/env python3

# Copyright (c) 2020, Arista Networks
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# * Redistributions of source code must retain the above copyright notice, this
#   list of conditions and the following disclaimer.
#
# * Redistributions in binary form must reproduce the above copyright notice,
#   this list of conditions and the following disclaimer in the documentation
#   and/or other materials provided with the distribution.
#
# * Neither the name of the Arista nor the names of its
#   contributors may be used to endorse or promote products derived from
#   this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
# SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
# OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import argparse
import csv
import re
import ssl
import sys
import textwrap
from collections import defaultdict
from pathlib import Path

import jsonrpclib
import yaml


def nested_dd():
    return defaultdict(nested_dd)


def import_cli_info(csv_file):
    """generates a dict w/regexes and response text from provided csv_file

    args:
    csv_file - path to the file to be imported.
    """
    cmds = nested_dd()
    try:
        with open(csv_file, newline="") as cli_csvfile:
            import_reader = csv.reader(cli_csvfile)
            for row in import_reader:
                key = row[0]
                cmds[key]["cmd_regex"] = "^(?:\s*|\s*no\s*)" + row[1]
                cmds[key]["dep_cmd"] = row[2]
                cmds[key]["new_cmd"] = row[3]
                cmds[key]["section"] = row[4]
    except IOError:
        print("error opening csv_file file:", csv_file)
        sys.exit()

    return cmds


def gen_summary(config_lines, lnums, cmd_info, verbose=False, **kwargs):
    """creates a table with the list of commands and the lines
    they occur on  with the relevant replacement command
    """
    summary = ""
    for k in config_lines:
        # since only output the line numbers in the summary
        linenumbers = ", ".join(str(x) for x in lnums[k])
        linenumbers = textwrap.fill(linenumbers, subsequent_indent=" " * 16)
        config_entries = "\n".join(config_lines[k])
        summary += f"""
       old cmd: { cmd_info[k]['dep_cmd'] }
       new cmd: { cmd_info[k]['new_cmd'] }
line number(s): { linenumbers }
"""

        if verbose:
            summary += f"""
config entries
==============
{ config_entries }
"""

    print(summary)


def load_config(config_file):
    """ given a file path returns the configuration as a list for processing

    parameters:
      config_file (string): path to the configuration file or show-tech to load.

    returns:
       list: contents of the device's running-config
    """

    try:
        with open(config_file) as f:
            config = f.readlines()
            return config
    except IOError:
        print("error opening configuration file:", config_file)
        sys.exit()


def get_router_config(
    router, username, password, enable_password, protocol="https", **kwargs
):
    """ logs into a router and slurps down the config

    parameters:
      router (string): hostname / ip address of the device to log into
      username (string): username for logging into the device
      password (string): password
      enable_password (string): enable password, if required.
      protocol (string): http/https.

    returns:
       list: contents of the device's running-config
    """

    try:
        _create_unverified_https_context = ssl._create_unverified_context
    except AttributeError:
        # legacy python that doesn't verify https certificates by default
        pass
    else:
        # handle target environment that doesn't support https verification
        ssl._create_default_https_context = _create_unverified_https_context

    rtr = jsonrpclib.Server(
        "%s://%s:%s@%s/command-api" % (protocol, username, password, router)
    )

    cmds = [{"cmd": "enable", "input": enable_password}, "show running-config"]

    resp = rtr.runCmds(1, cmds, "text")  # we specifically want text output
    return resp[1]["output"].splitlines()


def parse_cli_options():
    """ parses command line options and resolves CLI flag dependencies

    parameters:
      args:

    returns:
       argparse object
    """
    parser = argparse.ArgumentParser(usage=arg_usage())
    parser.add_argument(
        "-s",
        "--summary",
        dest="gen_summary",
        help="generate a summary of impacted commands.",
        action="store_true",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        dest="verbose_summary",
        help="includes the relevant configuration snippets in summary output",
        action="store_true",
    )
    parser.add_argument(
        "-c",
        "--csv_file",
        dest="csv_file",
        required=True,
        help="csv file with command changes",
    )
    parser.add_argument(
        "-f", "--config_file", dest="config_file", help="router config file to parse"
    )
    parser.add_argument(
        "-a",
        "--credentials_file",
        dest="credentials_file",
        help="yaml file with credentials.  by default this is to be found in ~/.config",
    )
    parser.add_argument(
        "-r", "--router", dest="router", help="router hostname/ip address"
    )
    parser.add_argument(
        "-u",
        "--username",
        dest="api_username",
        help="username for logging into a router",
    )
    parser.add_argument(
        "-p",
        "--password",
        dest="api_password",
        help="password for logging into a router",
    )
    parser.add_argument(
        "-e",
        "--enable_password",
        dest="enable_password",
        help="enable password when logging into a router",
    )
    parser.add_argument(
        "-t",
        "--showtech",
        dest="show_tech",
        action="store_true",
        help="optimization if you'r eparsign show-tech output (looks for running config)",
    )
    parser.add_argument(
        "--nossl", dest="no_ssl", action="store_true", help="why you no like ssl?"
    )
    args = parser.parse_args()

    # we either need a config file or a router hostname
    if (args.config_file is None) and (args.router is None):
        parser.error(
            "you must specify either a configuration file or a router hostname"
        )
        parser.print_usage

    return args


def get_config(args):
    """ get the configuration either from a file or directly from the router

    parameters:
      args: argparse object

    returns:
      list: with the configuration contents
    """
    config = []  # initialize the configuration

    if args.router:
        creds = {}
        # load credentials file - to be used if we're logging into the router
        credentials_file = str(Path.home()) + "/.config/router-creds.yml"
        if args.credentials_file:
            credentials_file = args.credentials_file
        try:
            with open(credentials_file) as yaml_file:
                creds = yaml.load(yaml_file)
        except IOError:
            print("error opening credentials file:", credentials_file)

    # command line argument overrides
    if args.api_username:
        creds["api_username"] = args.api_username

    if args.api_password:
        creds["api_password"] = args.api_password

    if args.enable_password:
        creds["enable_password"] = args.enable_password

    if args.no_ssl:
        rtr_protocol = "http"
    else:
        rtr_protocol = "https"

    if args.config_file and args.router is None:
        config = load_config(args.config_file)

    if args.router:
        config = get_router_config(
            args.router,
            creds["api_username"],
            creds["api_password"],
            creds["enable_password"],
            protocol=rtr_protocol,
        )

    return config


def parse_config(args, config):
    """ parses device configuration and generates the appropriate report info.

    parameters:
      args: argparse object
      config: list with the device config contents

    returns:
       outputs a report on STDOUT
    """

    cmd_info = import_cli_info(args.csv_file)  # load cli info

    # command change summaries
    dep_lnums = defaultdict(list)
    dep_cline = defaultdict(list)

    show_tech_flag = False
    tech_str = "^-+ show running-config sanitized"
    tech_re = re.compile(tech_str)

    line_num = 0  # config line number
    for line in config:
        if args.show_tech:
            skip = re.match(tech_re, line)
            config_end = re.match("^end", line)
            if not skip and not show_tech_flag:
                continue  # got to the next line
            elif skip and not show_tech_flag:  # starting the config section
                show_tech_flag = True
                line_num += 1
            elif config_end and show_tech_flag:
                break

        if args.show_tech and show_tech_flag:
            line_num += 1  # increment config line numbers when we're in a show tech
        if not args.show_tech:
            line_num += 1

        for k in cmd_info:
            if re.match(cmd_info[k]["cmd_regex"], line):

                d_cmd = f"[{line_num}] old cmd: {line.strip()}"
                pad = len(str(line_num)) + 3
                r_cmd = (
                    " " * pad
                    + f"new cmd: {cmd_info[k]['new_cmd']} {cmd_info[k]['section']}"
                )

                dep_lnums[k].append(line_num)
                dep_cline[k].append(line.strip())

                # note, this is the default mode of operation
                if not args.gen_summary:
                    print(d_cmd)
                    print(r_cmd)

    if args.gen_summary:
        gen_summary(dep_cline, dep_lnums, cmd_info, verbose=args.verbose_summary)


def main():
    args = parse_cli_options()  # parse command line option flags
    config = get_config(args)
    parse_config(args, config)


def arg_usage():
    """ outputs a nice usage message """
    return """
usage: check-config.py [-h] [-s] [-v] -c CSV_FILE [-f CONFIG_FILE]
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
"""


if __name__ == "__main__":
    main()
