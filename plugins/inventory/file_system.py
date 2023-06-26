DOCUMENTATION = r'''
    inventory: file_system
    name: Inventory Plugin Basics
    plugin_type: inventory
    author:
      - Bert Tejeda (@berttejeda)
    short_description: Creates an inventory from grouped device definition files.
    version_added: "2.10"
    description:
        - Creates an inventory from grouped device definition files
        - The parent directory of the specified inventory file is interpreted as the 'site_directory'
        - The device definitions files are expected to be located under $site_directory/devices
        - The logic expects definition files to be yaml-formatted, with the '.yaml' file extention
    options:
        environment_domain:
            description: The site's base FQDN
            type: string
            required: True
        os_class_map:
            description:
              - A mapping that populates two hostvars ('os_classes', 'os_class_names') based on host naming convention
              - e.g. lxr3-fso-01 will have the following:
                - os_classes:
                    - lxr3
                - os_class_names:
                    - Linux Raspberry PI Model 3
              - Can be a path to an external yaml file containing the OS class map under the 'data' key
            required: False
        sub_group_map:
            description:
              - A mapping that populates two hostvars ('sub_groups', 'sub_group_names') based on host naming convention
              - e.g. lxr3-fso-01 will have the following:
                - sub_groups:
                    - fso
                - sub_group_names:
                    - File System Object Server
              - Can be a path to an external yaml file containing the Subgroup map under the 'data' key
            required: False
    requirements:
        - python >= 3.4
'''

EXAMPLES = r'''
# In-line OS/Subgroup maps
plugin: file_system
environment_domain: /some/site
os_class_map:
  wl08:
    - wl08: Windows 8 Laptop
  wl10:
    - wl10: Windows 10 Laptop
  wg10:
    - wg10: Generic Windows 10
  wlnn:
    - wlnn: Generic Windows Laptop
  uxmb:
    - uxmb: OSX Macbook
  uxmd:
    - uxmd: OSX Mac Desktop
  lxol:
    - lxol: Linux (Oracle Enterprise Linux/OEL)
  lxr0:
    - lxr0: Linux Raspberry PI Model 0
  lxr1:
    - lxr1: Linux Raspberry PI Model 1
  lxr2:
    - lxr2: Linux Raspberry PI Model 2
  lxr3:
    - lxr3: Linux Raspberry PI Model 3
  lxr4:
    - lxr4: Linux Raspberry PI Model 4
sub_group_map:
  dck:
    - app: Application Server
    - dck: Docker Microservices Host
  vcs:
    - vcs: Version/Source Control Server
  vdi:
    - vdi: Virtual Desktop Instance
  cld:
    - cld: Cloud Server
  pbx:
    - pbx: PBX Server
  ofc:
    - ofc: Office Computer
  vga:
    - vga: Gaming Computer

# External OS/Subgroup maps
plugin: file_system
environment_domain: /some/site
os_class_map: /some/path/os_class_map.yaml
sub_group_map: /some/path/sub_group_map.yaml

'''

# Ansible internal request utilities
from ansible.plugins.inventory import BaseInventoryPlugin
from pathlib import Path
import argparse
import logging
import re
import yaml

# Setup Logging
logger = logging.getLogger()
streamhandler = logging.StreamHandler()
streamhandler.setFormatter(
    logging.Formatter("%(asctime)s %(name)s [%(levelname)s]: %(message)s", datefmt='%Y-%m-%d %H:%M:%S')
)
logger.addHandler(streamhandler)


def read_yaml(y):
    yaml_content = yaml.load(y, yaml.Loader)
    return yaml_content


