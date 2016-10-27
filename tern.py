# Sublime Text plugin for Tern

import sublime, sublime_plugin
import os, sys, platform, subprocess, webbrowser, json, re, time, atexit
from subprocess import CalledProcessError
try:
  # python 2
  from utils.renderer import create_renderer
except:
  from .utils.renderer import create_renderer

windows = platform.system() == "Windows"
python3 = sys.version_info[0] > 2
is_st2 = int(sublime.version()) < 3000

def is_js_file(view):
  return len(view.sel()) > 0 and view.score_selector(sel_end(view.sel()[0]), "source.js") > 0

files = {}
arghints_enabled = False
renderer = None
arg_completion_enabled = False
tern_command = None
tern_arguments = []

def on_deactivated(view):
  pfile = files.get(view.file_name(), None)
  if pfile and pfile.dirty:
    send_buffer(pfile, view)

def on_selection_modified(view):
  if not arghints_enabled: return
  pfile = get_pfile(view)
  if pfile is not None: show_argument_hints(pfile, view)

class Listeners(sublime_plugin.EventListener):
  def on_close(self, view):
    files.pop(view.file_name(), None)

  def on_deactivated(self, view):
    if is_st2: on_deactivated(view)

  def on_deactivated_async(self, view):
    on_deactivated(view)

  def on_modified(self, view):
    pfile = files.get(view.file_name(), None)
    if pfile: pfile_modified(pfile, view)

  def on_selection_modified(self, view):
    if is_st2: on_selection_modified(view)

  def on_selection_modified_async(self, view):
    on_selection_modified(view)

  def on_query_completions(self, view, prefix, _locations):
    sel = sel_start(view.sel()[0])
    if view.score_selector(sel, 'string.quoted') > 0: return None
    if view.score_selector(sel, 'comment') > 0: return None

    pfile = get_pfile(view)
    if pfile is None: return None

    completions, fresh = ensure_completions_cached(pfile, view)
    if completions is None: return None

    if not fresh:
      completions = [c for c in completions if c[1].startswith(prefix)]
    return completions


class ProjectFile(object):
  def __init__(self, name, view, project):
    self.project = project
    self.name = name
    self.dirty = view.is_dirty()
    self.cached_completions = None
    self.cached_arguments = None
    self.showing_arguments = False
    self.last_modified = 0

class Project(object):
  def __init__(self, dir):
    self.dir = dir
    self.port = None
    self.proc = None
    self.last_failed = 0
    self.disabled = False

  def __del__(self):
    kill_server(self)


def get_pfile(view):
  if not is_js_file(view): return None
  fname = view.file_name()
  if fname is None:
    fname = os.path.join(os.path.dirname(__file__), get_setting("tern_default_project_dir", "default_project_dir"), str(time.time()))
  if fname in files:
    pfile = files[fname]
    if pfile.project.disabled: return None
    return pfile

  pdir = project_dir(fname)
  if pdir is None: return None

  project = None
  for f in files.values():
    if f.project.dir == pdir:
      project = f.project
      break
  if project is None: project = Project(pdir)
  pfile = files[fname] = ProjectFile(fname, view, project)
  if project.disabled: return None
  return pfile

def project_dir(fname):
  dir = os.path.dirname(fname)
  if not os.path.isdir(dir): return None

  cur = dir
  while True:
    parent = os.path.dirname(cur[:-1])
    if not parent:
      break
    if os.path.isfile(os.path.join(cur, ".tern-project")):
      return cur
    cur = parent
  return dir

def pfile_modified(pfile, view):
  pfile.dirty = True
  now = time.time()
  if now - pfile.last_modified > .5:
    pfile.last_modified = now
    if is_st2:
      sublime.set_timeout(lambda: maybe_save_pfile(pfile, view, now), 5000)
    else:
      sublime.set_timeout_async(lambda: maybe_save_pfile(pfile, view, now), 5000)
  if pfile.cached_completions and sel_start(view.sel()[0]) < pfile.cached_completions[0]:
    pfile.cached_completions = None
  if pfile.cached_arguments and sel_start(view.sel()[0]) < pfile.cached_arguments[0]:
    pfile.cached_arguments = None

