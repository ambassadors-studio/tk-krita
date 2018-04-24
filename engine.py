"""
A Krita engine for Tank.

"""

import logging

from krita import Krita

import sgtk
from sgtk.platform import Engine
from sgtk.platform.qt import QtGui

###############################################################################################
# methods to support the state when the engine cannot start up
# for example if a non-sgtk file is loaded in maya


def _active_document():
    """
    Returns the current document.
    """
    if not Krita.instance():
        return None

    if not Krita.instance().documents():
        return None

    return Krita.instance().activeDocument()


def refresh_engine(engine_name, prev_context, menu_name):
    """
    Refresh the current engine
    """
    current_engine = sgtk.platform.current_engine()

    if not current_engine:
        # If we don't have an engine for some reason then we don't have
        # anything to do.
        return

    document = _active_document()

    if not document:
        # There is no active document so we leave the engine in it's current
        # state.
        return

    # determine the tk instance and ctx to use:
    tk = current_engine.sgtk

    # loading a scene file
    new_path = document.fileName().abspath()

    # this file could be in another project altogether, so create a new
    # API instance.
    try:
        tk = sgtk.sgtk_from_path(new_path)
    except sgtk.TankError, e:
        logging.warning("Shotgun: Engine cannot be started: %s" % e)
        # build disabled menu
        create_sgtk_disabled_menu(menu_name)
        return

    # shotgun menu may have been removed, so add it back in if its not already there.
    current_engine.create_shotgun_menu()
    # now remove the shotgun disabled menu if it exists.
    remove_sgtk_disabled_menu()

    # and construct the new context for this path:
    ctx = tk.context_from_path(new_path, prev_context)

    if ctx != sgtk.platform.current_engine().context:
        current_engine.change_context(ctx)


def sgtk_disabled_message():
    """
    Explain why sgtk is disabled.
    """
    msg = ("Shotgun integration is disabled because it cannot recognize "
           "the currently opened file.  Try opening another file or restarting "
           "Krita.")

    win = Krita.instance().window().qwindow()
    QtGui.QMessageBox.information(win,
                                  "Sgtk is disabled.",
                                  msg)


def create_sgtk_disabled_menu(menu_name):
    """
    Render a special "shotgun is disabled" menu
    """
    win = Krita.instance().window().qwindow()

    # Find the shotgun menu
    menuBar = win.menuBar()
    sg_menu = None
    for action in menuBar.actions():
        if action.objectName == "shotgun":
            sg_menu = action.menu()
            break

    if sg_menu:
        # Clear all the actions before adding our item
        sg_menu.clear()
    else:
        # we need to create a new shotgun menu
        sg_menu = QtGui.QMenu("Shotgun", menuBar)
        sg_menu.setObjectName("shotgun")
        menu_action = menuBar.addMenu(sg_menu)
        menu_action.setObjectName("shotgun")

    # add the disabled action to our menu
    disabled_action = QtGui.QAction("Sgtk is disabled.")
    disabled_action.triggered.connect(sgtk_disabled_message)
    disabled_action.setObjectName("shotgun_disabled")


def remove_sgtk_disabled_menu():
    """
    Remove the special "shotgun is disabled" menu if it exists

    :returns: True if the menu existed and was deleted
    """
    win = Krita.instance().window().qwindow()

    menuBar = win.menuBar()
    sg_menu = None
    for action in menuBar.actions():
        if action.objectName == "shotgun":
            sg_menu = action.menu()
            break

    if not sg_menu:
        return False

    for action in sg_menu.actions():
        if action.objectName() == "shotgun_disabled":
            sg_menu.removeAction(action)
            return True

    return False


###############################################################################################
# The Sgtk Krita engine