class InventoryGenerator(object):

    def __init__(self, **kwargs):

        self.args = kwargs.get('args')
        if self.args:
            if self.args.debug:
                logger.setLevel(logging.DEBUG)
        site_directory_obj = Path(kwargs['site_directory'])
        self.site_directory = site_directory_obj.as_posix()
        self.site_definitions_directory = Path.joinpath(site_directory_obj, 'definitions').as_posix()
        self.expression_pattern = re.compile("""hostname\\[(.*)\\][\\s]+\\+[\\s]+("')[\\d]+("')|hostname\\[(.*)\\]""")
        self.synthetic_hostname_pattern = re.compile('(.*)(\\[[\\d]+.*\\]).*')
        self.child_hostname_pattern = re.compile('(.*)@(.*)')
        self.group_names_pattern = re.compile('\\.|-| ')
        self.environment_domain = kwargs['environment_domain']
        os_class_map_arg = kwargs.get('os_class_map', '')
        if os_class_map_arg:
            if isinstance(os_class_map_arg, dict):
                self.os_class_map = os_class_map_arg
            elif Path(os_class_map_arg).is_file():
                os_class_map = read_yaml(open(os_class_map_arg).read())
                self.os_class_map = os_class_map.get('data', {})
            else:
                self.os_class_map = {}
        else:
            self.os_class_map = {}

        sub_group_map_arg = kwargs.get('sub_group_map', '')
        if sub_group_map_arg:
            if isinstance(sub_group_map_arg, dict):
                self.sub_group_map = sub_group_map_arg
            elif Path(sub_group_map_arg).is_file():
                sub_group_map = read_yaml(open(sub_group_map_arg).read())
                self.sub_group_map = sub_group_map.get('data', {})
            else:
                self.sub_group_map = {}
        else:
            self.sub_group_map = {}

    def merge(self, a, b, path=None):
        """merges b into a"""
        if not all([a, b]):
            return dict(a)
        if path is None:
            path = []
        for key in b:
            if key in a:
                if isinstance(a[key], dict) and isinstance(b[key], dict):
                    self.merge(a[key], b[key], path + [str(key)])
                elif a[key] == b[key]:
                    pass  # same leaf value
                else:
                    pass
            else:
                a[key] = b[key]
        return dict(a)

    def expand_host(self, **kwargs):

        expmatch = kwargs.get('expmatch')
        if expmatch:
            if expmatch.groups()[-1]:
                range_group = expmatch.groups()[-1]
            elif expmatch.groups()[1]:
                range_group = expmatch.groups()[1]
            range_string = range_group.translate(str.maketrans('', '', '[]'))
        hostnums = range_string.split('-')
        hoststring = expmatch.groups()[0]
        start = int(hostnums[0])
        if len(hostnums) > 1:
            end = int(hostnums[1]) + 1
        else:
            end = int(hostnums[0]) + 1
        for n_ in range(start, end):
            hostname_result = '{}{}'.format(hoststring, "%02d" % n_)
            yield hostname_result

    def traverse_site(self, directory):
        """
    Traverse recursively through the site
    directory for .yaml files
    """
        definition_file_dirs = (f for f in Path(directory).glob('*') if f.is_dir)
        for definition_file_dir in definition_file_dirs:
            for definition_file in Path(definition_file_dir).glob('*.yaml'):
                definition_file_name = definition_file.name
                definition_file_path = definition_file.as_posix()
                expanded_host = self.synthetic_hostname_pattern.match(definition_file_name)
                if expanded_host:
                    for eh in self.expand_host(expmatch=expanded_host):
                        hostname_short = eh
                        eh_hostname = '%s.%s' % (eh, self.environment_domain)
                        yield (definition_file_path, eh_hostname, hostname_short)
                else:
                    hostname_short = definition_file.stem
                    if hostname_short == 'localhost':
                        hostname = hostname_short
                    else:
                        hostname = f'{hostname_short}.{self.environment_domain}'
                    yield (definition_file_path, hostname, hostname_short)

    def generate_host_data(self, inv_obj_pairs):
        """
    Generate host data from inventory object pairs
    """

        for r in inv_obj_pairs:
            if not r:
                continue
            # Parse the hostname
            inv_obj = Path(r[0])
            default_group_path = (inv_obj.parent).as_posix()
            primary_group = Path(default_group_path).name
            definition_file = r[0]
            # Merge in vars from definition file
            # These are effectively hostvars
            definition_data = read_yaml(open(definition_file).read())
            definition_file_facts = []
            definition_file_vars = {}
            try:
                if isinstance(definition_data, dict):
                    definition_file_vars = dict(definition_data[0].get('vars', {}))
                elif isinstance(definition_data, list):
                    definition_file_facts = [dict(f.get('set_fact', {})) for f in definition_data if
                                             dict(f.get('set_fact', {}))]
                    for fact_vars in definition_file_facts:
                        definition_file_vars = self.merge(fact_vars, definition_file_vars)
            except TypeError as e:
                logger.debug('Encountered an error when reading {f} - {err}'.format(
                    f=definition_file,
                    err=e
                )
                )
            hostparts = r[0].split('@')
            if len(hostparts) > 1:
                parent = '.'.join(hostparts[1].split('.')[0:-1])
                hostname = f'{parent}:{r[1]}'
            else:
                hostname = r[1]
            logger.debug('Processed record name is %s' % hostname)
            hostname_short = r[2]
            host_data = {}
            hostname_parts = hostname.split('-')
            if hostname == 'localhost':
                host_data['primary_group'] = 'ansible_controller'
                host_data['os_classes'] = ['local']
                host_data['sub_groups'] = ['local']
            elif len(hostname_parts) == 1:
                continue
            elif len(hostname_parts) > 0:
                os_class = hostname_parts[0]
                sub_group = hostname_parts[1] if len(hostname_parts) > 1 else 'misc'
                host_data['os_classes'] = [list(c.keys())[0] for k, v in self.os_class_map.items() for c in v if
                                           os_class == k]
                host_data['os_class_names'] = [list(c.values())[0] for k, v in self.os_class_map.items() for c in v if
                                               os_class == k]
                host_data['sub_groups'] = [list(g.keys())[0] for k, v in self.sub_group_map.items() for g in v if
                                           sub_group == k]
                host_data['sub_group_names'] = [list(g.values())[0] for k, v in self.sub_group_map.items() for g in v if
                                                sub_group == k]
                host_data['primary_group'] = primary_group

            host_data['hostname'] = hostname_short
            # Add more metadata
            host_data['fqdn'] = hostname
            host_data['definition_file'] = definition_file
            host_data['default_group_path'] = default_group_path
            host_data['site_directory'] = self.site_directory
            host_data['environment_domain'] = self.environment_domain
            host_data['ansible_host'] = hostname
            host_data = self.merge(host_data, definition_file_vars)
            ansible_real_host = host_data.get('ansible_real_host')
            if ansible_real_host:
                host_data['ansible_ssh_host'] = ansible_real_host
            else:
                host_data['ansible_ssh_host'] = hostname
                host_data['ansible_winrm_host'] = hostname
            system_type = host_data.get('system_type')
            if system_type == 'lxd':
                lxd_host = host_data.get('lxd_host')
                if lxd_host:
                    host_data['ansible_host'] = f'{lxd_host}:{hostname_short}'
            elif system_type == 'qemu':
                host_data['ansible_host'] = f'{hostname_short}'
                host_data['ansible_ssh_host'] = f'{hostname_short}'
            yield host_data

    def generate_inventory(self, **kwargs):

        host_mock = kwargs.get('host_mock')
        host_filter = kwargs.get('filter')

        ################################################################################
        # Get the records from recurisve file listing
        ################################################################################
        # If mock-host is specified, skip DNS logic
        if (host_mock):
            inv = [(host_mock, host_mock)]
        else:
            # Limit hosts to that provided in limit option
            # (for troubleshooting)
            if host_filter:
                inv = [f for f in self.traverse_site(self.site_definitions_directory) if f[1] in host_filter]
            else:
                inv = self.traverse_site(self.site_definitions_directory)
        ################################################################################
        # Generate host data from inventory object pairs
        ################################################################################
        host_data = self.generate_host_data(inv)
        ################################################################################
        # Initialize the output hash and create the "all" group
        ################################################################################
        output = {
            "all": {
                "hosts": [],
                "vars": {}
            },
            "_meta": {
                "hostvars": {}

            }
        }

        # Iterate over each host and assign it to the group "all"
        # We also assign hostvars in the _meta group here
        for host_record in host_data:
            hostname = host_record['hostname']
            host_aliases = host_record.get('host_aliases', [])
            if host_aliases:
                logger.debug(f'Found host aliases for {hostname}: {host_aliases}')
            for host_alias in host_aliases:
                output["_meta"]["hostvars"][host_alias] = host_record
                output["all"]["hosts"].append(host_alias)
            output["_meta"]["hostvars"][hostname] = host_record
            output["all"]["hosts"].append(hostname)

        logger.debug(output)

        return output


