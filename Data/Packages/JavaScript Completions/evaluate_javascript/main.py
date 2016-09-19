import sublime, sublime_plugin
import traceback, os, json, io, sys, imp

import _init

if int(sublime.version()) >= 3000 :
  from node.main import NodeJS


SETTINGS_FOLDER_NAME = "evaluate_javascript"
SETTINGS_FOLDER = os.path.join(_init.PACKAGE_PATH, SETTINGS_FOLDER_NAME)

class EvaluateJavascript():
  settings_id = 2
  def init(self):
    self.api = {}
    self.settings = sublime.load_settings('Evaluate-JavaScript.sublime-settings')

    if self.settings.get("enable_context_menu_option") :
      _init.enable_setting(SETTINGS_FOLDER, "Context", "sublime-menu")
    else :
      _init.disable_setting(SETTINGS_FOLDER, "Context", "sublime-menu")

    if self.settings.get("enable_key_map") :
      _init.enable_setting(SETTINGS_FOLDER, "Default ("+_init.PLATFORM+")", "sublime-keymap")
    else :
      _init.disable_setting(SETTINGS_FOLDER, "Default ("+_init.PLATFORM+")", "sublime-keymap")

ej = EvaluateJavascript()

if int(sublime.version()) < 3000 :
  ej.init()
else :
  def plugin_loaded():
    global ej
    ej.init()

if int(sublime.version()) >= 3000 :
  result_js = ""
  region_selected = None
  popup_is_showing = False
  css = """
  <style>
  html{
    margin: 0;
    padding: 0;
  }
  body{
    color: #fff;
    margin: 0;
    padding: 0;
  }
  .container{
    background-color: #202A31;
    padding: 10px;
  }
  a{
    color: #fff;
    display: block;
    margin: 10px 0;
  }
  </style>
  """

  def action_result(action):
    global result_js
    global region_selected

    view = sublime.active_window().active_view()
    sel = region_selected
    str_selected = view.substr(sel).strip()

    if action == "copy_to_clipboard" :
      sublime.set_clipboard(result_js)

    elif action == "replace_text" :
      view.run_command("replace_text")

    elif action == "view_result_with_allspaces":
      view.run_command("view_result_with_allspaces")

    view.hide_popup()
    result_js = ""

  class view_result_with_allspacesCommand(sublime_plugin.TextCommand):
    def run(self, edit):
      global result_js
      global region_selected

      sublime.active_window().show_input_panel("Result", result_js, back_to_popup, back_to_popup, back_to_popup)

  class replace_textCommand(sublime_plugin.TextCommand):

    def run(self, edit):
      global result_js
      global region_selected

      view = self.view
      sel = trim_Region(view, region_selected)
      view.replace(edit, sel, result_js)
      if region_selected.a < region_selected.b :
        region_selected.b = region_selected.a+len(result_js)
      else :
        region_selected.a = region_selected.b+len(result_js)

  class ej_hide_popupEventListener(sublime_plugin.EventListener):
    def on_modified_async(self, view) :
      global popup_is_showing
      if popup_is_showing :
        view.hide_popup()
        popup_is_showing = False

  class evaluate_javascriptCommand(sublime_plugin.TextCommand):

    def run(self, edit, is_line=False, eval_type="eval"):
      global result_js
      global region_selected
      global popup_is_showing

      view = self.view
      sel = view.sel()[0]
      popup_is_showing = False
      str_selected = view.substr(sel).strip()

      if is_line:
        lines = view.lines(sel)
        region_selected = lines[0]
        str_selected = view.substr(region_selected)
      else: 
        if not str_selected and region_selected : 
          region = get_start_end_code_highlights_eval()
          region_selected = sublime.Region(region[0], region[1])
          lines = view.lines(region_selected)
          str_selected = ""
          for line in lines:
            str_selected += view.substr(view.full_line(line))
        elif str_selected:
          lines = view.lines(sel)
          region_selected = sublime.Region if not region_selected else region_selected
          region_selected = sublime.Region(lines[0].begin(), lines[-1:][0].end())
        elif not str_selected :
          return
      
      if not region_selected :
        return

      view.run_command("show_start_end_dot_eval")

      try:
        node = NodeJS()
        result_js = node.eval(str_selected, eval_type, True)
        popup_is_showing = True
        view.show_popup("<html><head></head><body>"+css+"""<div class=\"container\">
          <p class="result">Result: """+result_js+"""</p>
          <div><a href="view_result_with_allspaces">View result with all spaces(\\t,\\n,...)</a></div>
          <div><a href="copy_to_clipboard">Copy result to clipboard</a></div>
          <div><a href="replace_text">Replace text with result</a></div>
          </div>
        </body></html>""", sublime.COOPERATE_WITH_AUTO_COMPLETE, -1, 400, 400, action_result)
      except Exception as e:
        #sublime.error_message("Error: "+traceback.format_exc())
        sublime.active_window().show_input_panel("Result", "Error: "+traceback.format_exc(), lambda x: "" , lambda x: "", lambda : "")

  class show_start_end_dot_evalCommand(sublime_plugin.TextCommand) :
    def run(self, edit) :
      global region_selected
      view = self.view
      lines = view.lines(region_selected)
      view.add_regions("region-dot", [lines[0], lines[-1:][0]],  "code", "dot", sublime.DRAW_NO_FILL | sublime.DRAW_NO_OUTLINE)
      #view.add_regions("region-body", [region_selected],  "code", "", sublime.DRAW_NO_FILL)

  class hide_start_end_dot_evalCommand(sublime_plugin.TextCommand) :
    def run(self, edit) :
      view = self.view
      view.erase_regions("region-dot")
      #view.erase_regions("region-body")

  def get_start_end_code_highlights_eval() :
    view = sublime.active_window().active_view()
    return [view.line(view.get_regions("region-dot")[0]).begin(), view.line(view.get_regions("region-dot")[1]).end()]

  def trim_Region(view, region):
    new_region = sublime.Region(region.begin(), region.end())
    while(view.substr(new_region).startswith(" ") or view.substr(new_region).startswith("\n")):
      new_region.a = new_region.a + 1
    while(view.substr(new_region).endswith(" ") or view.substr(new_region).startswith("\n")):
      new_region.b = new_region.b - 1
    return new_region

  def back_to_popup(*str_arg):
    view = sublime.active_window().active_view()
    view.run_command("evaluate_javascript")
    return
