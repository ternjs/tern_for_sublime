# encoding=utf8

import abc
import cgi
import textwrap

import sublime


def format_doc(doc):
  """Format doc output for display in panel."""

  return textwrap.fill(doc, width=79)


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
  if ftype['doc'] is not None:
    msg += "\n\n" + format_doc(ftype['doc'])
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
    'doc_link': hint_line(link(ftype['url'], '[docs]')),
    'doc': hint_line(doc)
  }

  return template.format(**template_data)


def get_description_message(useHTML, type, doc=None, url=None):
  """Get the message to display for Describe commands.

  If useHTML is True, the message will be formatted with HTML tags.
  """

  message = type
  if useHTML:
    message = "<strong>{type}</strong>".format(type=message)
  if doc is not None:
    if useHTML:
      message += " — " + cgi.escape(doc)
    else:
      message += "\n\n" + format_doc(doc)
  if url is not None:
    message += " "
    if useHTML:
      message += '<a href="{url}">[docs]</a>'.format(url=url)
    else:
      message += "\n\n" + url
  return message


def maybe(fn):
  def maybe_fn(arg, *args, **kwargs):
    return fn(arg, *args, **kwargs) if arg else ''
  return maybe_fn


@maybe
def link(url, linkText='{url}'):
  """Returns a link HTML string.

  The string is an &lt;a&gt; tag that links to the given url.
  If linkText is not provided, the link text will be the url.
  """

  template = '<a href={url}>' + linkText + '</a>'
  return template.format(url=url)


@maybe
def hint_line(txt):
  return '<div class="hint-line-content">{txt}</div>'.format(txt=txt)


def go_to_url(url=None):
  if url:
    import webbrowser
    webbrowser.open(url)


class RendererBase(object):
  """Class that renders Tern messages."""

  __metaclass__ = abc.ABCMeta

  @abc.abstractmethod
  def _render_impl(self, pfile, view, message):
    """Render the message.

    Implement this to define how subclasses render the message.
    """

  def _clean_impl(self, pfile, view):
    """Clean rendered content.

    Override this to define subclass-specific cleanup.
    """
    pass

  def _render_message(self, pfile, view, message):
    self._render_impl(pfile, view, message)
    pfile.showing_arguments = True

  def render_arghints(self, pfile, view, ftype, argpos):
    """Render argument hints."""

    if self.useHTML:
      message = get_html_message_from_ftype(ftype, argpos)
    else:
      message = get_message_from_ftype(ftype, argpos)
    self._render_message(pfile, view, message)

  def render_description(self, pfile, view, type, doc=None, url=None):
    """Render description."""

    message = get_description_message(self.useHTML, type, doc, url)
    self._render_message(pfile, view, message)

  def clean(self, pfile, view):
    """Clean rendered content."""

    self._clean_impl(pfile, view)
    pfile.showing_arguments = False


class TooltipRenderer(RendererBase):
  """Class that renders Tern messages in a tooltip."""

  def __init__(self):
    self.useHTML = True  # Used in RendererBase

  def _render_impl(self, pfile, view, message):
    view.show_popup(message, sublime.COOPERATE_WITH_AUTO_COMPLETE,
                    max_width=600, on_navigate=go_to_url)


class StatusRenderer(RendererBase):
  """Class that renders Tern messages in the status bar."""

  def __init__(self):
    self.useHTML = False

  def _render_impl(self, pfile, view, message):
    sublime.status_message(message.split('\n')[0])

  def _clean_impl(self, pfile, view):
    if pfile.showing_arguments:
      sublime.status_message("")


class PanelRenderer(RendererBase):
  """Class that renders Tern messages in a panel."""

  def __init__(self):
    self.useHTML = False

  def _render_impl(self, pfile, view, message):
    panel = view.window().get_output_panel("tern_arghint")
    panel.run_command("tern_arghint", {"msg": message})
    view.window().run_command("show_panel", {"panel": "output.tern_arghint"})

  def _clean_impl(self, pfile, view):
    if pfile.showing_arguments:
      panel = view.window().get_output_panel("tern_arghint")
      panel.run_command("tern_arghint", {"msg": ""})


def create_renderer(arghints_type):
  """Create the correct renderer based on type.

  Currently supported types are "tooltip", "status", and "panel".
  """

  if arghints_type == "tooltip":
    return TooltipRenderer()
  elif arghints_type == "status":
    return StatusRenderer()
  elif arghints_type == "panel":
    return PanelRenderer()
