import sys
import os

from krita import *
from PyQt5.QtWidgets import QAction, QMenu


class ShotgunExtension(Extension):
    """
    Note: The Shotgun integration requires shotgun to be python3 compatible.
    
    Up until then, we can keep this extension enabled.
    """

    def __init__(self, parent):
        """ constructor """
        super().__init__(parent)
        
        self._use_shotgun = False

    def setup(self):
        """
        Make sure we load shotgun
        """
        try:
            if os.environ.get('SG_PYTHONPATH'):
                paths = os.environ.get('SG_PYTHONPATH').split(os.pathsep)
                for p in paths:
                    sys.path.append(p)
            import sgtk
            sgtk.LogManager().initialize_base_file_handler("tk-krita")
        except:
            self._use_shotgun = False
            # for debugging we raise the error

    def createActions(self, window):
        """
        Post startup script
        """
        if self._use_shotgun:
            import sgtk
            logger = sgtk.LogManager.get_logger(__name__)
            
            env_engine = os.environ.get('SGTK_ENGINE')
            env_context = os.environ.get('SGTK_CONTEXT')
            if not env_engine:
                raise Exception("Shotgun: Missing required environment "
                                  "variable SGTK_ENGINE")
            if not env_context:
                raise Exception("Shotgun: Missing required environment "
                                  "variable SGTK_CONTEXT")
                                  
            try:
                context = sgtk.context.deserialize(env_context)
            except Exception as e:
                raise Exception("Shotgun: Could not create context! "
                                  "Shotgun Pipeline Toolkit will be disabled. "
                                  "Details: {}".format(e))
            
            try:
                logger.debug("Launching engine instance '{0}' "
                             "for context '{1}'".format(env_engine, 
                                                        env_context))
                engine = sgtk.platform.start_engine(env_engine,
                                                    context.sgtk,
                                                    context)
            except Exception as e:
                raise Exception("Shotgun: Could not start engine: "
                                  "\n{}".format(e))

# And add the extension to Krita's list of extensions:
Krita.instance().addExtension(ShotgunExtension(Krita.instance())) 
