#!/usr/bin/env python3
import os

from ops.main import main
from ops.charm import CharmBase
from subprocess import PIPE, Popen
import pathlib

THIS_DIR = pathlib.Path(__file__).parent.resolve()
HOOKS_DIR = THIS_DIR.parent / 'hooks'
UNIT_NAME = THIS_DIR.parent.parent.name
PATH_PREFIX = f"export PATH=$PATH:/var/lib/juju/tools/{UNIT_NAME}"
SETENV = "source /proc/1/environ"  # hacky! assume we can clone PID 1's env
CMD_WRAPPER = f'/bin/bash -c "{SETENV}; {PATH_PREFIX}; {HOOKS_DIR}/{{}}"'


print('ENV:')
for k, val in os.environ.items():
    print(f"{k} = {val}")


def dash_to_underscore(s: str) -> str:
    return s.replace('-', '_')


def run_hook(name):
    cmd = CMD_WRAPPER.format(name)
    p = Popen(cmd, shell=True, stdout=PIPE, stderr=PIPE)
    stdout, stderr = p.communicate()
    print(stdout)
    if stderr:
        raise RuntimeError(cmd, stderr)


class Microsample(CharmBase):
    def __init__(self, *args):
        super().__init__(*args)

        framework = self.framework

        # don't do this at home; really, do not.
        for hook_name in os.listdir(f"{HOOKS_DIR}"):
            snake_case_hook = dash_to_underscore(hook_name)
            framework.observe(
                getattr(self.on, snake_case_hook),  # event binding
                getattr(self, f"_on_{snake_case_hook}")  # method
            )

    def _on_config_changed(self, _event):  # noqa
        run_hook('config-changed')

    def _on_install(self, _event):  # noqa
        run_hook('install')

    def _on_start(self, _event):  # noqa
        run_hook('start')

    def _on_stop(self, _event):  # noqa
        run_hook('stop')

    def _on_update_status(self, _event):  # noqa
        run_hook('update-status')

    def _on_upgrade_charm(self, _event):  # noqa
        run_hook('upgrade_charm')

    def _on_website_relation_broken(self, _event):  # noqa
        run_hook('website-relation-broken')

    def _on_website_relation_changed(self, _event):  # noqa
        run_hook('website-relation-changed')

    def _on_website_relation_departed(self, _event):  # noqa
        run_hook('website-relation-departed')

    def _on_website_relation_joined(self, _event):  # noqa
        run_hook('website-relation-joined')


if __name__ == "__main__":
    main(Microsample)
