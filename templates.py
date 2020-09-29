import jinja2
import os

class Templates:
    def __init__(self, stateVars):
        self.stateVars = stateVars
        loader = jinja2.FileSystemLoader(self.html_dirpath())
        self.environment = jinja2.Environment(loader=loader)

    def html_dirpath(self):
        return os.path.join(os.getcwd(),'html')

    def index(self):
        opts = {}
        # opts['streaming'] = self.apsync.streaming
        # opts['streaming_error'] = self.apsync.streaming_error
        # opts['streaming_to_ip'] = self.apsync.streaming_to_ip
        # opts['auto_streaming'] = self.apsync.auto_streaming_enabled()
        return self.render_template('index', opts)

    def render_template(self, template_name, opts):
        template = self.environment.get_template(template_name + '.html')
        return template.render(state=opts)
