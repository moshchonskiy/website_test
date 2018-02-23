import json
import socket
from argparse import ArgumentParser
from urllib.parse import urlparse
from pprint import pprint
from time import time

import requests
from requests.exceptions import Timeout


def write_to_json(source_dict):
    with open('output.json', 'w') as json_file:
        json.dump(source_dict, json_file, indent=4)


desktop_agents = {'chrome': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/64.0.3282.167 Safari/537.36',
                  'firefox': 'Mozilla/5.0 (Windows NT 10.0; WOW64; rv:57.0) Gecko/20100101 Firefox/57.0',
                  'safari': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_1) AppleWebKit/602.2.14 (KHTML, like Gecko) Version/10.0.1 Safari/602.2.14'}


def _header(agent):
    return {'User-Agent': desktop_agents[agent],
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'}


class DomainTester(object):
    def __init__(self):
        self.scheme = 'https://'
        self.requests_timeout = None
        self.desktop_agent = None

    def _default_result(self):
        result_dict = dict(
            resolution_time=self.requests_timeout,
            ip='not_known',
            redirects=0,
            http_code=504,
            ip_connect_time=self.requests_timeout
        )
        return result_dict

    def set_timeout(self, timeout):
        def print_warn():
            print('Timeout must be an integer or a float!')

        if '.' in timeout:
            try:
                timeout = float(timeout)
            except ValueError:
                print_warn()
                exit(1)
        else:
            try:
                timeout = int(timeout)
            except ValueError:
                print_warn()
                exit(1)
        self.requests_timeout = timeout

    def set_agent(self, agent):
        self.desktop_agent = _header(agent)

    def connect_to_ip_time(self, socket_tuple):
        """returns time in seconds to connect to ip"""
        start_time = time()
        socket.create_connection(socket_tuple, timeout=self.requests_timeout)
        finish_time = time()
        return finish_time - start_time

    def get_site_content_time(self, url):
        """returns time in seconds to get site content"""
        start_time = time()
        requests.get(url, timeout=self.requests_timeout, headers=self.desktop_agent)
        finish_time = time()
        return finish_time - start_time

    def get_resolution_time(self, url):
        """returns response obj and time taken to resolve dns"""
        start_time = time()
        response = requests.head(url, timeout=self.requests_timeout, headers=self.desktop_agent,
                                 stream=True, allow_redirects=True)
        taken_time = time() - start_time
        return response, taken_time

    def test_domain(self, host):
        """ Resolves host and returns a dictionary of
        { 'ip', 'resolution_time', 'redirects', 'http_code', 'ip', 'ip_connect_time', 'get_content_time}. """
        resolved_host = {}
        parsed = urlparse(host)
        if not parsed.scheme:
            scheme = self.scheme
        else:
            scheme = parsed.scheme

        url = scheme + host
        try:
            response, resolved_host['resolution_time'] = self.get_resolution_time(url)
        except Timeout:
            return self._default_result()

        ip_port = response.raw._connection.sock.getpeername()
        resolved_host['ip_connect_time'] = self.connect_to_ip_time(ip_port)
        resolved_host['ip'] = ip_port[0]
        redirects = response.history
        resolved_host['redirects'] = len(redirects) if redirects else 0
        if response.ok:
            resolved_host['get_content_time'] = self.get_site_content_time(url)
        resolved_host['http_code'] = response.status_code
        return resolved_host

    def test_domains(self, domains):
        """tests provided list of domains and returns dictionary with results"""
        resolved_domains = {}
        for domain in domains:
            resolved = self.test_domain(domain)
            resolved_domains[domain] = {}
            resolved_domains[domain].update(resolved)
        return resolved_domains


def parse_cli():
    argparser = ArgumentParser(usage="Usage: -d [domain1, domain2] [arguments]", prog="dns_resolve")

    argparser.add_argument("-j", "--to_json", help="Output results to output.json file", dest="to_json",
                           action="store_true")

    argparser.add_argument("-t", "--timeout",
                           help="resolve timeout", dest="timeout", action="store")

    argparser.add_argument("-d", "--domains", dest="domains", nargs='+', action="store",
                           help="List of domains to perform testing")

    argparser.add_argument("-f", "--file", dest="filename",
                           help="File containing list of domains, every domain on new line")

    argparser.add_argument("-a", "--user_agent", dest='agent', help="chrome, firefox or safari")

    options = argparser.parse_args()

    if (not options.to_json) and (not options.timeout) and (not options.domains) and (not options.filename):
        argparser.print_help()
        exit(1)

    return options


if __name__ == "__main__":
    domain_tester = DomainTester()

    opts = parse_cli()

    if not opts.domains and not opts.filename:
        print('You must specify a list of web sites or provide a file')
        exit(1)
    if opts.timeout:
        domain_tester.set_timeout(opts.timeout)
    if opts.agent:
        domain_tester.set_agent(opts.agent)
    if opts.domains:
        tested_domains = domain_tester.test_domains(opts.domains)
    if opts.filename:
        with open(opts.filename) as f:
            sites = [site.strip() for site in f.readlines()]
            tested_domains = domain_tester.test_domains(sites)
    if not opts.to_json:
        pprint(tested_domains)
    else:
        write_to_json(tested_domains)

    print("\nCompleted")
