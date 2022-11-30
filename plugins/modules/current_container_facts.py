#!/usr/bin/python
#
# (c) 2020 Matt Clay <mclay@redhat.com>
# (c) 2020 Felix Fontein <felix@fontein.de>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type


DOCUMENTATION = r'''
---
module: current_container_facts
short_description: Return facts about whether the module runs in a Docker container
version_added: 1.1.0
description:
  - Return facts about whether the module runs in a Docker container.
  - This module attempts a best-effort detection. There might be special cases where
    it does not work; if you encounter one, L(please file an issue,
    https://github.com/ansible-collections/community.docker/issues/new?assignees=&labels=&template=bug_report.md).
author:
  - Felix Fontein (@felixfontein)
'''

EXAMPLES = '''
- name: Get facts on current container
  community.docker.current_container_facts:

- name: Print information on current container when running in a container
  ansible.builtin.debug:
    msg: "Container ID is {{ ansible_module_container_id }}"
  when: ansible_module_running_in_container
'''

RETURN = r'''
ansible_facts:
    description: Ansible facts returned by the module
    type: dict
    returned: always
    contains:
        ansible_module_running_in_container:
            description:
              - Whether the module was able to detect that it runs in a container or not.
            returned: always
            type: bool
        ansible_module_container_id:
            description:
              - The detected container ID.
              - Contains an empty string if no container was detected.
            returned: always
            type: str
        ansible_module_container_type:
            description:
              - The detected container environment.
              - Contains an empty string if no container was detected.
              - Otherwise, will be one of C(docker) or C(azure_pipelines).
            returned: always
            type: str
            # choices:
            #   - docker
            #   - azure_pipelines
'''

import os
import re

from ansible.module_utils.basic import AnsibleModule


def main():
    module = AnsibleModule(dict(), supports_check_mode=True)

    cpuset_path = '/proc/self/cpuset'
    mountinfo_path = '/proc/self/mountinfo'

    container_id = ''
    container_type = ''

    contents = None
    if os.path.exists(cpuset_path):
        # File content varies based on the environment:
        #   No Container: /
        #   Docker: /docker/c86f3732b5ba3d28bb83b6e14af767ab96abbc52de31313dcb1176a62d91a507
        #   Azure Pipelines (Docker): /azpl_job/0f2edfed602dd6ec9f2e42c867f4d5ee640ebf4c058e6d3196d4393bb8fd0891
        #   Podman: /../../../../../..
        # While this was true and worked well for a long time, this seems to be no longer accurate
        # with newer Docker / Podman versions and/or with cgroupv2. That's why the /proc/self/mountinfo
        # detection further down is done when this test is inconclusive.
        with open(cpuset_path, 'rb') as f:
            contents = f.read().decode('utf-8')

        cgroup_path, cgroup_name = os.path.split(contents.strip())

        if cgroup_path == '/docker':
            container_id = cgroup_name
            container_type = 'docker'

        if cgroup_path == '/azpl_job':
            container_id = cgroup_name
            container_type = 'azure_pipelines'

    if not container_id and os.path.exists(mountinfo_path):
        with open(mountinfo_path, 'rb') as f:
            contents = f.read().decode('utf-8')

        for line in contents.splitlines():
            parts = line.split()
            if len(parts) >= 5 and parts[4] == '/etc/hostname':
                m = re.match('.*/docker/containers/([a-f0-9]+)/hostname', parts[3])
                if m:
                    container_id = m.group(1)
                    container_type = 'docker'

    module.exit_json(ansible_facts=dict(
        ansible_module_running_in_container=container_id != '',
        ansible_module_container_id=container_id,
        ansible_module_container_type=container_type,
    ))


if __name__ == '__main__':
    main()