def maybe_save_pfile(pfile, view, timestamp):
  if pfile.last_modified == timestamp and pfile.dirty:
    send_buffer(pfile, view)

def server_port(project, ignored=None):
  if project.port is not None and project.port != ignored:
    return (project.port, True)
  if project.port == ignored:
    kill_server(project)

  port_file = os.path.join(project.dir, ".tern-port")
  if os.path.isfile(port_file):
    port = int(open(port_file, "r").read())
    if port != ignored:
      project.port = port
      return (port, True)

  started = start_server(project)
  if started is not None:
    project.port = started
  return (started, False)

def start_server(project):
  if not tern_command: return None
  if time.time() - project.last_failed < 30: return None
  env = None
  if platform.system() == "Darwin":
    env = os.environ.copy()
    env["PATH"] += ":/usr/local/bin"
  proc = subprocess.Popen(tern_command + tern_arguments, cwd=project.dir, env=env,
                          stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                          stderr=subprocess.STDOUT, shell=windows)
  output = ""

  while True:
    line = proc.stdout.readline().decode("utf-8")
    if not line:
      sublime.error_message("Failed to start server" + (output and ":\n" + output))
      project.last_failed = time.time()
      return None
    match = re.match("Listening on port (\\d+)", line)
    if match:
      project.proc = proc
      return int(match.group(1))
    else:
      output += line

def kill_server(project):
  if project.proc is None: return
  project.proc.stdin.close()
  project.proc.wait()
  project.proc = None

def relative_file(pfile):
  return pfile.name[len(pfile.project.dir) + 1:]

def buffer_fragment(view, pos):
  region = None
  for js_region in view.find_by_selector("source.js"):
    if js_region.a <= pos and js_region.b >= pos:
      region = js_region
      break
  if region is None: return sublime.Region(pos, pos)

  start = view.line(max(region.a, pos - 1000)).a
  if start < pos - 1500: start = pos - 1500
  cur = start
  min_indent = 10000
  while True:
    next = view.find("\\bfunction\\b", cur)
    if next is None or next.b > pos or (next.a == -1 and next.b == -1): break
    line = view.line(next.a)
    if line.a < pos - 1500: line = sublime.Region(pos - 1500, line.b)
    indent = count_indentation(view.substr(line))
    if indent < min_indent:
      min_indent = indent
      start = line.a
    cur = line.b
  return sublime.Region(start, min(pos + 500, region.b))

def count_indentation(line):
  count, pos = (0, 0)
  while pos < len(line):
    ch = line[pos]
    if ch == " ": count += 1
    elif ch == "\t": count += 4
    else: break
    pos += 1
  return count

def sel_start(sel):
  return min(sel.a, sel.b)
def sel_end(sel):
  return max(sel.a, sel.b)

class Req_Error(Exception):
  def __init__(self, message):
    self.message = message
  def __str__(self):
    return self.message

localhost = (windows and "127.0.0.1") or "localhost"

def make_request_py2():
  import urllib2
  opener = urllib2.build_opener(urllib2.ProxyHandler({}))
  def f(port, doc):
    try:
      req = opener.open("http://" + localhost + ":" + str(port) + "/", json.dumps(doc), 1)
      return json.loads(req.read())
    except urllib2.HTTPError as error:
      raise Req_Error(error.read())
  return f

def make_request_py3():
  import urllib.request, urllib.error
  opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
  def f(port, doc):
    try:
      req = opener.open("http://" + localhost + ":" + str(port) + "/", json.dumps(doc).encode("utf-8"), 1)
      return json.loads(req.read().decode("utf-8"))
    except urllib.error.URLError as error:
      raise Req_Error(error.read().decode("utf-8"))
  return f

if python3:
  make_request = make_request_py3()
else:
  make_request = make_request_py2()

def view_js_text(view):
  text, pos = ("", 0)
  for region in view.find_by_selector("source.js"):
    if region.a > pos: text += ";" + re.sub(r'[^\n]', " ", view.substr(sublime.Region(pos + 1, region.a)))
    text += view.substr(region)
    pos = region.b
  return text

