import sublime, sublime_plugin, os, subprocess, glob, tempfile, plistlib, time, threading
from zipfile import ZipFile

class Snippet:
	def __init__(self, region, edit, view):
		self.region = region
		self.edit = edit
		self.view = view
		self.scope = view.scope_name(region.begin()).split(' ')[0].strip()
		self.cmd = self.view.substr(region)
		self.settings = sublime.load_settings('smart-pieces.sublime-settings')
		self.done = True

	def output(self, lang):
		if self.done:
			if not '' == lang:
				self.cmd = lang + ':' + self.cmd
			shellCommand = '{0} render {1}'.format(self.settings.get('path'), self.cmd)
			output = subprocess.check_output(shellCommand, shell = True).decode()
			self.view.replace(self.edit, self.region, shellCommand + "\n" + output)
		scopes = self.settings.get('scopes')
		if self.scope not in scopes:
			scopes[self.scope] = lang
			self.settings.set("scopes", scopes)
			sublime.save_settings('smart-pieces.sublime-settings')

	def render(self):
		if ':' not in self.cmd.split(' ')[0]:
			scopes = self.settings.get('scopes')
			if self.scope not in scopes:
				lang = self.scope
				if lang.startswith('source.'):
					lang = lang[7:]
				elif lang.startswith('text.'):
					lang = lang[5:]
				if self.settings.get('ask_when_new_scope'):
					self.done = False
					self.view.window().show_input_panel(
						'Language for scope {0}:'.format(self.scope), lang, 
						self.output, None, None)
				else:
					self.output(lang)
			else:
				self.output(scopes[self.scope])
		else:
			self.output('')


class SmartPiecesCommand(sublime_plugin.TextCommand):
	settings = sublime.load_settings('smart-pieces.sublime-settings')
	if not settings.has('scopes'):
		load_and_save_scopes()

	def load_and_save_scopes(self):
		scopes = set()
		for x in os.walk(sublime.packages_path() + '/..'):
			for f in glob.glob(os.path.join(x[0], '*.tmLanguage')):
				for s in self.get_scopes_from(plistlib.readPlist(f)):
					scopes.add(s.strip())

		for x in os.walk(os.path.dirname(sublime.executable_path())):
			for f in glob.glob(os.path.join(x[0], '*.sublime-package')):
				input_zip = ZipFile(f)
				for name in input_zip.namelist():
					if name.endswith('.tmLanguage'):
						for s in self.get_scopes_from(plistlib.readPlistFromBytes(input_zip.read(name))):
							scopes.add(s.strip())

		for x in os.walk(sublime.packages_path() + '/..'):
			for f in glob.glob(os.path.join(x[0], '*.sublime-package')):
				input_zip = ZipFile(f)
				for name in input_zip.namelist():
					if name.endswith('.tmLanguage'):
						for s in self.get_scopes_from(plistlib.readPlistFromBytes(input_zip.read(name))):
							scopes.add(s.strip())
		names = list(scopes)
		scopes = dict()
		for name in names:
			value = name
			if value.startswith('source.'):
				value = value[7:]
			elif value.startswith('text.'):
				value = value[5:]
			scopes[name] = value
		self.settings.set('scopes', scopes)
		sublime.save_settings('smart-pieces.sublime-settings')

	def get_scopes_from(self, d):
		result = []
		for k in d.keys():
			if k == 'scopeName':
				result = result + [ s.strip() for s in d[k].split(',') ]
			elif isinstance(d[k], dict):
				result = result + self.get_scopes_from(d[k])
		return result

	def run(self, edit):
		for region in self.view.sel():
			if region.empty():
				region = self.view.line(region)
			s = Snippet(region, edit, self.view)
			s.render()