class InventoryModule(BaseInventoryPlugin):
    NAME = 'file_system'

    def parse(self, inventory, loader, path, cache=False):
        super(InventoryModule, self).parse(inventory, loader, path)
        self._read_config_data(path)

        site_directory = Path(path).parent

        root_group_name = self.inventory.add_group('site')

        inv_data = {
            'site_directory': site_directory,
            'environment_domain': self.get_option('environment_domain'),
            'os_class_map': self.get_option('os_class_map'),
            'sub_group_map': self.get_option('sub_group_map')
        }

        host_data = InventoryGenerator(**inv_data).generate_inventory()

        for hostname in host_data['all']['hosts']:

            hostname_data = host_data['_meta']['hostvars'][hostname]
            hostname_inv_obj = self.inventory.add_host(hostname)

            primary_group_inv_name = self.inventory.add_group(hostname_data['primary_group'])
            self.inventory.add_child(root_group_name, primary_group_inv_name)
            self.inventory.add_child(primary_group_inv_name, hostname_inv_obj)

            sub_groups = hostname_data['sub_groups']
            for sub_group in sub_groups:
                sub_group_inv_name = self.inventory.add_group(sub_group)
                self.inventory.add_child(sub_group_inv_name, hostname_inv_obj)
                self.inventory.add_child(root_group_name, sub_group_inv_name)

            os_classes = hostname_data['os_classes']
            for os_class in os_classes:
                os_class_group_inv_name = self.inventory.add_group(os_class)
                self.inventory.add_child(os_class_group_inv_name, hostname_inv_obj)
                self.inventory.add_child(root_group_name, os_class_group_inv_name)

            extra_host_groups = hostname_data.get('extra_host_groups', [])
            for extra_host_group in extra_host_groups:
                host_group_inv_name = self.inventory.add_group(extra_host_group)
                self.inventory.add_child(host_group_inv_name, hostname_inv_obj)
                self.inventory.add_child(root_group_name, host_group_inv_name)

            for var_key, var_val in hostname_data.items():
                self.inventory.set_variable(hostname, var_key, var_val)