def run_command(view, query, pos=None, fragments=True, silent=False):
  """Run the query on the Tern server.

  See default queries at http://ternjs.net/doc/manual.html#protocol.
  """

  pfile = get_pfile(view)
  if pfile is None or pfile.project.disabled: return

  if isinstance(query, str): query = {"type": query}
  if (pos is None): pos = view.sel()[0].b

  port, port_is_old = server_port(pfile.project)
  if port is None: return

  doc = {"query": query, "files": []}

  if not pfile.dirty:
    fname, sending_file = (relative_file(pfile), False)
  if fragments and view.size() > 8000:
    region = buffer_fragment(view, pos)
    doc["files"].append({"type": "part",
                         "name": relative_file(pfile),
                         "offset": region.a,
                         "text": view.substr(region)})
    pos -= region.a
    fname, sending_file = ("#0", False)
  else:
    doc["files"].append({"type": "full",
                         "name": relative_file(pfile),
                         "text": view_js_text(view)})
    fname, sending_file = ("#0", True)
  query["file"] = fname
  query["end"] = pos

  data = None
  try:
    data = make_request(port, doc)
  except Req_Error as e:
    if not silent: report_error(str(e), pfile.project)
    return None
  except:
    pass

  if data is None and port_is_old:
    try:
      port = server_port(pfile.project, port)[0]
      if port is None: return
      data = make_request(port, doc)
      if data is None: return None
    except Exception as e:
      if not silent: report_error(str(e), pfile.project)

  if sending_file: pfile.dirty = False
  return data

def send_buffer(pfile, view):
  port = server_port(pfile.project)[0]
  if port is None: return False
  try:
    make_request(port,
                 {"files": [{"type": "full",
                             "name": relative_file(pfile),
                             "text": view_js_text(view)}]})
    pfile.dirty = False
    return True
  except:
    return False

def report_error(message, project):
  if sublime.ok_cancel_dialog(message, "Disable Tern"):
    project.disabled = True

def completion_icon(type):
  if type is None or type == "?": return " (?)"
  if type.startswith("fn("): return " (fn)"
  if type.startswith("["): return " ([])"
  if type == "number": return " (num)"
  if type == "string": return " (str)"
  if type == "bool": return " (bool)"
  return " (obj)"

def fn_completion_icon(arguments):
  return " (fn/"+str(len(arguments))+")"

# create auto complete string from list arguments
def create_arg_str(arguments):
  if len(arguments) ==  0:
    return "${1}"
  arg_str = ""
  k = 1
  for argument in arguments:
    arg_str += "${" + str(k) + ":" + argument.replace("$", "\$") + "}, "
    k += 1
  return arg_str[0:-2]

# parse the type to get the arguments
def get_arguments(type):
  type = type[3:type.find(')')] + ",'"
  arg_list = []
  arg_start = 0
  arg_end = 0
  # this two variables are used to skip ': {...}' in signature like 'a: {...}'
  depth = 0
  arg_already = False
  for ch in type:
    if depth == 0 and ch == ',':
      if arg_already:
        arg_already = False
      elif arg_start != arg_end:
        arg_list.append(type[arg_start:arg_end])
      arg_start = arg_end+1
    elif depth == 0 and ch == ':':
      arg_already = True
      arg_list.append(type[arg_start:arg_end])
    elif ch == '{' or ch == '(' or ch == '[':
      depth += 1
    elif ch == '}' or ch == ')' or ch == ']':
      depth -= 1
    elif ch == ' ':
      arg_start = arg_end + 1
    arg_end += 1
  return arg_list

