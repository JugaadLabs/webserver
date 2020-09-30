import jinja2
import os

class Templates:
    def __init__(self, stateVars):
        self.stateVars = stateVars
        loader = jinja2.FileSystemLoader(self.html_dirpath())
        self.environment = jinja2.Environment(loader=loader)

    def html_dirpath(self):
        return os.path.join(os.getcwd(), 'html')

    def index(self):
        opts = {}
        opts['zedstop'] = self.stateVars['zedstop'].is_set()
        opts['zedpaused'] = self.stateVars['zedpaused'].is_set()
        opts['csistop'] = self.stateVars['csistop'].is_set()
        opts['csipaused'] = self.stateVars['csipaused'].is_set()
        return self.render_template('index', opts)

    def render_template(self, template_name, opts):
        template = self.environment.get_template(template_name + '.html')
        return template.render(state=opts)

def main():
    template = Templates(None)
    print(template.index())

if __name__=="__main__": 
    main() 
