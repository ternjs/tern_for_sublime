# Tern for Sublime Text

This is a [Sublime Text][st] (version 2 and 3) package that provides
[Tern][tern]-based JavaScript editing support.

[st]: http://www.sublimetext.com/
[tern]: http://ternjs.net

In JavaScript files, the package will handle autocompletion.

The following keys will be bound (in JavaScript files):

`alt+.`
Jump to the definition of the thing that the cursor is pointing at. If
there is no known code location, but it has a documentation URL
associated with, this will open the documentation in your browser
instead.

`alt+,`
Jump back to where you were when executing the previous `alt+.` command.

`alt+space`
When on a variable, select all references to that variable in the
current file.

## Installation

### Sublime Tern

* **With the [Package Control](https://packagecontrol.io/)** plugin (recommended):

  1. Install Package Control. See: https://packagecontrol.io/installation
  2. Hit **Cmd + Shift + P** and type “Install Package” command. Type `tern_for_sublime` and install the plugin.
  3. Restart Sublime editor


* **Manually**:

  1. Without Git: [Download](https://github.com/marijnh/tern_for_sublime/archive/master.zip) the git repo into your packages folder (in ST, find Browse Packages... menu item to open this folder).

  2. With Git: Check out the code in this repository into a subdirectory of your Sublime Text's `Packages` directory.
    ```
    cd /path/to/sublime-text-N/Packages
    git clone git://github.com/marijnh/tern_for_sublime.git
    ```
  3. Restart ST editor (if required)

### Depedencies (Node, Tern)

Next, make sure [node.js][node] and [npm][npm] are installed (Tern is
a JavaScript program).

**Installing Node.js**

You can manually download Node.js or use nvm to install it.

1. With nvm:
    ```
    nvm install 0.12.6
    ```
You may as well try Node v4.0.0

2. Without nvm:

  Download node from [here][node]

**Installing Tern**

1. Install tern as a global module (recommended)
    ```
    npm install -g tern
    ```

2. Manually by installing the dependencies of the package. Navigate to `tern_for_sublime` located in Sublime packages.
    ```
    cd /path/to/sublime-text-N/Packages/tern_for_sublime
    npm install
    ```

**Node and Tern binaries**

In case you have used `nvm` to install Node you can create symlinks to Node and Tern in order to avoid issues with Sublime

1. Create Node and Tern symlinks.
    ```
    ln -s `which node` /usr/local/bin/node
    ln -s `which tern` /usr/local/bin/tern
    ```

2. Update your Sublime preferences by adding the following configuration
    ```
    "tern_command":[
        "/usr/local/bin/node",
        "/usr/local/bin/tern"
    ]
    ```

*Another way of handling binaries on OS X is by installing the [Fix Mac
Path](https://github.com/int3h/SublimeFixMacPath) Sublime plugin to
help ST actually find your node binary.*


[node]: https://nodejs.org/en/
[npm]: https://npmjs.org/


You should be all set now.

## Configuration

The plugin will load its settings from `Tern.sublime-settings` (found in Preferences > Package Settings > Tern),
and recognizes the following settings:

* `tern_argument_hints` (boolean, defaults to false)
Whether to show argument hints (May impact responsiveness on slow machines or big projects).

* `tern_argument_hints_type` (status, panel, tooltip, defaults to tooltip when available, otherwise status)
  1. __status__ - When status is enabled, the status bar will list
the arguments for the function call that the cursor is inside.
Unfortunately, the status bar is tiny and Sublime Text 2 provides no saner way to show these hints.
  2. __panel__ - When panel is enabled, a new panel window opens and will list
the arguments for the function call that the cursor is inside.
  3. __tooltip__ - (only available on SublimeText build 3070+) When tooltip is enabled, a tooltip opens and will list the arguments for the function call that the cursor is inside, as well as, a clickable URL (if available) to the docs and a snippet of documentation (if available).


* `tern_argument_completion` (boolean, default to false)
Auto complete function arguments (similar to eclipse).
e.g. `document.addEv` will show completion for `addEventListener (fn/2)` which completes to
`document.addEventListener(type, listener)`. The first argument will be selected.
Use `tab` to select the next argument.

  Completions for smaller number arguments are supported.
e.g. in the extreme case, `THREE.SphereGeometry` has 7 arguments, most of which are optional. `THREE.SphG`
will show completions for `SphereGeometry (fn/7)`, `SphereGeometry (fn/6)`, ... , `SphereGeometry (fn/0)`.
Typing 3 (i.e. `THREE.SphG3`) will select the completion `THREE.SphereGeometry (fn/3)` which completes to `THREE.SphereGeometry(a, b, c)`.


* `tern_command` (list of strings) The command to execute to start a
Tern server. The default is
`["node", "/path/to/Packages/tern_for_sublime/node_modules/tern/bin/tern"]`.
If your node installation lives somewhere that's not in the default
path, or your Tern checkout is not where the module expects it to be,
you'll want to manually set this option.

* `tern_arguments` (list of strings) An extra set of arguments to pass
to the Tern server. For example `--no-port-file` to suppress the
creation of `.tern-port` files.

Tern uses `.tern-project` files to configure loading libraries and
plugins for a project. See the [Tern docs][docs] for details.

[docs]: http://ternjs.net/doc/manual.html#configuration

### Automatically Showing Completions

Add `{"selector": "source.js", "characters": "."}` to your
`auto_complete_triggers` array in the Sublime Text preferences (found in Sublime Text > Preferences > Settings - User) to
automatically show completions after a dot is typed following an object name.

Example:
```javascript
"auto_complete_triggers": [ {"selector": "text.html", "characters": "<"}, {"selector": "source.js", "characters": "."} ]
```

If you don't have already an item named `auto_complete_triggers`, just add it after the last one (after adding a comma) like so:

![](http://i.imgur.com/pptihb7.png)

Ensure that your `auto_complete` preference is set to `true`. It's enabled by default.