def ensure_completions_cached(pfile, view):
  pos = view.sel()[0].b
  if pfile.cached_completions is not None:
    c_start, c_word, c_completions = pfile.cached_completions
    if c_start <= pos:
      slice = view.substr(sublime.Region(c_start, pos))
      if slice.startswith(c_word) and not re.match(".*\\W", slice):
        return (c_completions, False)

  data = run_command(view, {"type": "completions", "types": True, "includeKeywords": True})
  if data is None: return (None, False)

  completions = []
  completions_arity = []
  for rec in data["completions"]:
    rec_name = rec.get('name').replace('$', '\\$')
    rec_type = rec.get("type", None)
    if arg_completion_enabled and completion_icon(rec_type) == " (fn)":
      arguments = get_arguments(rec_type)
      fn_name = rec_name + "(" + create_arg_str(arguments) + ")"
      completions.append((rec.get("name") + fn_completion_icon(arguments), fn_name))

      for i in range(len(arguments) - 1, -1, -1):
        fn_name = rec_name + "(" + create_arg_str(arguments[0:i]) + ")"
        completions_arity.append((rec.get("name") + fn_completion_icon(arguments[0:i]), fn_name))
    else:
      completions.append((rec.get("name") + completion_icon(rec_type), rec_name))

  # put the auto completions of functions with lower arity at the bottom of the autocomplete list
  # so they don't clog up the autocompeltions at the top of the list
  completions = completions + completions_arity
  pfile.cached_completions = (data["start"], view.substr(sublime.Region(data["start"], pos)), completions)
  return (completions, True)

def locate_call(view):
  sel = view.sel()[0]
  if sel.a != sel.b: return (None, 0)
  context = view.substr(sublime.Region(max(0, sel.b - 500), sel.b))
  pos = len(context)
  depth = argpos = 0
  while pos > 0:
    pos -= 1
    ch = context[pos]
    if ch == "}" or ch == ")" or ch == "]":
      depth += 1
    elif ch == "{" or ch == "(" or ch == "[":
      if depth > 0: depth -= 1
      elif ch == "(": return (pos + sel.b - len(context), argpos)
      else: return (None, 0)
    elif ch == "," and depth == 0:
      argpos += 1
  return (None, 0)

def show_argument_hints(pfile, view):
  call_start, argpos = locate_call(view)
  if call_start is None: return render_argument_hints(pfile, view, None, 0)
  if pfile.cached_arguments is not None and pfile.cached_arguments[0] == call_start:
    return render_argument_hints(pfile, view, pfile.cached_arguments[1], argpos)

  data = run_command(view, {"type": "type", "preferFunction": True}, call_start, silent=True)
  if data is not None:
    parsed = parse_function_type(data)
    if parsed is not None:
      parsed['url'] = data.get('url', None)
      parsed['doc'] = data.get('doc', None)
      pfile.cached_arguments = (call_start, parsed)
      render_argument_hints(pfile, view, parsed, argpos)

def render_argument_hints(pfile, view, ftype, argpos):
  if ftype is None:
    renderer.clean(pfile, view)
  else:
    renderer.render_arghints(pfile, view, ftype, argpos)

def parse_function_type(data):
  type = data["type"]
  if not re.match("fn\\(", type): return None
  pos = 3
  args, retval = ([], None)
  while pos < len(type) and type[pos] != ")":
    colon = type.find(":", pos)
    name = "?"
    if colon != -1:
      name = type[pos:colon]
      if not re.match("[\\w_$]+$", name): name = "?"
      else: pos = colon + 2
    type_start = pos
    depth = 0
    while pos < len(type):
      ch = type[pos]
      if ch == "(" or ch == "[" or ch == "{":
        depth += 1
      elif ch == ")" or ch == "]" or ch == "}":
        if depth > 0: depth -= 1
        else: break
      elif ch == "," and depth == 0:
        break
      pos += 1
    args.append((name, type[type_start:pos]))
    if type[pos] == ",": pos += 2
  if type[pos:pos + 5] == ") -> ":
    retval = type[pos + 5:]
  return {"name": data.get("exprName", None) or data.get("name", None) or "fn",
          "args": args,
          "retval": retval}

jump_stack = []

class TernArghintCommand(sublime_plugin.TextCommand):
  def run(self, edit, **args):
    self.view.insert(edit, 0, args.get('msg', ''))

class TernJumpToDef(sublime_plugin.TextCommand):
  def run(self, edit, **args):
    data = run_command(self.view, {"type": "definition", "lineCharPositions": True})
    if data is None: return
    file = data.get("file", None)
    if file is not None:
      # Found an actual definition
      row, col = self.view.rowcol(self.view.sel()[0].b)
      cur_pos = self.view.file_name() + ":" + str(row + 1) + ":" + str(col + 1)
      jump_stack.append(cur_pos)
      if len(jump_stack) > 50: jump_stack.pop(0)
      real_file = (os.path.join(get_pfile(self.view).project.dir, file) +
        ":" + str(data["start"]["line"] + 1) + ":" + str(data["start"]["ch"] + 1))
      sublime.active_window().open_file(real_file, sublime.ENCODED_POSITION)
    else:
      url = data.get("url", None)
      if url is None:
        sublime.error_message("Could not find a definition")
      else:
        webbrowser.open(url)

