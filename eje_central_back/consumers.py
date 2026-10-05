"""
Consumer de infraestructura, NO de producto: existe solo para poder
verificar end-to-end (nginx -> plazas-ws -> Channels -> Redis) que el
soporte de websockets funciona. Ningún feature lo usa todavía.
"""

from channels.generic.websocket import WebsocketConsumer


class HealthConsumer(WebsocketConsumer):
    def connect(self):
        self.accept()
        self.send(text_data="pong")

    def receive(self, text_data=None, bytes_data=None):
        self.send(text_data=f"echo:{text_data}")
