import sys
import ast
import os.path
import ConfigParser

import utils

DEBUG = 0
DEFAULT_CONFIG_DIR = os.path.join(os.path.split(__file__)[0], "configurations")

class ConfigDict(dict):
    def __getattr__(self, key):
        return self.__getitem__(key)


class CoastGuardConfigs(object):
    def __init__(self, base_config_dir=DEFAULT_CONFIG_DIR):
        self.base_config_dir = base_config_dir
        self.config_dicts = {}
        self.configs = ConfigDict()

    def __getattr__(self, key):
        return self.configs[key]

    def __getitem__(self, key):
        return self.config_dicts[key]

    def read_file(self, fn, required=False):
        if required and not os.path.isfile(fn):
            raise ValueError("Configuration file (%s) doesn't exist " \
                             "and is required!" % fn)
        if not fn.endswith('.cfg'):
            raise ValueError("Coast Guard configuration files must " \
                             "end with the extention '.cfg'.")
        key = os.path.split(fn)[-1][:-4]
        self.config_dicts[key] = ConfigDict()
        execfile(fn, {}, self.config_dicts[key])
        # Load just-read configurations into current configs
        self.configs.update(self.config_dicts[key])

    def get_default_configs(self):
        """Read the default configurations and return them.
 
            Inputs:
                None

            Outputs:
                None
        """
        default_config_fn = os.path.join(self.base_config_dir, "default.cfg")
        self.read_file(default_config_fn, required=True)

    def get_configs_for_archive(self, ar):
        """Given a psrchive archive object return relevant configurations.
            This will include configurations for the telescope, frontend,
            backend, and pulsar.
 
            Inputs:
                ar: The psrchive archive to get configurations for.
 
            Outputs:
                None
        """
        fn = ar.get_filename()
        hdrparams = utils.parse_psrfits_header(fn, \
                            ['site', 'be:name', 'rcvr:name', 'name'])
        
        # Create a list of all the configuration files to check
        config_files = []
        telescope = utils.site_to_telescope[hdrparams['site'].lower()]
        config_files.append(os.path.join(self.base_config_dir, 'telescopes', \
                                "%s.cfg" % telescope.lower()))
        config_files.append(os.path.join(self.base_config_dir, 'receivers', \
                                "%s.cfg" % hdrparams['rcvr:name'].lower()))
        config_files.append(os.path.join(self.base_config_dir, 'backends', \
                                "%s.cfg" % hdrparams['be:name'].lower()))
        config_files.append(os.path.join(self.base_config_dir, 'pulsars', \
                                "%s.cfg" % hdrparams['name'].upper()))
        config_files.append(os.path.join(self.base_config_dir, 'observations', \
                                "%s.cfg" % os.path.split(fn)[-1]))
 
        if DEBUG:
            print "Checking for the following configurations:"
            for cfg in config_files:
                print "    %s" % cfg
        
        for fn in config_files:
            if os.path.isfile(fn):
                self.read_file(fn)

def main():
    cfg = CoastGuardConfigs()
    cfg.get_default_configs()
    import psrchive
    ar = psrchive.Archive_load(sys.argv[1])
    cfg.get_configs_for_archive(ar)
    print '-'*25
    print cfg['default']['conf'], cfg['default'].conf, cfg.conf

if __name__ == '__main__':
    main()