class TernJumpBack(sublime_plugin.TextCommand):
  def run(self, edit, **args):
    if len(jump_stack) > 0:
      sublime.active_window().open_file(jump_stack.pop(), sublime.ENCODED_POSITION)

class TernSelectVariable(sublime_plugin.TextCommand):
  def run(self, edit, **args):
    data = run_command(self.view, "refs", fragments=False)
    if data is None: return
    file = relative_file(get_pfile(self.view))
    shown_error = False
    regions = []
    for ref in data["refs"]:
      if ref["file"].replace('\\','/') != file.replace('\\','/'):
        if not shown_error:
          sublime.error_message("Not all uses of this variable are file-local. Selecting only local ones.")
          shown_error = True
      else:
        regions.append(sublime.Region(ref["start"], ref["end"]))
    self.view.sel().clear()
    for r in regions: self.view.sel().add(r)


class TernDescribe(sublime_plugin.TextCommand):
  def run(self, edit, **args):
    data = run_command(self.view, {"type": "documentation"})
    if data is None:
      return
    renderer.render_description(get_pfile(self.view), self.view,
                                data["type"], data.get("doc", None),
                                data.get("url", None))


# fetch a certain setting from the package settings file and if it doesn't exist check the
# Preferences.sublime-settings file for backwards compatibility.
def get_setting(key, default):
  old_settings = sublime.load_settings("Preferences.sublime-settings")
  new_settings = sublime.load_settings("Tern.sublime-settings")

  setting = new_settings.get(key, None)
  if setting is None:
    return old_settings.get(key, default)
  else:
    return new_settings.get(key, default)

plugin_dir = os.path.abspath(os.path.dirname(__file__))

def plugin_loaded():
  global arghints_enabled, renderer, tern_command, tern_arguments
  global arg_completion_enabled
  arghints_enabled = get_setting("tern_argument_hints", False)
  arg_completion_enabled = get_setting("tern_argument_completion", False)

  if "show_popup" in dir(sublime.View):
    default_output_style = "tooltip"
  else:
    default_output_style = "status"
  output_style = get_setting("tern_output_style", get_setting("tern_argument_hints_type", default_output_style))
  renderer = create_renderer(output_style)
  tern_arguments = get_setting("tern_arguments", [])
  if not isinstance(tern_arguments, list):
    tern_arguments = [tern_arguments]
  tern_command = get_setting("tern_command", None)
  if tern_command is None:
    if not os.path.isdir(os.path.join(plugin_dir, "node_modules/tern")):
      if sublime.ok_cancel_dialog(
          "It appears Tern has not been installed. Do you want tern_for_sublime to try and install it? "
          "(Note that this will only work if you already have node.js and npm installed on your system.)"
          "\n\nTo get rid of this dialog, either uninstall tern_for_sublime, or set the tern_command setting.",
          "Yes, install."):
        try:
          if hasattr(subprocess, "check_output"):
            subprocess.check_output(["npm", "--loglevel=silent", "install"], cwd=plugin_dir, shell=windows)
          else:
            subprocess.check_call(["npm", "--loglevel=silent", "install"], cwd=plugin_dir, shell=windows)
        except (IOError, OSError, CalledProcessError) as e:
          msg = "Installation failed. Try doing 'npm install' manually in " + plugin_dir + "."
          if hasattr(e, "output") and e.output is not None:
            msg += "\nError message was:\n\n" + e.output
          if hasattr(e, "returncode"):
            msg += "\nReturn code was: " + str(e.returncode)
          sublime.error_message(msg)
          return
    tern_command = ["node",  os.path.join(plugin_dir, "node_modules/tern/bin/tern"), "--no-port-file"]

def cleanup():
  for f in files.values():
    kill_server(f.project)

atexit.register(cleanup)

if is_st2:
  sublime.set_timeout(plugin_loaded, 500)