if __name__ == '__main__':

    def parse_args():

        parser = argparse.ArgumentParser(description="Ansible inventory script")
        parser.add_argument('--site-directory', '-sid', required=True)
        parser.add_argument('--environment-domain', '-d', required=True)
        parser.add_argument('--sub-group-map', '-sgmap', default='{"data": {"NOMATCH": [""]}}')
        parser.add_argument('--os-class-map', '-osmap', default='{"data": {"NOMATCH": [""]}}')
        parser.add_argument('--debug', action='store_true')
        parser.add_argument('--verbose', action='store_true')
        args = parser.parse_args()
        return args

    args = parse_args()
    os_class_map = {}
    os_class_map_arg: object = args.os_class_map
    if os_class_map_arg:
        if Path(os_class_map_arg).is_file():
            os_class_map = read_yaml(open(os_class_map_arg).read())

    sub_group_map = {}
    sub_group_map_arg = args.sub_group_map
    if os_class_map_arg:
        if Path(sub_group_map_arg).is_file():
            sub_group_map = read_yaml(open(sub_group_map_arg).read())

    inv_data = {
        'args': args,
        'site_directory': args.site_directory,
        'environment_domain': args.environment_domain,
        'os_class_map': os_class_map,
        'sub_group_map': sub_group_map
    }

    InventoryGenerator(**inv_data).generate_inventory()
