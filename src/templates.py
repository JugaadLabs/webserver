import jinja2
import os

class Templates:
    def __init__(self, stateVars):
        self.stateVars = stateVars
        loader = jinja2.FileSystemLoader(self.templatePath())
        self.environment = jinja2.Environment(loader=loader)

    def templatePath(self):
        return os.path.join(os.getcwd(), 'templates')

    def index(self):
        opts = {}
        opts['zedstop'] = self.stateVars['zedstop'].is_set()
        opts['zedpaused'] = self.stateVars['zedpaused'].is_set()
        opts['csistop'] = self.stateVars['csistop'].is_set()
        opts['csipaused'] = self.stateVars['csipaused'].is_set()
        controlPanelTemplate = self.environment.get_template('recording.html')
        html = controlPanelTemplate.render(state=opts)
        template = self.environment.get_template('base.html')
        return template.render(body_html=html)

    def documentation(self):
        docu_template = self.environment.get_template('documentation.html')
        html = docu_template.render()
        template = self.environment.get_template('base.html')
        return template.render(body_html=html)

    def ls(self, files, dirs):
        opts = {}
        opts['files'] = files
        opts['dirs'] = dirs
        ls_template = self.environment.get_template('ls.html')
        html = ls_template.render(state=opts)
        template = self.environment.get_template('base.html')
        return template.render(body_html=html)


def main():
    template = Templates(None)
    print(template.index())

if __name__=="__main__": 
    main() 