class KritaEngine(Engine):
    """
    Toolkit engine for Krita.
    """

    @property
    def context_change_allowed(self):
        """
        Whether the engine allows a context change without the need for a restart.
        """
        return False

    @property
    def host_info(self):
        """
        :returns: A dictionary with information about the application hosting this engine.

        The returned dictionary is of the following form on success:

            {
                "name": "Krita",
                "version": "4.0.0",
            }

        The returned dictionary is of following form on an error preventing
        the version identification.

            {
                "name": "Krita",
                "version: "unknown"
            }
        """
        inst = Krita.instance()

        host_info = {
            "name": "Krita",
            "version": inst.version()
        }

        return host_info

    ##########################################################################################
    # init and destroy

    def pre_app_init(self):
        """
        Runs after the engine is set up but before any apps have been initialized.
        """
        # unicode characters returned by the shotgun api need to be converted
        # to display correctly in all of the app windows
        from sgtk.platform.qt import QtCore
        # tell QT to interpret C strings as utf-8
        utf8 = QtCore.QTextCodec.codecForName("utf-8")
        QtCore.QTextCodec.setCodecForCStrings(utf8)
        self.logger.debug("set utf-8 codec for widget text")

    def init_engine(self):
        """
        Initializes the Krita engine.
        """
        self.logger.debug("%s: Initializing...", self)

        self._kritaInstance = Krita.instance()

        # default menu name is Shotgun but this can be overriden
        # in the configuration to be Sgtk in case of conflicts
        self._menu_name = "Shotgun"

    def _has_menu(self):
        """
        Returns True when the shotgun menu has already been built once.
        """
        # We need the QWindow object for building the menu
        window = self._kritaInstance.window().qwindow()
        menuBar = window.menuBar()

        for action in menuBar.actions():
            if action.objectName == 'shotgun':
                return True

        return False

    def create_shotgun_menu(self):
        """
        Creates the main shotgun menu in Krita.
        Note that this only creates the menu, not the child actions.

        :return: bool
        """
        window = self._kritaInstance.window().qwindow()
        menuBar = window.menuBar()
        # only create the shotgun menu if not in batch mode and menu doesn't already exist
        if self.has_ui and not self._has_menu():
            menu = QtGui.QMenu("Shotgun", window.menuBar())
            menu.setObjectName("shotgun")

            menu_action = menuBar.addMenu(menu)
            menu_action.setObjectName("shotgun")

            #tk_krita = self.import_module("tk_krita")
            #self._menu_generator = tk_maya.MenuGenerator(self, self._menu_handle)
            ## hook things up so that the menu is created every time it is clicked
            #self._menu_handle.postMenuCommand(self._menu_generator.create_menu)

            ## Restore the persisted Shotgun app panels.
            #tk_maya.panel_generation.restore_panels(self)
            return True

        return False

    def post_app_init(self):
        """
        Called when all apps have initialized
        """
        self.create_shotgun_menu()

        # Run a series of app instance commands at startup.
        self._run_app_instance_commands()

    def post_context_change(self, old_context, new_context):
        """
        Runs after a context change. The Krita event watching will be stopped
        and new callbacks registered containing the new context information.

        :param old_context: The context being changed away from.
        :param new_context: The new context being changed to.
        """
        print("Not implemented yet")

    def _run_app_instance_commands(self):
        """
        Runs the series of app instance commands listed in the 'run_at_startup' setting
        of the environment configuration yaml file.
        """

        # Build a dictionary mapping app instance names to dictionaries of commands they registered with the engine.
        app_instance_commands = {}
        for (command_name, value) in self.commands.iteritems():
            app_instance = value["properties"].get("app")
            if app_instance:
                # Add entry 'command name: command function' to the command dictionary of this app instance.
                command_dict = app_instance_commands.setdefault(app_instance.instance_name, {})
                command_dict[command_name] = value["callback"]

        # Run the series of app instance commands listed in the 'run_at_startup' setting.
        for app_setting_dict in self.get_setting("run_at_startup", []):

            app_instance_name = app_setting_dict["app_instance"]
            # Menu name of the command to run or '' to run all commands of the given app instance.
            setting_command_name = app_setting_dict["name"]

            # Retrieve the command dictionary of the given app instance.
            command_dict = app_instance_commands.get(app_instance_name)

            if command_dict is None:
                self.logger.warning(
                    "%s configuration setting 'run_at_startup' requests app '%s' that is not installed.",
                    self.name, app_instance_name)
            else:
                if not setting_command_name:
                    # Run all commands of the given app instance.
                    # Run these commands once Maya will have completed its UI update and be idle
                    # in order to run them after the ones that restore the persisted Shotgun app panels.
                    for (command_name, command_function) in command_dict.iteritems():
                        self.logger.debug("%s startup running app '%s' command '%s'.",
                                          self.name, app_instance_name, command_name)
                        command_function()
                        # maya.utils.executeDeferred(command_function)
                else:
                    # Run the command whose name is listed in the 'run_at_startup' setting.
                    # Run this command once Maya will have completed its UI update and be idle
                    # in order to run it after the ones that restore the persisted Shotgun app panels.
                    command_function = command_dict.get(setting_command_name)
                    if command_function:
                        self.logger.debug("%s startup running app '%s' command '%s'.",
                                          self.name, app_instance_name, setting_command_name)
                        command_function()
                        # maya.utils.executeDeferred(command_function)
                    else:
                        known_commands = ', '.join("'%s'" % name for name in command_dict)
                        self.logger.warning(
                            "%s configuration setting 'run_at_startup' requests app '%s' unknown command '%s'. "
                            "Known commands: %s",
                            self.name, app_instance_name, setting_command_name, known_commands)

    def destroy_engine(self):
        """
        Stops watching scene events and tears down menu.
        """
        self.logger.debug("%s: Destroying...", self)

        # clean up UI:
        if self.has_ui and self._has_menu():
            shotgun_action = None
            for action in self._kritaInstance.menuBar().actions():
                if action.objectName() == "shotgun":
                    shotgun_action = action
                    break
            self._kritaInstance.menuBar().removeAction(shotgun_action)

    def _get_dialog_parent(self):
        """
        Get the QWidget parent for all dialogs created through
        show_dialog & show_modal.
        """
        parent = self._kritaInstance.window().qwindow()
        return parent

    @property
    def has_ui(self):
        """
        Detect and return if maya is running in batch mode
        """
        return True

    ##########################################################################################
    # logging

    def _emit_log_message(self, handler, record):
        """
        Called by the engine to log messages in Maya script editor.
        All log messages from the toolkit logging namespace will be passed to this method.

        :param handler: Log handler that this message was dispatched from.
                        Its default format is "[levelname basename] message".
        :type handler: :class:`~python.logging.LogHandler`
        :param record: Standard python logging record.
        :type record: :class:`~python.logging.LogRecord`
        """
        # Give a standard format to the message:
        #     Shotgun <basename>: <message>
        # where "basename" is the leaf part of the logging record name,
        # for example "tk-multi-shotgunpanel" or "qt_importer".
        if record.levelno < logging.INFO:
            formatter = logging.Formatter("Debug: Shotgun %(basename)s: %(message)s")
        else:
            formatter = logging.Formatter("Shotgun %(basename)s: %(message)s")

        msg = formatter.format(record)

        print(msg)

    def close_windows(self):
        """
        Closes the various windows (dialogs, panels, etc.) opened by the engine.
        """
        # Make a copy of the list of Tank dialogs that have been created by the engine and
        # are still opened since the original list will be updated when each dialog is closed.
        opened_dialog_list = self.created_qt_dialogs[:]

        # Loop through the list of opened Tank dialogs.
        for dialog in opened_dialog_list:
            dialog_window_title = dialog.windowTitle()
            try:
                # Close the dialog and let its close callback remove it from the original dialog list.
                self.logger.debug("Closing dialog %s.", dialog_window_title)
                dialog.close()
            except Exception, exception:
                self.logger.error("Cannot close dialog %s: %s", dialog_window_title, exception)
