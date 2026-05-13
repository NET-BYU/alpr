"""
This file defines a generic MQTT class for our lab-grade sensor scripts to use to transmit data.
It is based on example code from the Eclipse Paho MQTT library
"""

import paho.mqtt.client as mqtt


class labMqttPublisher:

    def __init__(
        self,
        brokerAddr: str,
        brokerPort: str,
        brokerTopic: str,
        brokerUser: str,
        brokerPass: str,
    ):
        # Store params
        self.brokerAddr = brokerAddr
        self.brokerPort = int(brokerPort)
        self.brokerTopic = brokerTopic
        self.brokerUser = brokerUser
        self.brokerPass = brokerPass

        # MQTT setup
        self.unacked_publish = set()
        self.mqttc = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        self.mqttc.on_publish = self.on_publish
        self.mqttc.user_data_set(self.unacked_publish)
        self.mqttc.username_pw_set(brokerUser, brokerPass)

    def connect(self):
        self.mqttc.connect(self.brokerAddr, self.brokerPort)
        self.mqttc.loop_start()

    def disconnect(self):
        self.mqttc.disconnect()
        self.mqttc.loop_stop()

    def on_publish(self, client, userdata, mid, reason_code, properties):
        """
        (copied from Eclipse Paho example code)
        """
        # reason_code and properties will only be present in MQTTv5. It's always unset in MQTTv3
        try:
            userdata.remove(mid)
        except KeyError:
            print("on_publish() is called with a mid not present in unacked_publish")
            print("This is due to an unavoidable race-condition:")
            print("* publish() return the mid of the message sent.")
            print("* mid from publish() is added to unacked_publish by the main thread")
            print("* on_publish() is called by the loop_start thread")
            print(
                "While unlikely (because on_publish() will be called after a network round-trip),"
            )
            print(" this is a race-condition that COULD happen")
            print("")
            print(
                "The best solution to avoid race-condition is using the msg_info from publish()"
            )
            print(
                "We could also try using a list of acknowledged mid rather than removing from pending list,"
            )
            print("but remember that mid could be re-used !")

    def transmit_message(self, message: str):
        msg_info = self.mqttc.publish(self.brokerTopic, message, qos=1)
        self.unacked_publish.add(msg_info.mid)

        # Wait for our message to be published
        # Due to the race condition described in on_publish, the is way is considered safer... apparently.
        msg_info.wait_for_publish()
