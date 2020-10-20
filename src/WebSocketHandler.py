from ws4py.server.cherrypyserver import WebSocketPlugin, WebSocketTool
from ws4py.websocket import WebSocket
from ws4py.messaging import TextMessage
import cherrypy

class WebSocketHandler(WebSocket):
    def received_message(self, m):
        if m.is_text:
            recvStr = m.data.decode("utf-8")
            print(recvStr)
        # cherrypy.engine.publish('websocket-broadcast', m)

    def closed(self, code, reason="Socket closed."):
        cherrypy.engine.publish('websocket-broadcast', TextMessage(reason))
