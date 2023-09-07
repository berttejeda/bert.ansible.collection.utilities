# Dynamic Inventory - file system

## Overview

The file system dynamic inventory allows you to define 
ansible hosts as yaml files organized into folders
that represent their primary host groups.

It expects the following directory structure:

```bash  
  ./definitions/
    host_group_1/
      host-01.yaml
    host_group_2/
      host-02.yaml
  ./inventory.yaml
```

## The inventory file

```yaml
plugin: berttejeda.utilities.file_system
environment_domain: {{ site_domain }}
#############################################
####    Host OS Class Map                ####
#### Map a given host to additional host #### 
#### groups based on regular expressions #### 
#### matching OS Classificaiton          ####
####                                     ####
#############################################
os_class_map: /path/to/os_class_map.yaml
#############################################
####    Host Subgroup Map                ####
#### Map a given host to additional host #### 
#### groups based on regular expressions #### 
#### matching functional sub groups      ####
#############################################
sub_group_map: path/to/sub_group_map.yaml
```

### environment_domain

The environment domain specifies the ansible host suffix.

### os_class_map

Given the following OS Class Map:

```yaml
data: 
  lxaw:
    - lxaw: Amazon Linux (AWS)
    - aws:  Generic AWS Hostgroup
```

Suppose your definition file is named `lxaw-01-apl.yaml`

The OS Class Map will add this host to the following host groups:

- lxaw
- aws

### sub_group_map

Given the following Sub-Group Map:

```yaml
data:
  apl:
    - apl:  Application Server
    - apps: Apps Group
```

Suppose your definition file is named `lxaw-01-apl.yaml`

The Sub-Group Map will add this host to the following host groups:

- apl
- apps

## Definition files

Definition files serve not only as host definitions, 
but as valid ansible task files.

## Example

Given the following:

1. You are logged in as user `ansible`
2. Your home directory is `/home/ansible`
3. You've created your site folder under `/home/ansible/sites/contoso.com`
4. Definitions directory structure:<br />
```bash  
  ./definitions/
    ansible.controller/
      localhost.yaml
    app.servers/
      lxub-apl-01.yaml
    cloud.servers/
      lxub-cld-01.yaml
      lxcs-cld-01.yaml
  ./inventory.yaml
```

5. The following inventory file `inventory.yaml`:<br />
```yaml
plugin: berttejeda.utilities.file_system
environment_domain: contoso.com
#############################################
####    Host OS Class Map                ####
####                                     ####
#############################################
os_class_map: os_class_map.yaml
#############################################
####    Host Subgroup Map                ####
####                                     ####
#############################################
sub_group_map: sub_group_map.yaml
```

6. The following os classification map `os_class_map.yaml`:<br />

```yaml
data: 
  lxaw:
    - lxaw: Amazon Linux (AWS)
  lxcs:
    - lxcs: Linux (Cent OS)
  lxde: 
    - lxde: Linux (Debian)
  lxub: 
    - lxub: Linux (Ubuntu)
  lxrh: 
    - lxrh: Linux (Red Hat)
  lxol: 
    - lxol: Linux (Oracle Enterprise Linux/OEL)
```

7. The following host sub-group map `sub_group_map.yaml`:<br />

```yaml
data: 
  mlx: 
    - mlx: Mail Exchange Server
  fso: 
    - fso: File System Object Server
  dmc: 
    - dmc: Domain controller
  clr: 
    - clr: Generic Cluster
  vrh: 
    - vrh: Virtual Host
  web: 
    - web: Web Server
  apl: 
    - apl: Application Server
  ddb: 
    - ddb: Database Server
  cld: 
    - apps: Application Server
    - cld: Cloud Server
```

Running `ansible-inventory -i inventory.yaml --list` would yield:

```yaml
{
    "_meta": {
        "hostvars": {
            "localhost": {
                "ansible_host": "localhost",
                "ansible_host_fqdn": "localhost",
                "ansible_ssh_host": "localhost",
                "ansible_winrm_host": "localhost",
                "default_group_path": "/home/ansible/sites/contoso.com/definitions/ansible.controller",
                "definition_file": "/home/ansible/sites/contoso.com/definitions/ansible.controller/localhost.yaml",
                "environment_domain": "contoso.com",
                "hostname": "localhost",
                "os_classes": [
                    "local"
                ],
                "primary_group": "ansible_controller",
                "site_directory": "/home/ansible/sites/contoso.com",
                "sub_groups": [
                    "local"
                ]
            },
            "lxcs-cld-01": {
                "ansible_host": "lxcs-cld-01.contoso.com",
                "ansible_host_fqdn": "lxcs-cld-01.contoso.com",
                "ansible_ssh_host": "lxcs-cld-01.contoso.com",
                "ansible_winrm_host": "lxcs-cld-01.contoso.com",
                "default_group_path": "/home/ansible/sites/contoso.com/definitions/cloud.servers",
                "definition_file": "/home/ansible/sites/contoso.com/definitions/cloud.servers/lxcs-cld-01.yaml",
                "environment_domain": "contoso.com",
                "hostname": "lxcs-cld-01",
                "os_class_names": [
                    "Linux (Cent OS)"
                ],
                "os_classes": [
                    "lxcs"
                ],
                "primary_group": "cloud.servers",
                "site_directory": "/home/ansible/sites/contoso.com",
                "sub_group_names": [
                    "Application Server",
                    "Cloud Server"
                ],
                "sub_groups": [
                    "apps",
                    "cld"
                ]
            },
            "lxub-apl-01": {
                "ansible_host": "lxub-apl-01.contoso.com",
                "ansible_host_fqdn": "lxub-apl-01.contoso.com",
                "ansible_ssh_host": "lxub-apl-01.contoso.com",
                "ansible_winrm_host": "lxub-apl-01.contoso.com",
                "default_group_path": "/home/ansible/sites/contoso.com/definitions/app.servers",
                "definition_file": "/home/ansible/sites/contoso.com/definitions/app.servers/lxub-apl-01.yaml",
                "environment_domain": "contoso.com",
                "hostname": "lxub-apl-01",
                "os_class_names": [
                    "Linux (Ubuntu)"
                ],
                "os_classes": [
                    "lxub"
                ],
                "primary_group": "app.servers",
                "site_directory": "/home/ansible/sites/contoso.com",
                "sub_group_names": [
                    "Application Server"
                ],
                "sub_groups": [
                    "apl"
                ]
            },
            "lxub-cld-01": {
                "ansible_host": "lxub-cld-01.contoso.com",
                "ansible_host_fqdn": "lxub-cld-01.contoso.com",
                "ansible_ssh_host": "lxub-cld-01.contoso.com",
                "ansible_winrm_host": "lxub-cld-01.contoso.com",
                "default_group_path": "/home/ansible/sites/contoso.com/definitions/cloud.servers",
                "definition_file": "/home/ansible/sites/contoso.com/definitions/cloud.servers/lxub-cld-01.yaml",
                "environment_domain": "contoso.com",
                "hostname": "lxub-cld-01",
                "os_class_names": [
                    "Linux (Ubuntu)"
                ],
                "os_classes": [
                    "lxub"
                ],
                "primary_group": "cloud.servers",
                "site_directory": "/home/ansible/sites/contoso.com",
                "sub_group_names": [
                    "Application Server",
                    "Cloud Server"
                ],
                "sub_groups": [
                    "apps",
                    "cld"
                ]
            }
        }
    },
    "all": {
        "children": [
            "ungrouped",
            "site"
        ]
    },
    "ansible_controller": {
        "hosts": [
            "localhost"
        ]
    },
    "apl": {
        "hosts": [
            "lxub-apl-01"
        ]
    },
    "app.servers": {
        "hosts": [
            "lxub-apl-01"
        ]
    },
    "apps": {
        "hosts": [
            "lxub-cld-01",
            "lxcs-cld-01"
        ]
    },
    "cld": {
        "hosts": [
            "lxub-cld-01",
            "lxcs-cld-01"
        ]
    },
    "cloud.servers": {
        "hosts": [
            "lxub-cld-01",
            "lxcs-cld-01"
        ]
    },
    "local": {
        "hosts": [
            "localhost"
        ]
    },
    "lxcs": {
        "hosts": [
            "lxcs-cld-01"
        ]
    },
    "lxub": {
        "hosts": [
            "lxub-cld-01",
            "lxub-apl-01"
        ]
    },
    "site": {
        "children": [
            "ansible_controller",
            "local",
            "cloud.servers",
            "apps",
            "cld",
            "lxub",
            "lxcs",
            "app.servers",
            "apl"
        ]
    }
}
```

# Host Facts

This plugin allws you to define host facts not only in the `group_vars` and `host_vars` directories,
but also at the definition level via the `set_facts` directive.

## Example

```yaml
- name: Set Fact | user_data
  set_fact:
    my_fact: 'my fact value'
```

During the dynamic inventory run phase, 
any facts declared as above will be made available 
as hostvars.

# Installation

To install:

`ansible-galaxy collection install bert.utilities`