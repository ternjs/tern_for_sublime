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

Check out the code in this repository into a subdirectory of your
Sublime Text's `Packages` directory.

    cd /path/to/sublime-text-N/Packages
    git clone git://github.com/marijnh/tern_for_sublime.git

Next, make sure [node.js][node] and [npm][npm] are installed (Tern is
a JavaScript program), and install the depedencies of the package.

[node]: http://nodejs.org
[npm]: https://npmjs.org/

    cd tern_for_sublime
    npm install

On OS X, you might also need to install the [Fix Mac
Path](https://github.com/int3h/SublimeFixMacPath) Sublime plugin to
help ST actually find your node binary.

You should be all set now.

## Configuration

The plugin will load its settings from `Tern.sublime-settings` (found in Preferences > Package Settings > Tern),
and recognized the following settings:

`tern_argument_hints` (boolean, defaults to false)  
Whether to show argument hints (May impact responsiveness on slow machines or big projects).

`tern_argument_hints_type` (status, panel, tooltip, defaults to tooltip when available, otherwise status)  
__status__ - When status is enabled, the status bar will list
the arguments for the function call that the cursor is inside.
Unfortunately, the status bar is tiny and Sublime Text 2 provides no saner way to show these hints.  
__panel__ - When panel is enabled, a new panel window opens and will list
the arguments for the function call that the cursor is inside.  
__tooltip__ - (only available on SublimeText build 3070+) When tooltip is enabled, a tooltip opens and will list the arguments for the function call that the cursor is inside, as well as, a clickable URL (if available) to the docs and a snippet of documentation (if available).

`tern_argument_completion` (boolean, default to false)  
Auto complete function arguments (similar to eclipse).  
e.g. `document.addEv` will show completion for `addEventListener (fn/2)` which completes to
`document.addEventListener(type, listener)`. The first argument will be selected.
Use `tab` to select the next argument.

Completions for smaller number arguments are supported.  
e.g. in the extreme case, `THREE.SphereGeometry` has 7 arguments, most of which are optional. `THREE.SphG`
will show completions for `SphereGeometry (fn/7)`, `SphereGeometry (fn/6)`, ... , `SphereGeometry (fn/0)`.
Typing 3 (i.e. `THREE.SphG3`) will select the completion `THREE.SphereGeometry (fn/3)` which completes to `THREE.SphereGeometry(a, b, c)`.


`tern_command` (list of strings) The command to execute to start a
Tern server. The default is
`["node", "/path/to/Packages/tern_for_sublime/node_modules/tern/bin/tern"]`.
If your node installation lives somewhere that's not in the default
path, or your Tern checkout is not where the module expects it to be,
you'll want to manually set this option.

`tern_arguments` (list of strings) An extra set of arguments to pass
to the Tern server. For example `--no-port-file` to suppress the
creation of `.tern-port` files.

Tern uses `.tern-project` files to configure loading libraries and
plugins for a project. See the [Tern docs][docs] for details.

[docs]: http://ternjs.net/doc/manual.html#configuration

### Automatically Showing Completions

Add `{"selector": "source.js", "characters": "."}` to your
`auto_complete_triggers` array in the Sublime Text preferences to
automatically show completions after a dot is typed following an
object name.

Example:
```javascript
"auto_complete_triggers": [ {"selector": "text.html", "characters": "<"}, {"selector": "source.js", "characters": "."} ]
```

Ensure that your `auto_complete` preference is set to `true`. It's enabled by default.
