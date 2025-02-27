import textwrap

from pathlib import Path as P
from typing import Dict, List

import click
from git import Repo

from commodore.component import Component, component_parameters_key
from .inventory import Inventory


# pylint: disable=too-many-instance-attributes,too-many-public-methods
class Config:
    _inventory: Inventory
    _components: Dict[str, Component]
    _config_repos: Dict[str, Repo]
    _component_aliases: Dict[str, str]
    _deprecation_notices: List[str]

    # pylint: disable=too-many-arguments
    def __init__(
        self,
        work_dir: P,
        api_url=None,
        api_token=None,
        verbose=0,
        username=None,
        usermail=None,
    ):
        self._work_dir = work_dir.resolve()
        self.api_url = api_url
        self.api_token = None
        self.api_token = api_token
        self._components = {}
        self._config_repos = {}
        self._component_aliases = {}
        self._verbose = verbose
        self.username = username
        self.usermail = usermail
        self.local = None
        self.push = None
        self.interactive = None
        self.force = False
        self.fetch_dependencies = True
        self._inventory = Inventory(work_dir=self.work_dir)
        self._deprecation_notices = []
        self._global_repo_revision_override = None
        self._tenant_repo_revision_override = None

    @property
    def verbose(self):
        return self._verbose

    @property
    def debug(self):
        return self._verbose > 0

    @property
    def trace(self):
        return self._verbose >= 3

    @property
    def config_file(self):
        return self._inventory.global_config_dir / "commodore.yml"

    @property
    def jsonnet_file(self) -> P:
        return self._work_dir / "jsonnetfile.json"

    @property
    def work_dir(self) -> P:
        return self._work_dir

    @work_dir.setter
    def work_dir(self, d: P):
        self._work_dir = d
        self.inventory.work_dir = d

    @property
    def vendor_dir(self) -> P:
        return self.work_dir / "vendor"

    @property
    def catalog_dir(self) -> P:
        return self.work_dir / "catalog"

    @property
    def refs_dir(self) -> P:
        return self.catalog_dir / "refs"

    @property
    def api_token(self):
        return self._api_token

    @api_token.setter
    def api_token(self, api_token):
        if api_token is not None:
            try:
                p = P(api_token)
                if p.is_file():
                    with open(p) as apitoken:
                        api_token = apitoken.read()
            except OSError as e:
                # File name too long, assume token is not configured as file
                if "File name too long" in e.strerror:
                    pass
                else:
                    raise
            self._api_token = api_token.strip()

    @property
    def global_repo_revision_override(self):
        return self._global_repo_revision_override

    @global_repo_revision_override.setter
    def global_repo_revision_override(self, rev):
        self._global_repo_revision_override = rev

    @property
    def tenant_repo_revision_override(self):
        return self._tenant_repo_revision_override

    @tenant_repo_revision_override.setter
    def tenant_repo_revision_override(self, rev):
        self._tenant_repo_revision_override = rev

    @property
    def inventory(self):
        return self._inventory

    def update_verbosity(self, verbose):
        self._verbose += verbose

    def get_components(self):
        return self._components

    def register_component(self, component: Component):
        self._components[component.name] = component

    def get_component_repo(self, component_name):
        return self._components[component_name].repo

    def get_configs(self):
        return self._config_repos

    def register_config(self, level, repo):
        self._config_repos[level] = repo

    def get_component_aliases(self):
        return self._component_aliases

    def register_component_aliases(self, aliases: Dict[str, str]):
        self._component_aliases = aliases

    def verify_component_aliases(self, cluster_parameters: Dict):
        for alias, cn in self._component_aliases.items():
            ckey = component_parameters_key(cn)
            caliasable = cluster_parameters[ckey].get("multi_instance", False)
            if alias != cn and not caliasable:
                raise click.ClickException(
                    f"Component {cn} with alias {alias} does not support instantiation."
                )

    def register_deprecation_notice(self, notice: str):
        self._deprecation_notices.append(notice)

    def print_deprecation_notices(self):
        tw = textwrap.TextWrapper(
            width=100,
            # Next two options ensure we don't break URLs
            break_long_words=False,
            break_on_hyphens=False,
            initial_indent=" > ",
            subsequent_indent="   ",
        )
        if len(self._deprecation_notices) > 0:
            click.secho("\nCommodore notices:", bold=True)
            for notice in self._deprecation_notices:
                notice = tw.fill(notice)
                click.secho(notice)

    def register_component_deprecations(self, cluster_parameters):
        for cname in self._component_aliases.values():
            ckey = component_parameters_key(cname)
            cmeta = cluster_parameters[ckey].get("_metadata", {})

            if cmeta.get("deprecated", False):
                msg = f"Component {cname} is deprecated."
                if "replaced_by" in cmeta:
                    msg += f" Use component {cmeta['replaced_by']} instead."
                if "deprecation_notice" in cmeta:
                    msg += f" {cmeta['deprecation_notice']}"
                self.register_deprecation_notice(msg)
