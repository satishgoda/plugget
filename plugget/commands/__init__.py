"""
Plugget is a plugin-manager for various applications.
"""
import logging
import subprocess
import datetime
import pprint

from plugget.utils import rmdir
from plugget.data import Package
from plugget import settings

from pathlib import Path


# plugget / cache
# plugget / installed / blender / io_xray.


# def _plugin_name_from_manifest(package_name):
#     # todo rename plugin name to resource name
#     # get plugin_name from manifest
#     if package_name:
#         print("provided manifest, searching for plugin")
#         package = search(package_name, verbose=False)[0]
#         print("found plugin name from manifest", package.package_name)
#         plugin_name = package.plugin_name
#
#         return plugin_name


def _clone_manifest_repo(source_url) -> "pathlib.Path":
    """clone git repo containing plugget manifests, from a git URL"""
    source_name = source_url.split("/")[-1].split(".")[0]
    source_dir = settings.TEMP_PLUGGET / source_name

    # CACHING: check when repo was last updated
    if (source_dir / "_LAST_UPDATED").exists():
        with open(source_dir / "_LAST_UPDATED", "r") as f:
            last_updated = datetime.datetime.strptime(f.read(), "%Y-%m-%d %H:%M:%S")
        if last_updated > datetime.datetime.now() - datetime.timedelta(days=1):
            print("using cached manifest repo, last updated less than a day ago")
            return source_dir

    # remove old manifest repo
    rmdir(source_dir)  # todo catch if this failed
    # check if dir exists
    if source_dir.exists():
        raise Exception(f"Failed to remove source_dir {source_dir}")

    # clone repo
    subprocess.run(["git", "clone", "--depth", "1", "--progress", source_url, str(source_dir)])
    # todo check if command errored / catch exception
    # todo check if clone was successful

    # CACHING: make a file inside named _LAST_UPDATED with the current date
    source_dir.mkdir(parents=True, exist_ok=True)
    with open(source_dir / "_LAST_UPDATED", "w") as f:
        f.write(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    return source_dir


def _clone_manifest_repos():
    """
    clone the manifest repos that are registered, defaults to ['github.com/hannesdelbeke/plugget-pkgs']
    """
    # if repo doesn't exist, clone it
    source_dirs = []
    for source_url in settings.sources:

        # first check if path is a local path
        source_dir = Path(source_url)
        if not source_dir.exists():  # todo fix this naive impicit approach
            # else assume it's a git URL
            source_dir = _clone_manifest_repo(source_url)

        source_dirs.append(source_dir)

    return source_dirs


def _add_source(repo_url):
    """add a git URL or local path to manifest repo"""
    settings.sources.append(repo_url)
    # TODO save to config file


def _detect_app_id():
    try:
        import detect_app
        app = None
        if not app:
            app_found = detect_app.detect_app()
            return app_found.id if app_found else None
    except:
        None


def search(name=None, app=None, verbose=True, latest_only=True):
    """
    search if package is in sources
    :param name: pacakge name to search in manifest repo, return all packages if not set
    :param app: app name to search in, return all apps if not set
    :param verbose: print results if True
    """

    app = _detect_app_id() if not app else app

    plugins = []
    source_dirs = _clone_manifest_repos()
    for source_dir in source_dirs:  # go through all cloned manifest repos
        if app and app != 'all':  # filter by app
            source_dir = source_dir / app
        for plugin_manifest in source_dir.rglob("*.json"):
            source_name = plugin_manifest.parent.name  # this checks for manifest name, not name in package todo
            if name is None or name.lower() in source_name.lower():
                plugins.append(Package.from_json(plugin_manifest))

    if latest_only and len(plugins)>1:
        # todo sort versions
        # [ numpy 1, numpy 2 ]
        # check if same manifest folder
        shared = {}  # same packages, but diff version, sorted by their package name
        temp = []
        for plugin in plugins:
            shared.setdefault(plugin.package_name, [])
            shared[plugin.package_name].append(plugin)
            temp.append(plugin)
        if len(shared) == 1:

            # get latest in shared
            # TODO sort temp, by latest version
            # for now hack, if it says latest return that
            latest = [p.version == "latest" for p in temp]
            if latest:
                return latest

            # sort versions sorts list of strings
            # temp contains packages, so we need to get their version with .version
            temp_sorted = sorted(temp, key=lambda x: x.version)
            plugins = [temp_sorted[-1]]

    if verbose:
        print(f"{len(plugins)} plugins found in repo:")
        print(f"{'-' * 20}")
        for plugin in plugins:
            print(f"{plugin}")

    return plugins


# # WARNING we overwrite build in type list here, careful when using list in this module!
# open package manager
def list(package_name:str = None, enabled=False, disabled=False, verbose=True, app=None):  # , source=None):
    """
    list all installed packages
    if run from an app, only list the apps installed packages, with option to list all app installed packages

    :param enabled: list enabled packages only if True
    :param disabled: list disabled packages only if True
    TODO :param source: list packages from specific source only if set
    """
    # todo print installed packages in INSTALLED_DIR, instead of app plugins

    # module = _get_app_module()

    # if enabled:
    #     plugins = module.enabled_plugins()
    # elif disabled:
    #     plugins = module.disabled_plugins()
    # else:  # list all installed
    #     plugins = module.installed_plugins()

    # todo we don#'t _clone_manifest_repos, so won't find packages if we didnt first search.

    # list all installed in settings.INSTALLED_DIR
    plugins = []
    app = _detect_app_id() if not app else app

    if app and app != "all":
        app_manifest_dir = settings.INSTALLED_DIR / app
    else:
        app_manifest_dir = settings.INSTALLED_DIR

    for plugin_manifest in app_manifest_dir.rglob("*.json"):
        package = Package.from_json(plugin_manifest)
        if package_name and package_name.lower() not in package.package_name.lower():  #  plugin_manifest.parent.name.lower():
            continue
        plugins.append(package)

    if verbose:
        print(f"{len(plugins)} installed plugins")
        print(f"{'-' * 20}")
        for plugin in plugins:
            print(f"{plugin}")

    return plugins


#    plugin_name = plugin_name or plugin_name_from_manifest(package_name)
def install(package_name, enable=True, app=None, **kwargs):
    """
    install package
    :param name: name of the manifest folder in the manifest repo
    :param enable: enable plugin after install
    """
    # todo
    #  get package (manifest)
    #  check if package is already installed
    #  install package, by running action(s) from manifest
    #  save manifest to installed packages dir

    # copy package to blender package folder
    # module = _get_app_module()

    # get package manifest from package repo
    package = search(name=package_name, app=app, verbose=False)[0]
    if not package:
        logging.warning("Package not found, cancelling install")
        return

    package.install(enable=enable, **kwargs)
    # uninstall if unsuccessful?


def uninstall(package_name=None, dependencies=False, **kwargs):
    """
    uninstall package
    :param name: name of the manifest folder in the manifest repo
    """
    # todo, a user might expect to do install(pluginname") instead of install("manifestname"),
    #  since this would also work with non plugget plugins
    #  check repos for (matching) manifest, uninstall? vs check local isntalled plugins, uninstall. much easier but name is diff from install

    # plugin_name = plugin_name or _plugin_name_from_manifest(package_name)
    # module = _get_app_module()  # todo remove
    # module.uninstall_plugin(plugin_name)

    package = list(package_name, verbose=False)[0]
    if not package:
        logging.warning("Package not found, cancelling install")
        return

    package.uninstall(dependencies=dependencies, **kwargs)


def info(package_name=None, verbose=True):
    """
    show info about package
    :param name: name of the manifest folder in the manifest repo
    """

    packages = list(package_name, verbose=False) or search(package_name, verbose=False)
    if not packages:
        logging.warning("Package not found")
        return
    if len(packages) > 1:
        logging.warning(f"Multiple packages found: {packages}")
        return
    package = packages[0]
    pprint.pp(package.to_dict())
    import plugget.github as github
    favorited = github.is_starred(package.repo_url)
    star_count = github.get_repo_stars(package.repo_url)
    print(f"starred by hannes: {favorited}, star-count ⭐:", star_count)


# # todo this is a plugin command, exposed to plugget. maybe we want to do this for all commands?
# def disable(package_name=None, plugin_name=None):
#     """
#     disable package
#     :param name: name of the manifest folder in the manifest repo
#     """
#     plugin_name = plugin_name or _plugin_name_from_manifest(package_name)
#     module = _get_app_module()  # todo remove
#     module.disable_plugin(plugin_name)
#
#
# def enable(package_name=None, plugin_name=None):
#     """
#     enable package
#     :param name: name of the manifest folder in the manifest repo
#     """
#     plugin_name = plugin_name or _plugin_name_from_manifest(package_name)
#     module = _get_app_module()  # todo remove
#     module.enable_plugin(plugin_name)


# def update(package_name=None, plugin_name=None, all=False):
#     """
#     update a plugin, identify by either:
#     TODO :param name: name of the manifest folder in the manifest repo
#     TODO :param plugin_name: name of the plugin in the app
#     TODO :param all: update all installed plugins if True
#     """
#
#     # get list of isntalled (not enabled) plugins.
#     # check them for updates (plugget and app update if supported)
#
#     pass


# def open_install_dir():
#     module = _get_app_module()  # todo remove
#     module.open_install_dir()


# aliases
# upgrade = update





