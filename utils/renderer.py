import sublime

def get_message_from_ftype(ftype, argpos):
  msg = ftype["name"] + "("
  i = 0
  for name, type in ftype["args"]:
    if i > 0: msg += ", "
    if i == argpos: msg += "*"
    msg += name + ("" if type == "?" else ": " + type)
    i += 1
  msg += ")"
  if ftype["retval"] is not None:
    msg += " -> " + ftype["retval"]
  return msg

def get_html_message_from_ftype(ftype, argpos):
  style = '''
    <style>
      .hint-popup {
        padding-top: 10px;
        font-size: 14px;
      }
      .hint-line-content {
        padding-bottom: 10px;
      }
      .func-arrow {
        font-size: 16px;
      }
      .arg-name {
        color: #70a;
      }
      .current-arg {
        font-weight: bold;
        text-decoration: underline;
      }
      .doc {
        font-style: italic;
      }
      .type {
        color: #07c;
      }
    </style>
  '''

  func_signature = '<span class="func-name">{func_name}</span>('.format(func_name=ftype["name"])
  i = 0
  for name, type in ftype["args"]:
    if i > 0: func_signature += ", "
    if i == argpos:
      func_signature += '<span class="arg-name current-arg">{name}</span>'.format(name=name)
    else:
      func_signature += '<span class="arg-name">{name}</span>'.format(name=name)
    if type != "?":
      func_signature += ': <span class="type">{type}</span>'.format(type=type)
    i += 1
  func_signature += ")"
  if ftype["retval"] is not None:
    func_signature += '<span class="func-arrow"> ➜ </span><span class="type">{type}</span>'.format(type=ftype["retval"])

  template = '''
    {style}
    <div class="hint-popup">
      <div class="hint-line func-signature">{func_signature}</div>
      <div class="hint-line doc-link">{doc_link}</div>
      <div class="hint-line doc">{doc}</div>
    </div>
  '''

  doc = ftype['doc']
  if doc: doc = doc.replace("\n", "<br>")

  template_data = {
    'style': style,
    'func_signature': hint_line(func_signature),
    'doc_link': hint_line(link(ftype['url'])),
    'doc': hint_line(doc)
  }

  return template.format(**template_data)

def maybe(fn):
  def maybe_fn(arg):
    return fn(arg) if arg else ''
  return maybe_fn

@maybe
def link(url):
  return '<a href={url}>{url}</a>'.format(url=url)

@maybe
def hint_line(txt):
  return '<div class="hint-line-content">{txt}</div>'.format(txt=txt)

def go_to_url(url=None):
  if url:
    import webbrowser
    webbrowser.open(url)

class TooltipArghintsRenderer(object):
  def render(self, pfile, view, ftype, argpos):
    view.show_popup(get_html_message_from_ftype(ftype, argpos), sublime.COOPERATE_WITH_AUTO_COMPLETE, max_width=600, on_navigate=go_to_url)
    pfile.showing_arguments = True

  def clean(self, pfile, view):
    pfile.showing_arguments = False


class StatusArghintsRenderer(object):
  def render(self, pfile, view, ftype, argpos):
    msg = get_message_from_ftype(ftype, argpos)
    sublime.status_message(msg)
    pfile.showing_arguments = True

  def clean(self, pfile, view):
    if pfile.showing_arguments:
      sublime.status_message("")
      pfile.showing_arguments = False


class PanelArghintsRenderer(object):
  def render(self, pfile, view, ftype, argpos):
    msg = get_message_from_ftype(ftype, argpos)
    panel = view.window().get_output_panel("tern_arghint")
    panel.run_command("tern_arghint", {"msg": msg})
    view.window().run_command("show_panel", {"panel": "output.tern_arghint"})
    pfile.showing_arguments = True

  def clean(self, pfile, view):
    if pfile.showing_arguments:
      panel = view.window().get_output_panel("tern_arghint")
      panel.run_command("tern_arghint", {"msg": ""})
      pfile.showing_arguments = False


def create_arghints_renderer(arghints_type):
  if arghints_type == "tooltip":
    return TooltipArghintsRenderer()
  elif arghints_type == "status":
    return StatusArghintsRenderer()
  elif arghints_type == "panel":
    return PanelArghintsRenderer()